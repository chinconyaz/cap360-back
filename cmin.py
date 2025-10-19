from typing import Dict
from models import Member
import json
from fastapi.encoders import jsonable_encoder

import database
plain = jsonable_encoder(database.members_db)
json_str = json.dumps(plain)
print(json_str)

# read from disk
data = json.loads(json_str)
members = {k: Member.model_validate(v) for k, v in data.items()}
print(database.members_db)