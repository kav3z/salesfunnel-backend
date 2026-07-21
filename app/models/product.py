from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON
from decimal import Decimal
import uuid

if TYPE_CHECKING:
    from .user import User
    from .order_item import OrderItem
    from .cart import CartItem
    from .category import Category


class Product(SQLModel, table=True):
    __tablename__ = "products" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sku: str = Field(unique=True, index=True, nullable=False)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    price_per_case: Decimal = Field(
        nullable=False,
        decimal_places=2,
        max_digits=16
    )
    stock_quantity: int = Field(default=0, nullable=False)
    distributor_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    
    # Existing string field (consider removing later if replacing with relation)
    category: Optional[str] = Field(default=None)
    category_id: Optional[uuid.UUID] = Field(default=None, foreign_key="categories.id")
    
    dimensions: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="Product dimensions as {'length': L, 'width': W, 'height': H} in cm")
    weight: Optional[int] = Field(default=None, nullable=True, description="Product weight in grams")

    image_url: Optional[str] = Field(default=None)
    is_available: bool = Field(default=True)
    is_deleted: bool = Field(default=False)  # Added field
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Many-to-one relationship with category
    category_rel: Optional["Category"] = Relationship(back_populates="products")
    
    # Relationships
    distributor: "User" = Relationship(back_populates="products")
    order_items: list["OrderItem"] = Relationship(back_populates="product")
    cart_items: list["CartItem"] = Relationship(back_populates="product")
