import uuid

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

from api.auth.manager import get_user_manager
from api.config import get_settings
from api.models import User

_settings = get_settings()


cookie_transport = CookieTransport(
    cookie_name=_settings.cookie_name,
    cookie_max_age=_settings.cookie_max_age,
    cookie_httponly=True,
    cookie_samesite="lax",
    cookie_secure=_settings.cookie_secure,
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=_settings.secret, lifetime_seconds=_settings.cookie_max_age, algorithm="HS256")


auth_backend = AuthenticationBackend(
    name="cookie-jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
