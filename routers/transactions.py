from fastapi import APIRouter, HTTPException
from models import Transaction
import database
import uuid
from routers.nessie import get_nessie_account_balance, nessie_withdraw, nessie_deposit

router = APIRouter()

@router.post("/{family_id}/create")
async def create_transaction(family_id: str, from_id: str, to_id: str, amount: float, desc: str = None):
    family = database.families_db.get(family_id)
    if not family:
        raise HTTPException(404, "Family not found")

    lender = database.members_db.get(from_id)
    borrower = database.members_db.get(to_id)

    if not lender or not borrower:
        raise HTTPException(404, "Invalid member IDs")
    
    lender_acc = lender.nessie_account_id[0]["_id"]
    borrower_acc = borrower.nessie_account_id[0]["_id"]

    # Validate lender balance from Nessie
    lender_balance = await get_nessie_account_balance(lender_acc)
    if lender_balance < amount:
        raise HTTPException(400, f"Lender has insufficient balance (${lender_balance} available)")

    # Execute Nessie withdrawal and deposit
    try:
        withdrawal = await nessie_withdraw(lender_acc, amount, f"Loan to {borrower.first_name}")
        deposit = await nessie_deposit(borrower_acc, amount, f"Loan from {lender.first_name}")
    except Exception as e:
        raise HTTPException(500, f"Nessie transfer failed: {e}")

    # Update local mock data
    txn_id = str(uuid.uuid4())
    transaction = Transaction(
        id=txn_id,
        from_id=from_id,
        to_id=to_id,
        amount=amount,
        description=desc
    )

    database.transactions_db[txn_id] = transaction

    lender.balance -= amount
    borrower.balance += amount

    borrower.debts[from_id] = borrower.debts.get(from_id, 0) + amount
    lender.transactions_visible_to[to_id] = lender.transactions_visible_to.get(to_id, 0) + amount
    
    lender.transactions.append(txn_id)
    borrower.transactions.append(txn_id)
    family.transactions.append(transaction)

    current_debt = borrower.debts[from_id]

    if current_debt > 0 and from_id in borrower.debts:
        borrower.debts[from_id] -= amount

    return {
        "transaction_id": txn_id,
        "message": f"{lender.first_name} lent ${amount} to {borrower.first_name}",
        "nessie_withdrawal_id": withdrawal["_id"],
        "nessie_deposit_id": deposit["_id"],
        "lender_new_balance": lender.balance,
        "borrower_new_balance": borrower.balance
    }