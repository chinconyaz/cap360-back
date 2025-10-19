from fastapi import APIRouter, HTTPException
from models import Member, MemberCreate, Transaction, MoneyRequest
import database
import httpx, uuid, os
from dotenv import load_dotenv
from typing import Optional

from routers.nessie import create_nessie_customer, get_nessie_account_balance, nessie_withdraw, nessie_deposit
from datetime import datetime

router = APIRouter()
load_dotenv()

NESSIE_API_KEY = os.getenv("NESSIE_API_KEY")
BASE_URL = "http://api.nessieisreal.com"

router = APIRouter()

@router.post('/register')
async def create_member(member_to_add: MemberCreate):
    first_name = member_to_add.first_name
    last_name = member_to_add.last_name

    mid = str(uuid.uuid4())
    member = Member(
        id=mid, 
        first_name=first_name, 
        last_name=last_name, 
        balance=500.0,
        nessie_account_id=[])

    try:
        nessie_customer = await create_nessie_customer(first_name, last_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Nessie customer creation failed: {e}")
    
    nessie_customer_id = nessie_customer['_id']

    # Step 2 — Create a checking account for that customer
    account_data = {
        "type": "Checking",
        "nickname": f"{first_name}'s Account",
        "rewards": 0,
        "balance": 500  # mock starting balance
    }

    async with httpx.AsyncClient() as client:
        acc_res = await client.post(
            f"{BASE_URL}/customers/{nessie_customer_id}/accounts?key={NESSIE_API_KEY}",
            json=account_data
        )

        if acc_res.status_code != 201:
            raise HTTPException(
                status_code=acc_res.status_code,
                detail=f"Nessie account creation failed: {acc_res.text}"
            )

        nessie_account = acc_res.json()["objectCreated"]

    member.nessie_customer_id = nessie_customer_id
    member.nessie_account_id.append(nessie_account)

    database.members_db[mid] = member

    return {
        "message": f"Member {first_name} {last_name} created successfully",
        "member_id": mid,
        "nessie_customer_id": nessie_customer_id,
        "nessie_account_id": nessie_account["_id"],
        "starting_balance": nessie_account["balance"]
    }


@router.get('/{member_id}')
def get_member(member_id: str):
    member = database.members_db.get(member_id)
    if not member:
        raise HTTPException(404, "Member not found")
    return member.model_dump()

@router.post("/{family_id}/add/{member_id}")
def add_member(family_id: str, member_id: str):
    family = database.families_db.get(family_id)
    member = database.members_db.get(member_id)
    
    if not family:
        raise HTTPException(404, "Family not found")

    if not member:
        raise HTTPException(404, "Member not found")

    family.members.append(member)
    return {"message": "f{member.first_name} {member.last_name} added to {family.name} family"}

@router.get("/{member_id}/transactions")
def get_member_transactions(member_id: str):
    transactions = []
    member = database.members_db.get(member_id)

    for transaction_id in member.transactions:
        transaction = database.transactions_db.get(transaction_id)
        sender_name = database.members_db.get(transaction.from_id).first_name + " " + database.members_db.get(transaction.from_id).last_name
        receiver_name = database.members_db.get(transaction.to_id).first_name + " " + database.members_db.get(transaction.to_id).last_name

        if transaction:
            transactions.append({
                "from": sender_name,
                "to": receiver_name,
                "amount": transaction.amount,
                "description": transaction.description
            })

    return transactions

@router.get("/{member_id}/borrower_transactions")
def get_borrower_transactions(member_id: str):
    transactions = []
    member = database.members_db.get(member_id)
    # return HTTPException(404, f"{member.transactions_visible_to}")

    for borrower in member.transactions_visible_to.keys():
        transactions.append({
            "borrower_name": database.members_db.get(borrower).first_name + " " + database.members_db.get(borrower).last_name,
            "transactions_done": database.members_db.get(borrower).transactions
        })

    return transactions

@router.get("/thegoat/bakra")
def get_bakra():
    for member_id, member in database.members_db.items():
        print(member.first_name)
        if member.first_name == "Aiyaz":
            return member
        
    raise HTTPException(404, "Bakra not found")

@router.get("/{member_id}/get_all_borrowers")
def get_all_borrowers_transactions(member_id: str):
    member = database.members_db.get(member_id)
    
    if not member:
        raise HTTPException(404, "Member not found")
    
    member = database.members_db.get(member_id)

    borrowers_summary = {}

    for borrower_id in member.transactions_visible_to.keys():
        borrower = database.members_db.get(borrower_id)

        if borrower:
            last_five_transactions = borrower.transactions[-5:]

            borrowers_summary[borrower_id] = {
                "amount_owed": member.transactions_visible_to[borrower_id],
                "last_five_transactions": last_five_transactions
            }

    return borrowers_summary


@router.get("/{member_id}/money_requests")
def get_money_requests(member_id: str):
    if member_id not in database.members_db:
        raise HTTPException(status_code=404, detail="Member not found")

    sent = [
        req.model_dump() for req in database.money_requests_db.values()
        if req.from_id == member_id
    ]
    received = [
        req.model_dump() for req in database.money_requests_db.values()
        if req.to_id == member_id
    ]

    return {
        "sent_requests": sent,
        "received_requests": received
    }

@router.post("/{from_id}/request_money")
def request_money(from_id: str, to_id: str, amount: float, description: Optional[str] = None):
    sender = database.members_db.get(from_id)
    receiver = database.members_db.get(to_id)

    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="Invalid member IDs")

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

    # Store the request in database
    database.money_requests_db[request_id] = money_request

    return {
        "message": f"Money request of ${amount} sent from {sender.first_name} to {receiver.first_name}",
        "request": money_request.model_dump()
    }


@router.post("/respond_request/{request_id}")
async def respond_to_request(request_id: str, accept: bool):
    req = database.money_requests_db.get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {req.status}")

    sender = database.members_db.get(req.from_id)   # borrower
    receiver = database.members_db.get(req.to_id)   # lender

    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="Invalid members in request")

    # Only process if approved
    if accept:
        # ----------------------------
        # Validate Nessie accounts
        # ----------------------------
        if not receiver.nessie_account_id or not sender.nessie_account_id:
            raise HTTPException(status_code=400, detail="Both users must have Nessie accounts")

        receiver_acc = receiver.nessie_account_id[0]["_id"] if isinstance(receiver.nessie_account_id[0], dict) else receiver.nessie_account_id[0]
        sender_acc = sender.nessie_account_id[0]["_id"] if isinstance(sender.nessie_account_id[0], dict) else sender.nessie_account_id[0]

        # ----------------------------
        # Validate balance via Nessie
        # ----------------------------
        lender_balance = await get_nessie_account_balance(receiver_acc)
        if lender_balance < req.amount:
            raise HTTPException(status_code=400, detail=f"Insufficient Nessie balance (${lender_balance} available)")

        # ----------------------------
        # Perform Nessie transfer
        # ----------------------------
        try:
            withdrawal = await nessie_withdraw(receiver_acc, req.amount, f"Money request to {sender.first_name}")
            deposit = await nessie_deposit(sender_acc, req.amount, f"Money request from {receiver.first_name}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Nessie transfer failed: {e}")

        # ----------------------------
        # Update local balances
        # ----------------------------
        receiver.balance -= req.amount
        sender.balance += req.amount

        # Create a Transaction object
        tx_id = str(uuid.uuid4())
        transaction = Transaction(
            id=tx_id,
            from_id=receiver.id,
            to_id=sender.id,
            amount=req.amount,
            description=f"Money request accepted ({req.id})",
            settled=True
        )

        # Store locally
        if not hasattr(database, "transactions_db"):
            database.transactions_db = {}
        database.transactions_db[tx_id] = transaction

        sender.transactions.append(tx_id)
        receiver.transactions.append(tx_id)

        req.status = "accepted"

    else:
        req.status = "declined"

    # Persist changes
    database.money_requests_db[request_id] = req

    return {
        "message": f"Request {req.status}",
        "request": req.model_dump(),
        **(
            {
                "nessie_withdrawal_id": withdrawal["_id"],
                "nessie_deposit_id": deposit["_id"],
                "lender_new_balance": receiver.balance,
                "borrower_new_balance": sender.balance,
            } if accept else {}
        )
    }