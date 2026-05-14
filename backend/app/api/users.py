from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import UserResponse, UserPreferenceUpdate, UserUpdate, PasswordChange
from app.core.security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", summary="Get current user profile", response_model=UserResponse)
async def get_profile(current_user: CurrentUser):
    return UserResponse.model_validate(current_user)


@router.put("/me", summary="Update user profile", response_model=UserResponse)
async def update_profile(
    payload: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.put("/me/password", summary="Change password", status_code=204)
async def change_password(
    payload: PasswordChange,
    current_user: CurrentUser,
    db: DbSession,
):
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少需要6个字符")
    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()


@router.put("/me/preferences", summary="Update user preferences", response_model=UserResponse)
async def update_preferences(
    payload: UserPreferenceUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    current_user.preferences = payload.preferences
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
