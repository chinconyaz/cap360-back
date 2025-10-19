from __future__ import annotations
import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MemberCreate(BaseModel):
    first_name: str
    last_name: str

class Member(BaseModel):
    id: str
    first_name: str
    last_name: str
    balance: float = 0.0
    nessie_customer_id: Optional[str] = None
    nessie_account_id: List[Dict[str, Any]] = Field(default_factory=list)
    transactions: List[str] = Field(default_factory=list)
    debts: Dict[str, float] = Field(default_factory=dict)            # {lender_id: amount_owed}
    transactions_visible_to: Dict[str, Any] = Field(default_factory=dict)
    family_id: Optional[str] = None

class Transaction(BaseModel):
    id: str
    from_id: str
    to_id: str
    amount: float
    date: datetime.datetime = Field(default_factory=datetime.datetime.now)  # evaluated per-instance
    description: Optional[str] = None
    settled: bool = False

class Family(BaseModel):
    id: str
    name: str
    members: List[Member] = Field(default_factory=list)
    transactions: List[Transaction] = Field(default_factory=list)

class Merchants(BaseModel):
    id: str
    nessie_id: Optional[str] = None
    name: str
    category: str
    location: str

class Purchase(BaseModel):
    id: str
    member_id: str
    merchant_id: str
    amount: float
    description: Optional[str] = None

class MoneyRequest(BaseModel):
    id: str
    from_id: str
    to_id: str      
    amount: float
    date: datetime.datetime = Field(default_factory=datetime.datetime.now)
    status: str = "pending"
    description: Optional[str] = None