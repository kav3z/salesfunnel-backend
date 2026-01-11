from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from decimal import Decimal
import uuid

if TYPE_CHECKING:
    from .user import User
    from .product import Product


class Cart(SQLModel, table=True):
    __tablename__ = "carts"  # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wholesaler_id: uuid.UUID = Field(foreign_key="users.id", unique=True, nullable=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    wholesaler: "User" = Relationship(back_populates="cart")
    items: list["CartItem"] = Relationship(back_populates="cart", cascade_delete=True)


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"  # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cart_id: uuid.UUID = Field(foreign_key="carts.id", nullable=False, index=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", nullable=False, index=True)
    quantity: int = Field(nullable=False, gt=0)
    added_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    cart: "Cart" = Relationship(back_populates="items")
    product: "Product" = Relationship(back_populates="cart_items")
