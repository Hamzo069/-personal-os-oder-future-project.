from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DBDep, SettingsDep, StorageDep
from app.core.errors import UnauthorizedError
from app.core.security import verify_password
from app.schemas.auth import DeleteAccountRequest, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserUpdate, user: CurrentUser, db: DBDep) -> UserRead:
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    payload: DeleteAccountRequest,
    user: CurrentUser,
    db: DBDep,
    storage: StorageDep,
    settings: SettingsDep,
    response: Response,
) -> Response:
    """GDPR-style account deletion: removes the user, all rows and uploaded files."""
    if not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Password is incorrect")
    storage.delete_user_files(user.id)
    db.delete(user)  # ON DELETE CASCADE removes the user's data
    db.commit()
    response.delete_cookie(key=settings.refresh_cookie_name, path=f"{settings.api_v1_prefix}/auth")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
