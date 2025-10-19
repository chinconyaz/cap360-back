# backend/routers/nessie.py
import httpx, os
from dotenv import load_dotenv

load_dotenv()
NESSIE_API_KEY = os.getenv("NESSIE_API_KEY")
BASE_URL = "http://api.nessieisreal.com"

# Create a new Nessie customer
async def create_nessie_customer(first_name: str, last_name: str):
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "address": {
            "street_number": "1",
            "street_name": "Hackathon Blvd",
            "city": "Austin",
            "state": "TX",
            "zip": "73301"
        }
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(f"{BASE_URL}/customers?key={NESSIE_API_KEY}", json=payload)
        res.raise_for_status()
        return res.json()["objectCreated"]

# Create a default checking account
async def create_nessie_account(customer_id: str, name: str):
    payload = {
        "type": "Checking",
        "nickname": f"{name}'s Account",
        "rewards": 0,
        "balance": 500
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BASE_URL}/customers/{customer_id}/accounts?key={NESSIE_API_KEY}",
            json=payload
        )
        res.raise_for_status()
        return res.json()["objectCreated"]

# Fetch Nessie account balance
async def get_nessie_account_balance(account_id: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{BASE_URL}/accounts/{account_id}?key={NESSIE_API_KEY}")
        res.raise_for_status()
        data = res.json()
        return data["balance"]

# Fetch available merchants
async def list_merchants(limit: int = 5):
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{BASE_URL}/merchants?key={NESSIE_API_KEY}")
        res.raise_for_status()
        merchants = res.json()
        return merchants[:limit]  # limit for simplicity


# Make a purchase at a merchant
async def nessie_make_purchase(account_id: str, merchant_id: str, amount: float, description: str = "Purchase"):
    payload = {
        "merchant_id": merchant_id,
        "medium": "balance",
        "purchase_date": "2025-10-18",
        "amount": amount,
        "status": "pending",
        "description": description
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BASE_URL}/accounts/{account_id}/purchases?key={NESSIE_API_KEY}",
            json=payload
        )
        res.raise_for_status()
        return res.json()["objectCreated"]

# Withdraw money from a user's account
async def nessie_withdraw(account_id: str, amount: float, description: str = "Transfer out"):
    payload = {
        "medium": "balance",
        "transaction_date": "2025-10-18",
        "status": "pending",
        "amount": amount,
        "description": description
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BASE_URL}/accounts/{account_id}/withdrawals?key={NESSIE_API_KEY}",
            json=payload
        )
        res.raise_for_status()
        return res.json()["objectCreated"]
    
# Deposit money into a user's account
async def nessie_deposit(account_id: str, amount: float, description: str = "Transfer in"):
    payload = {
        "medium": "balance",
        "transaction_date": "2025-10-18",
        "status": "pending",
        "amount": amount,
        "description": description
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BASE_URL}/accounts/{account_id}/deposits?key={NESSIE_API_KEY}",
            json=payload
        )
        res.raise_for_status()
        return res.json()["objectCreated"]