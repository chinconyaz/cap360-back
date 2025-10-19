from pathlib import Path
from fastapi import FastAPI, Request
from routers import family, members, merchants, requests
import database
import os

app = FastAPI(
    title="CrediBridge API",
    description="Backend for P2P Family Lending App",
    version="1.0",
    docs_url="/docs"
)

app.include_router(family.router, prefix="/family", tags=["Family"])
app.include_router(members.router, prefix="/members", tags=["Members"])
app.include_router(merchants.router, prefix='/merchants', tags=["Merchants"])
app.include_router(requests.router, prefix='/request', tags=["Money Requests"])

@app.on_event("startup")
async def on_startup():
    print("startup pid", os.getpid())
    database.init()
    if not Path("data").is_dir() or not any(Path("data").glob("*.json")):
        database.seed_data()  # create seeded members/families in-memory
    database.sync()

@app.middleware("http")
async def add_custom_header(request: Request, call_next):
    response = await call_next(request)
    database.sync()
    return response