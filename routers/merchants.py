# backend/routers/merchants.py
from fastapi import APIRouter, HTTPException
from routers.nessie import list_merchants, nessie_make_purchase, get_nessie_account_balance
import database
import uuid, httpx, os
from models import Merchants, Transaction

router = APIRouter()
NESSIE_API_KEY = os.getenv("NESSIE_API_KEY")
BASE_URL = "http://api.nessieisreal.com"

@router.get("/")
async def get_merchants(limit: int = 5):
    """Fetch a few merchants from Nessie (e.g., Target, Walmart)."""
    try:
        merchants = await list_merchants(limit)
        return {"count": len(merchants), "merchants": merchants}
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch merchants: {e}")

async def create_nessie_merchant(name: str, category: str, address: dict, geocode: dict):
    """
    Create a merchant in the real Nessie API and return the created object.
    """
    payload = {
        "name": name,
        "category": category,
        "address": address,
        "geocode": geocode
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(f"{BASE_URL}/merchants?key={NESSIE_API_KEY}", json=payload)
        res.raise_for_status()
        return res.json()["objectCreated"]

@router.post("/create")
async def create_merchant(name: str, category: str, city: str = "Austin", state: str = "TX"):
    """
    Create a new merchant both in Nessie and in the local database.
    """
    # Mock address/geocode for now
    address = {
        "street_number": "1",
        "street_name": f"{name} Blvd",
        "city": city,
        "state": state,
        "zip": "73301"
    }
    geocode = {"lat": 30.2672, "lng": -97.7431}

    try:
        nessie_obj = await create_nessie_merchant(name, category, address, geocode)
    except Exception as e:
        raise HTTPException(500, f"Failed to create merchant in Nessie: {e}")

    # Create local merchant object
    local_id = str(uuid.uuid4())
    merchant = Merchants(
        id=local_id,
        name=nessie_obj["name"],
        category=nessie_obj.get("category"),
        location=f"{city}, {state}"
    )

    database.merchants_db[local_id] = merchant

    return {
        "message": f"Merchant '{name}' created successfully",
        "local_merchant_id": local_id,
        "nessie_merchant_id": nessie_obj["_id"],
        "category": category,
        "address": address
    }

@router.post("/pay")
async def pay_merchant(member_id: str, merchant_id: str, amount: float, desc: str = "Merchant purchase"):
    """Allow a user to pay a merchant using their Nessie account."""
    member = database.members_db.get(member_id)
    if not member:
        raise HTTPException(404, "Member not found")

    account_id = member.nessie_account_id[0]["_id"]

    # Check Nessie balance
    balance = await get_nessie_account_balance(account_id)
    if balance < amount:
        raise HTTPException(400, f"Insufficient balance (${balance} available)")

    # Execute Nessie purchase
    try:
        purchase = await nessie_make_purchase(account_id, merchant_id, amount, desc)
    except Exception as e:
        raise HTTPException(500, f"Purchase failed: {e}")

    # Update transaction state.
    mid = str(uuid.uuid4())
    transaction = Transaction(
        id=mid,
        type_transaction="purchased",
        amount=amount,
        from_id = member_id,
        to_id = merchant_id,
        from_name = member.first_name + " " + member.last_name,
        to_name = desc,
        from_debt=member.current_debt,
        to_debt=0)
    
    database.members_db[member_id].balance -= amount
    database.members_db[member.id].transactions.append(transaction)
    for k in member.debts:
        database.members_db[k].transactions.append(transaction)

    return {
        "message": f"{member.first_name} spent ${amount} at {desc}",
        "purchase_id": purchase["_id"],
        "merchant_id": merchant_id,
        "new_balance": member.balance
    }