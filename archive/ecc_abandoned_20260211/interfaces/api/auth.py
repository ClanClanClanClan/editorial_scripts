"""Authentication API endpoints with basic JWT and roles."""

import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.ecc.infrastructure.runtime_flags import use_real_deps

try:
    from jose import JWTError, jwt  # type: ignore
except Exception as _e:  # pragma: no cover
    if use_real_deps():
        raise

    class _JWTError(Exception):
        pass

    class _jwt:
        @staticmethod
        def encode(payload: dict[str, Any], key: str, algorithm: str = "HS256") -> str:
            # Minimal dev-only stub: NOT SECURE
            return "stub." + str(payload.get("sub", "user"))

        @staticmethod
        def decode(token: str, key: str, algorithms: list[str] | None = None) -> dict[str, Any]:
            # Minimal stub decode: NOT SECURE
            return {"sub": "stub", "uid": "stub", "roles": ["editor"]}

    jwt = _jwt()
    JWTError = _JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select

from src.ecc.infrastructure.database.connection import get_database_manager
from src.ecc.infrastructure.database.models import UserModel

router = APIRouter()
security = HTTPBearer()

# JWT config
SECRET_KEY = os.getenv("ECC_SECRET_KEY", "devsecret_change_me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ECC_ACCESS_TOKEN_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    roles: list[str]


class UserInfo(BaseModel):
    user_id: str
    username: str
    email: str
    roles: list[str]
    created_at: datetime
    last_login: datetime | None = None


# Demo users fallback (dev only)
USERS = {
    "admin": {
        "user_id": "admin-001",
        "username": "admin",
        "email": "admin@ecc.local",
        "password_hash": pwd_context.hash("admin"),
        "roles": ["admin", "editor"],
        "created_at": datetime.now(),
        "last_login": None,
    },
    "editor": {
        "user_id": "editor-001",
        "username": "editor",
        "email": "editor@ecc.local",
        "password_hash": pwd_context.hash("editor"),
        "roles": ["editor"],
        "created_at": datetime.now(),
        "last_login": None,
    },
}

ACTIVE_TOKENS: dict[str, dict] = {}


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bool(pwd_context.verify(plain_password, password_hash))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return str(token)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    # Try DB-backed users first
    try:
        dbm = await get_database_manager()
        async with dbm.get_session() as session:
            res = await session.execute(
                select(UserModel).where(UserModel.username == request.username)
            )
            db_user = res.scalar_one_or_none()
            if db_user and verify_password(request.password, db_user.password_hash):
                access_token = create_access_token(
                    data={
                        "sub": db_user.username,
                        "uid": str(db_user.id),
                        "roles": db_user.roles or [],
                    }
                )
                return TokenResponse(
                    access_token=access_token,
                    expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    user_id=str(db_user.id),
                    username=db_user.username,
                    roles=db_user.roles or [],
                )
    except Exception as e:
        # In minimal envs, DB may be unavailable; fall back to demo users
        if use_real_deps():
            raise e
        # otherwise, continue to fallback

    # Fallback to in-memory demo users (dev only)
    user = USERS.get(request.username)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(
        data={"sub": user["username"], "uid": user["user_id"], "roles": user["roles"]}
    )
    USERS[request.username]["last_login"] = datetime.now()
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user["user_id"],
        username=user["username"],
        roles=user["roles"],
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserInfo:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        uid: str = payload.get("uid")
        roles: list[str] = payload.get("roles", [])
        if username is None or uid is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

    user = USERS.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return UserInfo(
        user_id=user["user_id"],
        username=user["username"],
        email=user["email"],
        roles=roles,
        created_at=user["created_at"],
        last_login=user["last_login"],
    )


def require_roles(required: list[str]):
    async def _role_checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if not any(r in user.roles for r in required):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _role_checker


@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return user


@router.get("/validate")
async def validate(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, bool]:
    # If decode passes in dependency, token is valid
    _ = await get_current_user(credentials)
    return {"valid": True}


async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
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
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Required role: {required_role}"
            )
        return user

    return role_checker
