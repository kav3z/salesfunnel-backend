from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from decimal import Decimal
import uuid

if TYPE_CHECKING:
    from .order import Order
    from .product import Product


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="orders.id", nullable=False, index=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", nullable=False, index=True)
    quantity: int = Field(nullable=False, gt=0)
    unit_price: Decimal = Field(
        nullable=False,
        decimal_places=2,
        max_digits=10
    )
    subtotal: Decimal = Field(
        nullable=False,
        decimal_places=2,
        max_digits=10
    )
    
    # Relationships
    order: "Order" = Relationship(back_populates="order_items")
    product: "Product" = Relationship(back_populates="order_items")
