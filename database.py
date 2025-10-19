import json
from typing import Dict, Any, Optional, Type
from models import Family, Member, Merchants, Purchase, MoneyRequest, Transaction
from pathlib import Path
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder

from uuid import uuid4

families_db: Dict[str, Family] = {}
members_db: Dict[str, Member] = {}
transactions_db: Dict[str, Transaction] = {}
merchants_db: Dict[str, dict] = {}
purchases_db: Dict[str, dict] = {}
money_requests_db: Dict[str, MoneyRequest] = {}

def seed_data():
    member_one = Member(
        id=str(uuid4()),
        first_name="Chinmay",
        last_name="Mangalwedhe",
        balance=500.0
    )
    
    member_two = Member(
        id=str(uuid4()),
        first_name="Aiyaz",
        last_name="Mostofa",
        balance=500.0
    )
    
    member_three = Member(
        id=str(uuid4()),
        first_name="Connor",
        last_name="Carey",
        balance=500.0
    )
    
    hacktx_fam = Family(
        id=str(uuid4()),
        name="Chinconyaz",
        members=[member_one, member_two, member_three],
        transactions=[]
    )
    
    member_one.family_id = hacktx_fam.id
    member_two.family_id = hacktx_fam.id
    member_three.family_id = hacktx_fam.id
    
    families_db[hacktx_fam.id] = hacktx_fam
    members_db[member_one.id] = member_one
    members_db[member_two.id] = member_two
    members_db[member_three.id] = member_three
    
    merchant_one = Merchants(
        id=str(uuid4()),
        name="Amazon",
        category="Shopping",
        location="Austin, TX"
    )
    
    merchant_two = Merchants(
        id=str(uuid4()),
        name="Walmart",
        category="Grocery",
        location="College Station, TX"
    )
    
    merchants_db[merchant_one.id] = merchant_one
    merchants_db[merchant_two.id] = merchant_two

    req = MoneyRequest(
        id=str(uuid4()),
        from_id=member_one.id,
        to_id=member_two.id,
        amount=50.0,
        status="pending"
    )

    money_requests_db[req.id] = req

def read_json_file(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def write_json_file(path: str, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def _to_plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    return value

def load_mapping(path: str, model: Optional[Type[BaseModel]] = None) -> Dict[str, Any]:
    raw = read_json_file(path)
    if not raw:
        return {}
    if model is None:
        return raw
    return {k: model.model_validate(v) for k, v in raw.items()}

def save_mapping(path: str, mapping: Dict[str, Any]) -> None:
    plain = {k: _to_plain(v) for k, v in mapping.items()}
    write_json_file(path, plain)

def init():
    if not Path("data").is_dir():
        return
    global members_db, families_db, merchants_db, purchases_db, money_requests_db, transactions_db
    members_db = load_mapping("data/members.json", Member)
    families_db = load_mapping("data/families.json", Family)
    merchants_db = load_mapping("data/merchants.json", Merchants)
    purchases_db = load_mapping("data/purchases.json", Purchase)
    money_requests_db = load_mapping("data/money_requests.json", MoneyRequest)
    transactions_db = load_mapping("data/transactions.json", Transaction)

def sync():
    Path("data").mkdir(parents=True, exist_ok=True)
    save_mapping("data/members.json", members_db)
    save_mapping("data/families.json", families_db)
    save_mapping("data/merchants.json", merchants_db)
    save_mapping("data/purchases.json", purchases_db)
    save_mapping("data/money_requests.json", money_requests_db)
    save_mapping("data/transactions.json", transactions_db)