from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
import uuid

if TYPE_CHECKING:
    from .order import Order
    from .product import Product
    from .notification import Notification
    from .payment import Payment
    from .wholesaler_profile import WholesalerProfile
    from .distributor_profile import DistributorProfile
    from .cart import Cart


class UserRole(str, Enum):
    WHOLESALER = "wholesaler"
    DISTRIBUTOR = "distributor"
    ADMIN = "admin"


class User(SQLModel, table=True):
    __tablename__ = "users" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)
    full_name: str = Field(nullable=False)
    phone: str = Field(nullable=False)
    role: UserRole = Field(nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    orders_as_wholesaler: list["Order"] = Relationship(
        back_populates="wholesaler",
        sa_relationship_kwargs={"foreign_keys": "Order.wholesaler_id"}
    )
    orders_as_distributor: list["Order"] = Relationship(
        back_populates="distributor",
        sa_relationship_kwargs={"foreign_keys": "Order.distributor_id"}
    )
    products: list["Product"] = Relationship(back_populates="distributor")
    notifications: list["Notification"] = Relationship(back_populates="user")
    payments_verified: list["Payment"] = Relationship(back_populates="verified_by")
    
    # Profile relationships
    wholesaler_profile: Optional["WholesalerProfile"] = Relationship(back_populates="user")
    distributor_profile: Optional["DistributorProfile"] = Relationship(back_populates="user")
    
    # Cart relationship (for wholesalers)
    cart: Optional["Cart"] = Relationship(back_populates="wholesaler")
