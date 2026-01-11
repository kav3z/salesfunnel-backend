from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from decimal import Decimal
import uuid

if TYPE_CHECKING:
    from .user import User
    from .order_item import OrderItem
    from .cart import CartItem


class Product(SQLModel, table=True):
    __tablename__ = "products" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sku: str = Field(unique=True, index=True, nullable=False)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    price_per_case: Decimal = Field(
        nullable=False,
        decimal_places=2,
        max_digits=10
    )
    stock_quantity: int = Field(default=0, nullable=False)
    distributor_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    category: Optional[str] = Field(default=None)
    image_url: Optional[str] = Field(default=None)
    is_available: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    distributor: "User" = Relationship(back_populates="products")
    order_items: list["OrderItem"] = Relationship(back_populates="product")
    cart_items: list["CartItem"] = Relationship(back_populates="product")
