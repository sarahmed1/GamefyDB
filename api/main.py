from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth.router import build_auth_router
from api.config import get_settings
from api.deps import require_admin
from api.models import User


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="GamefyDB API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(build_auth_router(), prefix="/api")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # TODO(phase-9): remove when real admin routes exist
    @app.get("/api/_admin_ping")
    async def admin_ping(user: User = Depends(require_admin)) -> dict[str, str]:
        return {"hello": user.email}

    return app


app = create_app()
