from __future__ import annotations
import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Transaction(BaseModel):
    id: str
    type_transaction: str
    from_id: str
    to_id: str
    from_name: str
    to_name: str
    amount: float
    from_debt: float
    to_debt: float
    date: datetime.datetime = Field(default_factory=datetime.datetime.now)  # evaluated per-instance
    description: Optional[str] = None

class Member(BaseModel):
    id: str
    first_name: str
    last_name: str
    balance: float = 0.0
    nessie_customer_id: Optional[str] = None
    nessie_account_id: List[Dict[str, Any]] = Field(default_factory=list)
    transactions: List[Transaction] = Field(default_factory=list)
    debts: Dict[str, float] = Field(default_factory=dict)            # {lender_id: amount_owed}
    tracked_transactions: List[Transaction] = Field(default_factory=list)
    family_id: Optional[str] = None
    current_debt: float = 0.0
    requests: Dict[str, Any] = Field(default_factory=dict)          # {request_id: MoneyRequest}

class Family(BaseModel):
    id: str
    name: str
    members: List[str] = Field(default_factory=list)
    requests: List[MoneyRequest] = Field(default_factory=list)

class Merchants(BaseModel):
    id: str
    nessie_id: Optional[str] = None
    name: str
    category: str
    location: str

class MoneyRequest(BaseModel):
    id: str
    from_id: str
    to_id: Optional[str] = None
    amount: float
    date: datetime.datetime = Field(default_factory=datetime.datetime.now)
    status: str = "pending"
    description: Optional[str] = None