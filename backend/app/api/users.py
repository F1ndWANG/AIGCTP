from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserPreferenceUpdate, UserUpdate, PasswordChange
from app.core.security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.put("/me/password", status_code=204)
async def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少需要6个字符")
    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()


@router.put("/me/preferences", response_model=UserResponse)
async def update_preferences(
    payload: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.preferences = payload.preferences
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
