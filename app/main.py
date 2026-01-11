# internal imports
from .api.v1.auth import v1_auth
from .api.v1.distributor import v1_distributor
from .api.v1.wholesaler import v1_wholesaler
from .api.v1.admin import v1_admin
from .core.database import init_db

# external imports
from fastapi import FastAPI

init_db()

app = FastAPI(
    title="SalesFunnel", 
    description="A platform that connects distributors with wholesalers"
    )

app.include_router(v1_auth)
app.include_router(v1_admin)
app.include_router(v1_distributor)
app.include_router(v1_wholesaler)



