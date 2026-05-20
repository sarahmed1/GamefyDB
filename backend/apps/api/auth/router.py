from fastapi import APIRouter, Depends

from backend.apps.api.auth.backend import auth_backend, fastapi_users
from backend.apps.api.deps import current_active_user
from backend.apps.api.models import User
from backend.apps.api.schemas import UserRead


def build_auth_router() -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    # /auth/login and /auth/logout from fastapi-users
    router.include_router(fastapi_users.get_auth_router(auth_backend))

    @router.get("/me", response_model=UserRead)
    async def me(user: User = Depends(current_active_user)) -> User:
        return user

    return router




