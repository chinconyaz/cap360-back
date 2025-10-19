from fastapi import APIRouter, HTTPException
from models import Family
import database
import uuid

router = APIRouter()

@router.post("/")
def create_family(name: str):
    # Create a new family and store it in the database
    fid = str(uuid.uuid4())
    new_family = Family(id=fid, name=name)

    database.families_db[fid] = new_family
    return {"family_id": fid, "message": "Family created successfully"}

@router.get("/{family_id}")
def get_family(family_id: str):
    family = database.families_db.get(family_id)
    if not family:
        raise HTTPException(404, "Family not found")
    return family

@router.get("/get_members/{family_id}")
def get_family_members(family_id: str):
    if database.families_db.get(family_id) is None:
        raise HTTPException(404, "Family not found")
    
    members = [database.members_db[member_id] for member_id in database.families_db[family_id].members]
    return {"family_id": family_id, "members": members}