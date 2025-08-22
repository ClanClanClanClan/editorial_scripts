"""Authentication API endpoints - placeholder implementation."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str


class UserInfo(BaseModel):
    """User information model."""
    user_id: str
    username: str
    email: str
    roles: list[str]
    created_at: datetime
    last_login: Optional[datetime] = None


# Placeholder user database
USERS = {
    "admin": {
        "user_id": "admin-001",
        "username": "admin",
        "email": "admin@ecc.local",
        "password": "admin",  # In production, this would be hashed
        "roles": ["admin", "editor"],
        "created_at": datetime.now(),
        "last_login": None,
    },
    "editor": {
        "user_id": "editor-001", 
        "username": "editor",
        "email": "editor@ecc.local",
        "password": "editor",  # In production, this would be hashed
        "roles": ["editor"],
        "created_at": datetime.now(),
        "last_login": None,
    },
}

# In production, use proper JWT with secret keys
ACTIVE_TOKENS = {}


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.
    
    **Note**: This is a placeholder implementation for development.
    In production, this would:
    - Hash passwords properly
    - Use real JWT tokens
    - Integrate with proper user management
    - Support MFA/2FA
    
    Default users:
    - username: admin, password: admin (admin + editor roles)
    - username: editor, password: editor (editor role only)
    """
    # Validate credentials
    user = USERS.get(request.username)
    
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create token (placeholder - use proper JWT in production)
    token = f"ecc_token_{user['user_id']}_{datetime.now().timestamp()}"
    expires_in = 3600 * 24  # 24 hours
    expires_at = datetime.now() + timedelta(seconds=expires_in)
    
    # Store token (in production, use Redis or database)
    ACTIVE_TOKENS[token] = {
        "user_id": user["user_id"],
        "username": user["username"],
        "expires_at": expires_at,
        "roles": user["roles"],
    }
    
    # Update last login
    USERS[request.username]["last_login"] = datetime.now()
    
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user_id=user["user_id"],
        username=user["username"],
    )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user and invalidate token.
    """
    token = credentials.credentials
    
    if token in ACTIVE_TOKENS:
        del ACTIVE_TOKENS[token]
        return {"message": "Logged out successfully"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token"
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current user information from token.
    """
    token = credentials.credentials
    
    # Validate token
    token_data = ACTIVE_TOKENS.get(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if token is expired
    if datetime.now() > token_data["expires_at"]:
        del ACTIVE_TOKENS[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user info
    username = token_data["username"]
    user = USERS[username]
    
    return UserInfo(
        user_id=user["user_id"],
        username=user["username"], 
        email=user["email"],
        roles=user["roles"],
        created_at=user["created_at"],
        last_login=user["last_login"],
    )


@router.get("/validate")
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate token and return basic info.
    """
    token = credentials.credentials
    
    token_data = ACTIVE_TOKENS.get(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    if datetime.now() > token_data["expires_at"]:
        del ACTIVE_TOKENS[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    
    return {
        "valid": True,
        "user_id": token_data["user_id"],
        "username": token_data["username"],
        "roles": token_data["roles"],
        "expires_at": token_data["expires_at"],
    }


async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency to get current user from token.
    Use this in other endpoints that require authentication.
    """
    token = credentials.credentials
    
    token_data = ACTIVE_TOKENS.get(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if datetime.now() > token_data["expires_at"]:
        del ACTIVE_TOKENS[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


async def require_role(required_role: str):
    """
    Dependency factory to require specific roles.
    Usage: Depends(require_role("admin"))
    """
    async def role_checker(user: dict = Depends(get_current_user_dependency)):
        if required_role not in user["roles"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
        return user
    return role_checker