# Local imports
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
from app.schemas.distributor import DistributorListResponse
from app.models.product import Product
from app.models.user import User, UserRole
from app.models.distributor_profile import DistributorProfile
from app.core.dependencies import get_current_user, DBSession, require_role

# External imports
from typing import Annotated, Optional, List
from uuid import UUID
from math import ceil
from datetime import datetime
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select, func


v1_distributor = APIRouter(prefix="/v1", tags=['v1_distributor'])

db_dependency = DBSession


@v1_distributor.get("/products", response_model=ProductListResponse, status_code=status.HTTP_200_OK)
async def get_all_products(
    db: db_dependency,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    distributor_id: Optional[UUID] = Query(default=None, description="Filter by distributor"),
    search: Optional[str] = Query(default=None, description="Search by product name"),
    available_only: bool = Query(default=True, description="Show only available products")
):
    """
    Retrieve a list of all products with optional filtering and pagination.
    
    This endpoint is used for the "All Products / Distributor Selection" view.
    
    Args:
        page: Page number for pagination
        page_size: Number of items per page
        category: Optional category filter
        distributor_id: Optional distributor filter
        search: Optional search term for product name
        available_only: If True, only return available products
    
    Returns:
        ProductListResponse: Paginated list of products
    """
    # Build base query
    query = select(Product)
    count_query = select(func.count()).select_from(Product)
    
    # Apply filters
    if available_only:
        query = query.where(Product.is_available == True)
        count_query = count_query.where(Product.is_available == True)
    
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)
    
    if distributor_id:
        query = query.where(Product.distributor_id == distributor_id)
        count_query = count_query.where(Product.distributor_id == distributor_id)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(Product.name.ilike(search_pattern)) # type: ignore
        count_query = count_query.where(Product.name.ilike(search_pattern)) # type: ignore
    
    # Get total count
    total = db.exec(count_query).one()
    
    # Calculate pagination
    total_pages = ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Apply pagination and ordering
    query = query.order_by(Product.created_at.desc()).offset(offset).limit(page_size) # type: ignore
    
    # Execute query
    products = db.exec(query).all()
    
    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@v1_distributor.post(
    "/distributors/{distributor_id}/products", 
    response_model=ProductResponse, 
    status_code=status.HTTP_201_CREATED
)
async def add_product_to_distributor_catalog(
    distributor_id: UUID,
    product_data: ProductCreate,
    db: db_dependency,
    current_user: User = Depends(get_current_user)
):
    """
    Add a new product to a distributor's catalog.
    
    This endpoint is restricted to Distributors (for their own catalog) and Admins.
    
    Args:
        distributor_id: UUID of the distributor
        product_data: Product creation data
    
    Returns:
        ProductResponse: The created product
        
    Raises:
        HTTPException 403: If user is not authorized to add products
        HTTPException 404: If distributor not found
        HTTPException 409: If SKU already exists
    """
    # Check authorization
    if current_user.role == UserRole.DISTRIBUTOR:
        # Distributors can only add products to their own catalog
        if current_user.id != distributor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only add products to your own catalog"
            )
    elif current_user.role != UserRole.ADMIN:
        # Only distributors and admins can add products
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only distributors and admins can add products"
        )
    
    # Verify distributor exists and has the correct role
    distributor = db.exec(
        select(User).where(User.id == distributor_id, User.role == UserRole.DISTRIBUTOR)
    ).first()
    
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    
    # Check if SKU already exists
    existing_product = db.exec(
        select(Product).where(Product.sku == product_data.sku)
    ).first()
    
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU '{product_data.sku}' already exists"
        )
    
    # Create new product
    new_product = Product(
        sku=product_data.sku,
        name=product_data.name,
        description=product_data.description,
        price_per_case=product_data.price_per_case,
        stock_quantity=product_data.stock_quantity,
        distributor_id=distributor_id,
        category=product_data.category,
        image_url=product_data.image_url,
        is_available=product_data.is_available
    )
    
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    return ProductResponse.model_validate(new_product)


@v1_distributor.get(
    "/distributors/{distributor_id}/products",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK
)
async def get_distributor_products(
    distributor_id: UUID,
    db: db_dependency,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    search: Optional[str] = Query(default=None, description="Search by product name"),
    available_only: bool = Query(default=False, description="Show only available products")
):
    """
    Retrieve a list of products for a specific distributor.
    
    This endpoint is used for the "Distributor Product Catalog" view.
    
    Args:
        distributor_id: UUID of the distributor
        page: Page number for pagination
        page_size: Number of items per page
        category: Optional category filter
        search: Optional search term for product name
        available_only: If True, only return available products
    
    Returns:
        ProductListResponse: Paginated list of distributor's products
    """
    # Verify distributor exists
    distributor = db.exec(
        select(User).where(User.id == distributor_id, User.role == UserRole.DISTRIBUTOR)
    ).first()
    
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    
    # Build base query filtered by distributor
    query = select(Product).where(Product.distributor_id == distributor_id)
    count_query = select(func.count()).select_from(Product).where(Product.distributor_id == distributor_id)
    
    # Apply filters
    if available_only:
        query = query.where(Product.is_available == True)
        count_query = count_query.where(Product.is_available == True)
    
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(Product.name.ilike(search_pattern)) # type: ignore
        count_query = count_query.where(Product.name.ilike(search_pattern)) # type: ignore
    
    # Get total count
    total = db.exec(count_query).one()
    
    # Calculate pagination
    total_pages = ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Apply pagination and ordering
    query = query.order_by(Product.created_at.desc()).offset(offset).limit(page_size) # type: ignore
    
    # Execute query
    products = db.exec(query).all()
    
    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@v1_distributor.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK
)
async def get_product_details(
    product_id: UUID,
    db: db_dependency
):
    """
    Retrieve details of a single product.
    
    This endpoint is used for the "Wholesaler Product Detail Page".
    
    Args:
        product_id: UUID of the product
    
    Returns:
        ProductResponse: Product details
        
    Raises:
        HTTPException 404: If product not found
    """
    product = db.exec(
        select(Product).where(Product.id == product_id)
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return ProductResponse.model_validate(product)


@v1_distributor.get(
    "/distributors",
    response_model=List[DistributorListResponse],
    status_code=status.HTTP_200_OK
)
async def get_all_distributors(
    db: db_dependency,
    verified_only: bool = Query(default=True, description="Show only verified distributors"),
    search: Optional[str] = Query(default=None, description="Search by business name")
):
    """
    Retrieve a list of all distributors.
    
    This endpoint returns all distributors including popular ones.
    
    Args:
        verified_only: If True, only return verified distributors
        search: Optional search term for business name
    
    Returns:
        List[DistributorListResponse]: List of distributors
    """
    # Build query for distributor profiles
    query = select(DistributorProfile)
    
    # Apply filters
    if verified_only:
        query = query.where(DistributorProfile.is_verified == True)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(DistributorProfile.business_name.ilike(search_pattern)) # type: ignore
    
    # Order by business name
    query = query.order_by(DistributorProfile.business_name)
    
    # Execute query
    distributors = db.exec(query).all()
    
    return [
        DistributorListResponse(
            id=str(d.id),
            business_name=d.business_name,
            business_address=d.business_address,
            business_phone=d.business_phone,
            business_email=d.business_email,
            is_verified=d.is_verified
        )
        for d in distributors
    ]


@v1_distributor.put(
    "/distributors/{distributor_id}/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK
)
async def update_distributor_product(
    distributor_id: UUID,
    product_id: UUID,
    product_data: ProductUpdate,
    db: db_dependency,
    current_user: User = Depends(get_current_user)
):
    """
    Update product details for a distributor's catalog.
    
    This endpoint is restricted to Distributors (for their own products) and Admins.
    
    Args:
        distributor_id: UUID of the distributor
        product_id: UUID of the product to update
        product_data: Product update data
    
    Returns:
        ProductResponse: Updated product details
        
    Raises:
        HTTPException 403: If user is not authorized to update products
        HTTPException 404: If distributor or product not found
    """
    # Check authorization
    if current_user.role == UserRole.DISTRIBUTOR:
        if current_user.id != distributor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update products in your own catalog"
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only distributors and admins can update products"
        )
    
    # Verify distributor exists
    distributor = db.exec(
        select(User).where(User.id == distributor_id, User.role == UserRole.DISTRIBUTOR)
    ).first()
    
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    
    # Find the product
    product = db.exec(
        select(Product).where(
            Product.id == product_id,
            Product.distributor_id == distributor_id
        )
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in this distributor's catalog"
        )
    
    # Update only provided fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Update timestamp
    product.updated_at = datetime.utcnow()
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@v1_distributor.delete(
    "/distributors/{distributor_id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_distributor_product(
    distributor_id: UUID,
    product_id: UUID,
    db: db_dependency,
    current_user: User = Depends(get_current_user)
):
    """
    Remove a product from a distributor's catalog.
    
    This endpoint is restricted to Distributors (for their own products) and Admins.
    
    Args:
        distributor_id: UUID of the distributor
        product_id: UUID of the product to remove
        
    Raises:
        HTTPException 403: If user is not authorized to delete products
        HTTPException 404: If distributor or product not found
    """
    # Check authorization
    if current_user.role == UserRole.DISTRIBUTOR:
        if current_user.id != distributor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete products from your own catalog"
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only distributors and admins can delete products"
        )
    
    # Verify distributor exists
    distributor = db.exec(
        select(User).where(User.id == distributor_id, User.role == UserRole.DISTRIBUTOR)
    ).first()
    
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    
    # Find the product
    product = db.exec(
        select(Product).where(
            Product.id == product_id,
            Product.distributor_id == distributor_id
        )
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in this distributor's catalog"
        )
    
    db.delete(product)
    db.commit()
    
    return None

