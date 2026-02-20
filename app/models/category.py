from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid

if TYPE_CHECKING:
    from .product import Product

class Category(SQLModel, table=True):
    __tablename__ = "categories" # type: ignore

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, index=True, nullable=False)
    
    products: list["Product"] = Relationship(back_populates="category_rel")
