from fastapi import Depends, HTTPException, status

from backend.apps.api.auth.backend import fastapi_users
from backend.apps.api.models import User

current_active_user = fastapi_users.current_user(active=True)


async def require_admin(user: User = Depends(current_active_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user




