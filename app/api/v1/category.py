from typing import List
from fastapi import APIRouter, HTTPException, status, Request
from sqlmodel import  select
import uuid

# Adjust these imports based on your actual project structure
from app.core.dependencies import DBSession
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead

v1_category = APIRouter(prefix="/v1", tags=['v1_category'])

db_dependency = DBSession

@v1_category.post("/", status_code=status.HTTP_201_CREATED)
async def create_category(db: db_dependency, category: CategoryCreate):
    """
    Create a new category.
    """
    existing_category = db.exec(select(Category).where(Category.name == category.name)).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    new_category = Category(name=category.name)
    
    db.add(new_category)
    db.commit()
    db.refresh(new_category)

@v1_category.get("/", response_model=List[CategoryRead])
def list_categories(db: db_dependency, request: Request):
    """
    List all categories.
    """
    # Extract request data
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # You can log this or do something with it
    print(f"IP: {ip_address}, User-Agent: {user_agent}")
    
    categories = db.exec(select(Category)).all()
    return categories

@v1_category.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: uuid.UUID, db: db_dependency):
    """
    Delete a category by ID.
    """
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(category)
    db.commit()
    return None
