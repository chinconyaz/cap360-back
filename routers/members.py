from fastapi import APIRouter, HTTPException
from models import Member, Transaction, MoneyRequest
import database
import httpx, uuid, os
from dotenv import load_dotenv
from typing import Optional

from routers.nessie import create_nessie_customer
from datetime import datetime

router = APIRouter()
load_dotenv()

NESSIE_API_KEY = os.getenv("NESSIE_API_KEY")
BASE_URL = "http://api.nessieisreal.com"

router = APIRouter()

@router.post('/register')
async def create_member(first_name_temp: str, last_name_temp: str):
    first_name = first_name_temp
    last_name = last_name_temp

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

    database.members_db[mid] = member

    database.members_db[mid].nessie_customer_id = nessie_customer_id
    database.members_db[mid].nessie_account_id.append(nessie_account)

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

    family.members.append(member.id)
    database.members_db.get(member_id).family_id = family_id
    return {"message": "f{member.first_name} {member.last_name} added to {family.name} family"}

@router.get("/{member_id}/transactions")
def get_member_transactions(member_id: str):
    member = database.members_db.get(member_id)
    return member.transactions

@router.get("/{member_id}/borrower_transactions")
def get_borrower_transactions(member_id: str):
    member = database.members_db.get(member_id)

    return member.tracked_transactions

@router.get("/thegoat/bakra")
def get_bakra():
    for member_id, member in database.members_db.items():
        print(member.first_name)
        if member.first_name == "Aiyaz":
            return member
        
    raise HTTPException(404, "Bakra not found")

@router.get("/thegoat/cakra")
def get_bakra():
    for member_id, member in database.members_db.items():
        print(member.first_name)
        if member.first_name == "Chinmay":
            return member
        
    raise HTTPException(404, "Cakra not found")

@router.get("/thegoat/dakra")
def get_bakra():
    for member_id, member in database.members_db.items():
        print(member.first_name)
        if member.first_name == "Connor":
            return member
        
    raise HTTPException(404, "Dakra not found")

@router.get("/{member_id}/get_indebted_to")
def get_indebted_to(member_id: str):
    member = database.members_db.get(member_id)
    return member.debts