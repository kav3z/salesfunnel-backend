from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from .config import settings

# Import ALL models before creating tables
from app.models.user import User
from app.models.order import Order
from app.models.audit_log import AuditLog
from app.models.distributor_profile import DistributorProfile
from app.models.notification import Notification
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.wholesaler_profile import WholesalerProfile

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

print(settings.DATABASE_URL)
def create_db_and_tables():
    """
    Create all database tables based on SQLModel models.
    This should be called on application startup.
    """
    SQLModel.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Usage in FastAPI endpoints:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    
    Yields:
        Session: SQLModel database session
    """
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()


def init_db():
    """
    Initialize database with tables and seed data if needed.
    Call this function on application startup.
    """
    create_db_and_tables()

