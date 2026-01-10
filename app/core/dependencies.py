# internal imports
from app.core.config import settings

# external imports
from jose import jwt, JWTError
from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from .database import get_db
from app.models.user import User, UserRole


# OAuth2 scheme for token authentication
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")


# Type aliases for cleaner code
DBSession = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(oauth2_bearer)]

def get_current_user(token: TokenDep):
    """Extract and validate user from JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get('email', '')
        user_id: str = payload.get('user_id', '')
        user_role: str = payload.get('role', '')
        is_active: bool = payload.get('is_active', '')
        full_name: str = payload.get('full_name', '')
        password_hash: str = payload.get('password_hash', '')
        phone: str = payload.get('phone', '')

        if email is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user"
            )
        return User(
            id=UUID(user_id),
            email=email,
            role=UserRole(user_role),
            full_name=full_name,
            is_active=is_active,
            password_hash=password_hash,
            phone=phone
        )
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate user: {err}"
        )

# Type alias for current user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_user(current_user: CurrentUser) -> User:
    """
    Verify that the current user is active.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if active
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(allowed_roles: list[UserRole]):
    """
    Dependency factory to check if user has required role.
    
    Usage:
        @app.get("/admin/users", dependencies=[Depends(require_role([UserRole.ADMIN]))])
        
    Args:
        allowed_roles: List of allowed user roles
        
    Returns:
        Dependency function that validates user role
    """
    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {[r.value for r in allowed_roles]}"
            )
        return current_user
    
    return role_checker


# Convenience dependencies for specific roles
def wholesaler_only(current_user: CurrentUser) -> User:
    """Dependency to ensure user is a wholesaler"""
    if current_user.role != UserRole.WHOLESALER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only wholesalers can access this endpoint"
        )
    return current_user


def distributor_only(current_user: CurrentUser) -> User:
    """Dependency to ensure user is a distributor"""
    if current_user.role != UserRole.DISTRIBUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only distributors can access this endpoint"
        )
    return current_user


def admin_only(current_user: CurrentUser) -> User:
    """Dependency to ensure user is an admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access this endpoint"
        )
    return current_user


# Type aliases for role-specific dependencies
WholesalerUser = Annotated[User, Depends(wholesaler_only)]
DistributorUser = Annotated[User, Depends(distributor_only)]
AdminUser = Annotated[User, Depends(admin_only)]


class Pagination:
    """
    Pagination dependency for list endpoints.
    
    Usage:
        @app.get("/items")
        def get_items(pagination: Pagination = Depends()):
            skip = pagination.skip
            limit = pagination.limit
    """
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100
    ):
        self.page = max(1, page)
        self.page_size = min(page_size, max_page_size)
        self.skip = (self.page - 1) * self.page_size
        self.limit = self.page_size
    
    @property
    def offset(self) -> int:
        """Alias for skip"""
        return self.skip


# Type alias for pagination dependency
PaginationDep = Annotated[Pagination, Depends()]
