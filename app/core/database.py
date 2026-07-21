from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from .config import settings

# Import ALL models before creating tables
from app.models.user import User
from app.models.order import Order
from app.models.cart import Cart, CartItem
from app.models.audit_log import AuditLog
from app.models.distributor_profile import DistributorProfile
from app.models.notification import Notification
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.wholesaler_profile import WholesalerProfile
from app.models.category import Category
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,
    pool_recycle=1800,
)

print(settings.DATABASE_URL)
from sqlalchemy import text


def create_db_and_tables():
    """
    Create all database tables based on SQLModel models.
    This should be called on application startup.
    """
    SQLModel.metadata.create_all(engine)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'COMPLETED';"))
            conn.execute(text("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'completed';"))
            conn.execute(text("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'PENDING';"))
            conn.execute(text("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'pending';"))
            conn.execute(text("ALTER TABLE wholesaler_profiles ADD COLUMN IF NOT EXISTS has_submitted_documents BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE distributor_profiles ADD COLUMN IF NOT EXISTS has_submitted_documents BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE orders ALTER COLUMN total_amount TYPE NUMERIC(16, 2);"))
            conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS mode_of_transport VARCHAR(255) NULL;"))
            conn.execute(text("ALTER TABLE order_items ALTER COLUMN unit_price TYPE NUMERIC(16, 2);"))
            conn.execute(text("ALTER TABLE order_items ALTER COLUMN subtotal TYPE NUMERIC(16, 2);"))
            conn.execute(text("ALTER TABLE products ALTER COLUMN price_per_case TYPE NUMERIC(16, 2);"))
            conn.execute(text("ALTER TABLE payments ALTER COLUMN amount TYPE NUMERIC(16, 2);"))
            conn.execute(text("ALTER TABLE wallets ALTER COLUMN balance TYPE NUMERIC(16, 2);"))
            conn.execute(text("ALTER TABLE wallet_transactions ALTER COLUMN amount TYPE NUMERIC(16, 2);"))
            conn.commit()
    except Exception as e:
        print(f"Migration check notice: {e}")


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

