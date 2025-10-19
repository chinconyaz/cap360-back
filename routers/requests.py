from fastapi import APIRouter, HTTPException
from models import Member, Transaction, MoneyRequest
import database
import httpx, uuid, os
from dotenv import load_dotenv
from typing import Optional

from routers.nessie import create_nessie_customer
from datetime import datetime

router = APIRouter()

@router.post("/{from_id}/request_money")
def request_money(from_id: str, to_id: str, amount: float, description: Optional[str] = None):
    sender = database.members_db.get(from_id)
    receiver = database.members_db.get(to_id)

    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="Invalid member IDs")
    
    if sender.family_id != receiver.family_id:
        raise HTTPException(status_code=400, detail="Must be same family")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    request_id = str(uuid.uuid4())
    money_request = MoneyRequest(
        id=request_id,
        from_id=from_id,
        to_id=to_id,
        amount=amount,
        description=description,
        date=datetime.now(),
        status="pending"
    )

    database.money_requests_db[request_id] = money_request
    database.members_db[receiver.id].requests[request_id] = money_request

    return {
        "message": f"Money request of ${amount} sent from {sender.first_name} to {receiver.first_name}",
        "request": money_request.model_dump()
    }

@router.post("/resolve_request/{request_id}")
def resolve_request(request_id: str, success: bool):
    if request_id not in database.money_requests_db:
        raise HTTPException(status_code=404, detail="Request not found")

    request = database.money_requests_db.get(request_id)
    sender = database.members_db.get(request.from_id)
    receiver = database.members_db.get(request.to_id)
    
    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="Invalid member IDs")
    
    if sender.family_id != receiver.family_id:
        raise HTTPException(status_code=400, detail="Must be same family")
    
    if receiver.balance - request.amount < 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    mid = str(uuid.uuid4())
    transaction = Transaction(
        id=mid,
        type_transaction="request fufilled",
        amount=request.amount,
        from_id = sender.id,
        to_id = receiver.id,
        from_name = sender.first_name + " " + sender.last_name,
        to_name = receiver.first_name + " " + receiver.last_name,
        from_debt=sender.current_debt + request.amount,
        to_debt=receiver.current_debt)

    del database.money_requests_db[request.id]
    del database.members_db[receiver.id].requests[request_id]

    if success:
        database.members_db[receiver.id].balance = receiver.balance - request.amount
        database.members_db[sender.id].balance = sender.balance + request.amount
        database.members_db[sender.id].current_debt = sender.current_debt + request.amount

        database.members_db[sender.id].transactions.append(transaction)
        database.members_db[receiver.id].transactions.append(transaction)

        for k in receiver.debts:
            if k != sender.id:
                database.members_db[k].transactions.append(transaction)

        print(request.amount)
        if receiver.id in database.members_db[sender.id].debts:
            database.members_db[sender.id].debts[receiver.id] += request.amount
        else:
            database.members_db[sender.id].debts[receiver.id] = request.amount
    else:
        return {
            "message": "request declined"
        }

    return {
        "message": "resolved debt"
    }

@router.post("/resolve_debt/{from_id}/{to_id}")
def resolve_debt(from_id: str, to_id: str, amount: float):
    # money should be returned back to the lender
    borrower = database.members_db.get(from_id)
    lender = database.members_db.get(to_id)

    if not lender or not borrower:
        raise HTTPException(404, "Invalid member IDs")

    if to_id not in borrower.debts or borrower.debts[to_id] < amount:
        raise HTTPException(400, "No such debt to resolve or insufficient debt amount")

    if borrower.balance < amount:
        raise HTTPException(400, "Borrower has insufficient balance")

    database.members_db.get(borrower.id).balance -= amount
    database.members_db.get(lender.id).balance += amount

    database.members_db.get(borrower.id).debts[to_id] -= amount

    if database.members_db.get(borrower.id).debts[to_id] == 0:
        del database.members_db.get(borrower.id).debts[to_id]

    mid = str(uuid.uuid4())
    transaction = Transaction(
        id=mid,
        type_transaction="debt resolution",
        from_id = from_id,
        amount=amount,
        to_id = to_id,
        from_name = borrower.first_name + " " + borrower.last_name,
        to_name = lender.first_name + " " + lender.last_name,
        from_debt=borrower.current_debt - amount,
        to_debt=lender.current_debt)

    database.members_db[borrower.id].current_debt -= amount

    database.members_db[borrower.id].transactions.append(transaction)
    database.members_db[lender.id].transactions.append(transaction)

    return {
        "message": f"{borrower.first_name} resolved ${amount} of debt to {lender.first_name}",
        "new_borrower_balance": borrower.balance,
        "new_lender_balance": lender.balance,
        "remaining_debt": borrower.debts[to_id]
    }