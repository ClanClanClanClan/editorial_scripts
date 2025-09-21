"""User management endpoints (admin-only)."""

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ecc.infrastructure.database.connection import get_database_manager
from src.ecc.infrastructure.database.models import UserModel
from src.ecc.interfaces.api.auth import require_roles

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)
    roles: list[str] = Field(default_factory=list)


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    roles: list[str]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    db_manager = await get_database_manager()
    async with db_manager.get_session() as session:
        yield session


@router.post("/", response_model=UserResponse, dependencies=[Depends(require_roles(["admin"]))])
async def create_user(
    req: CreateUserRequest, db: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    # Check existing username/email
    existing = (
        await db.execute(
            select(UserModel).where(
                (UserModel.username == req.username) | (UserModel.email == req.email)
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="User with same username or email exists")
    user = UserModel(
        username=req.username,
        email=req.email,
        password_hash=pwd_context.hash(req.password),
        roles=req.roles or [],
    )
    db.add(user)
    await db.flush()
    return UserResponse(
        id=UUID(str(user.id)), username=user.username, email=user.email, roles=user.roles
    )


@router.get(
    "/", response_model=list[UserResponse], dependencies=[Depends(require_roles(["admin"]))]
)
async def list_users(db: AsyncSession = Depends(get_db_session)) -> list[UserResponse]:
    rows = (await db.execute(select(UserModel))).scalars().all()
    return [
        UserResponse(id=UUID(str(u.id)), username=u.username, email=u.email, roles=u.roles or [])
        for u in rows
    ]


class UpdateRolesRequest(BaseModel):
    roles: list[str]


@router.patch(
    "/{user_id}/roles",
    response_model=UserResponse,
    dependencies=[Depends(require_roles(["admin"]))],
)
async def update_roles(
    user_id: UUID, req: UpdateRolesRequest, db: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    user = (await db.execute(select(UserModel).where(UserModel.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.roles = req.roles
    await db.flush()
    return UserResponse(
        id=UUID(str(user.id)), username=user.username, email=user.email, roles=user.roles
    )


@router.delete("/{user_id}", dependencies=[Depends(require_roles(["admin"]))])
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
    await db.execute(delete(UserModel).where(UserModel.id == user_id))
    return {"status": "deleted"}
