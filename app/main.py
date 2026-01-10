# internal imports
from .api.v1.auth import v1_auth
from .core.database import init_db

# external imports
from fastapi import FastAPI

init_db()

app = FastAPI(
    title="SalesFunnel", 
    description="A platform that connects distributors with wholesalers"
    )

app.include_router(v1_auth)


