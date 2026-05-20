# Phase 1 — Backend Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `api/` FastAPI server with SQLite, async SQLAlchemy, `User` + `Job` models, cookie-based JWT auth via `fastapi-users`, role gating (admin/viewer), pytest harness, and an admin-seed script. End state: an admin can log in via cookie and a viewer is 403-blocked on admin-only routes.

**Architecture:** New `api/` package at repo root, imported as `api.main:app`. Async SQLAlchemy 2.x + `aiosqlite` for the user/job store (data pipeline files remain unchanged). `fastapi-users` provides login/logout; we expose `/auth/me` ourselves. `current_user` and `require_admin` dependencies guard routes. Alembic manages migrations.

**Tech Stack:** FastAPI, fastapi-users[sqlalchemy], SQLAlchemy 2.x async, aiosqlite, alembic, pydantic v2, pytest, pytest-asyncio, httpx (for TestClient).

**Notes for the implementer:**

- Python is NOT on PATH. Use the literal string `C:/Users/sarah/AppData/Local/Python/bin/python` (or set a shell variable `$PYTHON` at the top of your session) for every Python and pip command.
- All paths are absolute or relative to repo root `C:/Users/sarah/GamefyDB`.
- Commit after each task. Use the existing commit style (no Claude/Anthropic co-author trailer — see project memory).
- The spec is `docs/superpowers/specs/2026-05-18-frontend-stack-design.md`. Read § 3 (Repo Layout), § 5 (API Surface — auth section only for this phase), and § 6 (Auth Flow) before starting.

---

## File Structure

This phase creates the following files. Each has one responsibility:

```
api/
├── __init__.py              package marker, empty
├── main.py                  FastAPI app factory, router includes, lifespan, CORS
├── config.py                env/secret loading (SECRET, DB URL, COOKIE_SECURE)
├── db.py                    async engine, sessionmaker, Base, get_async_session
├── deps.py                  current_user, require_admin
├── models/
│   ├── __init__.py          re-exports User, Job
│   ├── user.py              User SQLAlchemy model (extends SQLAlchemyBaseUserTableUUID)
│   └── job.py               Job SQLAlchemy model
├── schemas/
│   ├── __init__.py
│   └── user.py              UserRead, UserCreate, UserUpdate (pydantic)
├── auth/
│   ├── __init__.py
│   ├── manager.py           UserManager, get_user_manager
│   ├── backend.py           cookie_transport, get_jwt_strategy, auth_backend, fastapi_users
│   └── router.py            assembles /auth/login, /auth/logout, /auth/me
├── alembic.ini              alembic config
├── alembic/
│   ├── env.py               async env wired to api.db
│   ├── script.py.mako       default
│   └── versions/            (initial migration written by alembic)
├── scripts/
│   └── seed_admin.py        creates initial admin user from env vars
└── tests/
    ├── __init__.py
    ├── conftest.py          test client, async session, fixtures (admin, viewer)
    ├── test_health.py
    ├── test_auth_login.py
    ├── test_auth_me.py
    └── test_require_admin.py
```

**Not created in this phase** (deferred to later phases): routers for facts/kpis/forecasts/chat/pipeline, services layer, data cache.

---

## Task 1: Install dependencies and create the package skeleton

**Files:**
- Modify: `requirements.txt`
- Create: `api/__init__.py`
- Create: `api/config.py`
- Create: `api/main.py`
- Create: `api/tests/__init__.py`
- Create: `api/tests/test_health.py`

- [ ] **Step 1: Append API dependencies to `requirements.txt`**

Open `requirements.txt` and append (do not reorder existing lines):

```
fastapi
uvicorn[standard]
fastapi-users[sqlalchemy]
sqlalchemy[asyncio]
aiosqlite
alembic
httpx
pytest-asyncio
pydantic-settings
```

- [ ] **Step 2: Install them**

Run:

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m pip install -r requirements.txt
```

Expected: all new packages install. If `fastapi-users` pulls in `pwdlib`/`bcrypt`, that is correct.

- [ ] **Step 3: Create the package skeleton**

Create `api/__init__.py` as an empty file.

Create `api/config.py`:

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="GAMEFYDB_", extra="ignore")

    secret: str = "dev-secret-change-me"
    database_url: str = "sqlite+aiosqlite:///./api/gamefydb.sqlite"
    cookie_name: str = "gamefydb_session"
    cookie_max_age: int = 60 * 60 * 24  # 24h
    cookie_secure: bool = False  # True in prod
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Create `api/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings


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

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

Create `api/tests/__init__.py` as an empty file.

- [ ] **Step 4: Write the health-check test**

Create `api/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from api.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_health.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Smoke-test the server manually**

Run (in a separate terminal):

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m uvicorn api.main:app --reload --port 8000
```

In another terminal:

```powershell
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok"}`. Stop the server with Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt api/__init__.py api/config.py api/main.py api/tests/
git commit -m "feat(api): scaffold FastAPI app with health endpoint"
```

---

## Task 2: Async SQLAlchemy engine and session

**Files:**
- Create: `api/db.py`

- [ ] **Step 1: Write `api/db.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from api.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_async_engine(_settings.database_url, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
```

- [ ] **Step 2: Smoke-check the import**

Run:

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -c "from api.db import engine, async_session_maker, Base; print('ok')"
```

Expected: `ok`. (No tests yet — the engine is exercised in Task 4 once models exist.)

- [ ] **Step 3: Commit**

```bash
git add api/db.py
git commit -m "feat(api): add async SQLAlchemy engine and session factory"
```

---

## Task 3: User model

**Files:**
- Create: `api/models/__init__.py`
- Create: `api/models/user.py`

- [ ] **Step 1: Create `api/models/user.py`**

```python
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    role: Mapped[str] = mapped_column(String(16), nullable=False, default="viewer")
```

`SQLAlchemyBaseUserTableUUID` already declares `id` (UUID PK), `email`, `hashed_password`, `is_active`, `is_superuser`, `is_verified`. We only add `role`.

- [ ] **Step 2: Create `api/models/__init__.py`**

```python
from api.models.user import User

__all__ = ["User"]
```

- [ ] **Step 3: Verify the import**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -c "from api.models import User; print(User.__tablename__)"
```

Expected: `users`.

- [ ] **Step 4: Commit**

```bash
git add api/models/
git commit -m "feat(api): add User model with role column"
```

---

## Task 4: Job model

**Files:**
- Create: `api/models/job.py`
- Modify: `api/models/__init__.py`

**Background:** `SQLAlchemyBaseUserTableUUID` stores `users.id` as a 36-char string on SQLite via `GUID`-style logic. We use the matching `String(36)` here for `Job.user_id` so the foreign key types align.

- [ ] **Step 1: Create `api/models/job.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


def _now() -> datetime:
    return datetime.utcnow()


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    log: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 2: Update `api/models/__init__.py`**

```python
from api.models.job import Job
from api.models.user import User

__all__ = ["Job", "User"]
```

- [ ] **Step 3: Verify**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -c "from api.models import User, Job; print(User.__tablename__, Job.__tablename__)"
```

Expected: `users jobs`.

- [ ] **Step 4: Commit**

```bash
git add api/models/
git commit -m "feat(api): add Job model"
```

---

## Task 5: Alembic setup and initial migration

**Files:**
- Create: `api/alembic.ini`
- Create: `api/alembic/env.py`
- Create: `api/alembic/script.py.mako`
- Create: `api/alembic/versions/` (directory)
- The migration file itself is generated by `alembic revision --autogenerate`.

- [ ] **Step 1: Initialize alembic in the `api/` folder**

`alembic init` creates the config alongside the scripts, so run it from inside `api/`:

```powershell
cd C:/Users/sarah/GamefyDB/api
C:/Users/sarah/AppData/Local/Python/bin/python -m alembic init alembic
cd C:/Users/sarah/GamefyDB
```

This creates `api/alembic.ini`, `api/alembic/env.py`, `api/alembic/script.py.mako`, and `api/alembic/versions/`.

- [ ] **Step 2: Edit `api/alembic.ini`**

Find the `sqlalchemy.url` line and set it to (matching `api/config.py` default):

```ini
sqlalchemy.url = sqlite:///./api/gamefydb.sqlite
```

We use the **sync** sqlite URL here because alembic runs migrations synchronously by default. The application uses the async URL.

- [ ] **Step 3: Rewrite `api/alembic/env.py`**

Replace the generated file with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from api.db import Base
from api.models import User, Job  # noqa: F401  ensures tables are registered

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate the initial migration**

```powershell
cd C:/Users/sarah/GamefyDB
C:/Users/sarah/AppData/Local/Python/bin/python -m alembic -c api/alembic.ini revision --autogenerate -m "initial users and jobs"
```

Expected: a new file appears in `api/alembic/versions/`. Open it and confirm `op.create_table('users', ...)` and `op.create_table('jobs', ...)` are present.

- [ ] **Step 5: Apply the migration**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m alembic -c api/alembic.ini upgrade head
```

Expected: creates `api/gamefydb.sqlite`. Verify:

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -c "import sqlite3; c = sqlite3.connect('api/gamefydb.sqlite').execute(\"select name from sqlite_master where type='table' order by name\"); print([r[0] for r in c])"
```

Expected: `['alembic_version', 'jobs', 'users']`.

- [ ] **Step 6: Add the sqlite file and the alembic versions dir intent to git, ignore the DB**

Append to `.gitignore`:

```
api/gamefydb.sqlite
api/gamefydb.sqlite-journal
```

The `api/alembic/versions/*.py` files SHOULD be committed.

- [ ] **Step 7: Commit**

```bash
git add api/alembic.ini api/alembic/ .gitignore
git commit -m "feat(api): add alembic with initial users and jobs migration"
```

---

## Task 6: User pydantic schemas

**Files:**
- Create: `api/schemas/__init__.py`
- Create: `api/schemas/user.py`

- [ ] **Step 1: Create `api/schemas/user.py`**

```python
import uuid

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    role: str


class UserCreate(schemas.BaseUserCreate):
    role: str = "viewer"


class UserUpdate(schemas.BaseUserUpdate):
    role: str | None = None
```

- [ ] **Step 2: Create `api/schemas/__init__.py`**

```python
from api.schemas.user import UserCreate, UserRead, UserUpdate

__all__ = ["UserCreate", "UserRead", "UserUpdate"]
```

- [ ] **Step 3: Verify**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -c "from api.schemas import UserCreate, UserRead, UserUpdate; print('ok')"
```

Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add api/schemas/
git commit -m "feat(api): add User pydantic schemas"
```

---

## Task 7: UserManager

**Files:**
- Create: `api/auth/__init__.py` (empty)
- Create: `api/auth/manager.py`

- [ ] **Step 1: Create `api/auth/__init__.py`** (empty file).

- [ ] **Step 2: Create `api/auth/manager.py`**

```python
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.db import get_async_session
from api.models import User

_settings = get_settings()


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = _settings.secret
    verification_token_secret = _settings.secret


async def get_user_db(session: AsyncSession = Depends(get_async_session)) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)
```

- [ ] **Step 3: Verify the import**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -c "from api.auth.manager import UserManager, get_user_manager; print('ok')"
```

Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add api/auth/
git commit -m "feat(api): add UserManager and user-db dependencies"
```

---

## Task 8: Auth backend (cookie + JWT) and FastAPIUsers

**Files:**
- Create: `api/auth/backend.py`

- [ ] **Step 1: Create `api/auth/backend.py`**

```python
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
```

- [ ] **Step 2: Verify the import**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -c "from api.auth.backend import auth_backend, fastapi_users; print(auth_backend.name)"
```

Expected: `cookie-jwt`.

- [ ] **Step 3: Commit**

```bash
git add api/auth/backend.py
git commit -m "feat(api): add cookie+JWT auth backend"
```

---

## Task 9: Dependencies — `current_user` and `require_admin`

**Files:**
- Create: `api/deps.py`

- [ ] **Step 1: Create `api/deps.py`**

```python
from fastapi import Depends, HTTPException, status

from api.auth.backend import fastapi_users
from api.models import User

current_active_user = fastapi_users.current_user(active=True)


async def require_admin(user: User = Depends(current_active_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
```

- [ ] **Step 2: Verify**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -c "from api.deps import current_active_user, require_admin; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add api/deps.py
git commit -m "feat(api): add current_user and require_admin dependencies"
```

---

## Task 10: Auth router (login, logout, me)

**Files:**
- Create: `api/auth/router.py`
- Modify: `api/main.py`

- [ ] **Step 1: Create `api/auth/router.py`**

```python
from fastapi import APIRouter, Depends

from api.auth.backend import auth_backend, fastapi_users
from api.deps import current_active_user
from api.models import User
from api.schemas import UserRead


def build_auth_router() -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    # /auth/login and /auth/logout from fastapi-users
    router.include_router(fastapi_users.get_auth_router(auth_backend))

    @router.get("/me", response_model=UserRead)
    async def me(user: User = Depends(current_active_user)) -> User:
        return user

    return router
```

- [ ] **Step 2: Wire it into `api/main.py`**

Replace `api/main.py` with:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth.router import build_auth_router
from api.config import get_settings


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

    return app


app = create_app()
```

- [ ] **Step 3: Verify the app boots**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -c "from api.main import app; print([r.path for r in app.routes if hasattr(r, 'path')])"
```

Expected: includes `/api/health`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`.

- [ ] **Step 4: Commit**

```bash
git add api/auth/router.py api/main.py
git commit -m "feat(api): wire /api/auth/login, /logout, /me"
```

---

## Task 11: Test harness — conftest with admin + viewer fixtures

**Files:**
- Create: `api/tests/conftest.py`

- [ ] **Step 1: Create `api/tests/conftest.py`**

```python
import asyncio
import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.auth.manager import UserManager
from api.db import Base, get_async_session
from api.main import app
from api.models import User
from api.schemas import UserCreate
from fastapi_users.db import SQLAlchemyUserDatabase


# In-memory SQLite shared across all connections in a single test process
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def engine():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="function")
async def db_session(session_maker) -> AsyncSession:
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def seeded_users(session_maker):
    async with session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        manager = UserManager(user_db)
        admin = await manager.create(UserCreate(email="admin@gamefy.test", password="admin12345", role="admin"), safe=False)
        viewer = await manager.create(UserCreate(email="viewer@gamefy.test", password="viewer12345", role="viewer"), safe=False)
        await session.commit()
        return {"admin": admin, "viewer": viewer}


@pytest.fixture(scope="function")
def client(session_maker, seeded_users):
    async def _override_session():
        async with session_maker() as s:
            yield s

    app.dependency_overrides[get_async_session] = _override_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Add `pytest-asyncio` config at the repo root**

Create `C:/Users/sarah/GamefyDB/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests api/tests
```

This makes `pytest-asyncio` auto-detect async tests and keeps existing tests in `tests/` running alongside the new `api/tests/`.

- [ ] **Step 3: Verify the fixtures load without error**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_health.py -v
```

Expected: still 1 passed (conftest is loaded but unused by this test). If you see import errors from conftest, fix them now before continuing.

- [ ] **Step 4: Commit**

```bash
git add api/tests/conftest.py pytest.ini
git commit -m "test(api): add pytest conftest with admin/viewer fixtures"
```

---

## Task 12: Test login → me → logout flow

**Files:**
- Create: `api/tests/test_auth_login.py`
- Create: `api/tests/test_auth_me.py`

- [ ] **Step 1: Write `api/tests/test_auth_login.py`**

```python
def test_login_sets_cookie_and_me_returns_user(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin@gamefy.test", "password": "admin12345"},
    )
    assert resp.status_code == 204, resp.text
    assert "gamefydb_session" in client.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "admin@gamefy.test"
    assert body["role"] == "admin"


def test_login_with_wrong_password_returns_400(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin@gamefy.test", "password": "wrong-password"},
    )
    assert resp.status_code == 400


def test_me_without_cookie_returns_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
```

**Note:** fastapi-users' login endpoint expects form-encoded `username` and `password` (OAuth2 password flow convention), not JSON. The success status is **204 No Content** when using cookie transport.

- [ ] **Step 2: Write `api/tests/test_auth_me.py`**

```python
def test_logout_clears_cookie(client):
    client.post("/api/auth/login", data={"username": "viewer@gamefy.test", "password": "viewer12345"})
    assert client.get("/api/auth/me").status_code == 200

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204

    # After logout, the cookie should be cleared/invalidated.
    me_after = client.get("/api/auth/me")
    assert me_after.status_code == 401
```

- [ ] **Step 3: Run the tests**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_auth_login.py api/tests/test_auth_me.py -v
```

Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add api/tests/test_auth_login.py api/tests/test_auth_me.py
git commit -m "test(api): cover login, me, and logout flows"
```

---

## Task 13: Test `require_admin` gating

**Files:**
- Create: `api/tests/test_require_admin.py`
- Modify: `api/main.py` (add a temporary `/api/_admin_ping` route to gate)

- [ ] **Step 1: Replace `api/main.py` to add a temporary gated route**

This route exists purely to verify the dependency works end-to-end. It will be replaced by real admin routes in Phase 9.

```python
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
```

- [ ] **Step 2: Write `api/tests/test_require_admin.py`**

```python
def test_admin_can_access_admin_route(client):
    client.post("/api/auth/login", data={"username": "admin@gamefy.test", "password": "admin12345"})
    resp = client.get("/api/_admin_ping")
    assert resp.status_code == 200
    assert resp.json() == {"hello": "admin@gamefy.test"}


def test_viewer_is_forbidden_from_admin_route(client):
    client.post("/api/auth/login", data={"username": "viewer@gamefy.test", "password": "viewer12345"})
    resp = client.get("/api/_admin_ping")
    assert resp.status_code == 403


def test_unauthenticated_is_unauthorized_from_admin_route(client):
    resp = client.get("/api/_admin_ping")
    assert resp.status_code == 401
```

- [ ] **Step 3: Run the tests**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_require_admin.py -v
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add api/main.py api/tests/test_require_admin.py
git commit -m "test(api): cover require_admin gating on a temporary route"
```

---

## Task 14: Admin seed script

**Files:**
- Create: `api/scripts/__init__.py` (empty)
- Create: `api/scripts/seed_admin.py`

- [ ] **Step 1: Create the scripts package**

Create `api/scripts/__init__.py` as an empty file.

- [ ] **Step 2: Create `api/scripts/seed_admin.py`**

```python
"""Seed an initial admin user.

Usage:
    python -m api.scripts.seed_admin --email <addr> --password <pw>
    # or rely on env vars GAMEFYDB_SEED_EMAIL / GAMEFYDB_SEED_PASSWORD

Idempotent: if the email already exists, the script reports it and exits 0.
"""
import argparse
import asyncio
import os
import sys

from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.exceptions import UserAlreadyExists

from api.auth.manager import UserManager
from api.db import async_session_maker
from api.models import User
from api.schemas import UserCreate


async def _seed(email: str, password: str) -> int:
    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        manager = UserManager(user_db)
        try:
            user = await manager.create(UserCreate(email=email, password=password, role="admin"), safe=False)
            await session.commit()
            print(f"created admin user: {user.email}")
            return 0
        except UserAlreadyExists:
            print(f"admin already exists: {email}")
            return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=os.environ.get("GAMEFYDB_SEED_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("GAMEFYDB_SEED_PASSWORD"))
    args = parser.parse_args()

    if not args.email or not args.password:
        print("error: --email and --password are required (or set GAMEFYDB_SEED_EMAIL / GAMEFYDB_SEED_PASSWORD)", file=sys.stderr)
        return 2

    return asyncio.run(_seed(args.email, args.password))


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run it against the dev SQLite DB**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m api.scripts.seed_admin --email admin@gamefy.local --password change-me-now
```

Expected: `created admin user: admin@gamefy.local`. Running it a second time prints `admin already exists: admin@gamefy.local` and exits 0.

- [ ] **Step 4: Smoke-test login end-to-end against the real server**

In one terminal:

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m uvicorn api.main:app --reload --port 8000
```

In another:

```powershell
curl -i -c cookies.txt -X POST http://localhost:8000/api/auth/login -d "username=admin@gamefy.local&password=change-me-now"
curl -b cookies.txt http://localhost:8000/api/auth/me
```

Expected: first call returns `204 No Content` with a `Set-Cookie: gamefydb_session=...` header; second call returns JSON with `email` and `role: "admin"`. Stop the server.

- [ ] **Step 5: Commit**

```bash
git add api/scripts/
git commit -m "feat(api): add idempotent admin seed script"
```

---

## Task 15: Final verification and README note

**Files:**
- Modify: `CLAUDE.md` (append API quickstart)

- [ ] **Step 1: Run the full pytest suite**

```powershell
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest -v
```

Expected: all existing tests in `tests/` PASS, all 8 new tests in `api/tests/` PASS. If any existing test fails because of the new `pytest.ini`'s `asyncio_mode = auto`, investigate — none of the existing data-loader tests use `async def` so they should be unaffected.

- [ ] **Step 2: Append a section to `CLAUDE.md`**

Add at the bottom of `CLAUDE.md`:

```markdown
## API (Phase 1+)

```powershell
# install
$PYTHON = "C:/Users/sarah/AppData/Local/Python/bin/python"
& $PYTHON -m pip install -r requirements.txt

# run migrations
& $PYTHON -m alembic -c api/alembic.ini upgrade head

# seed the first admin
& $PYTHON -m api.scripts.seed_admin --email admin@gamefy.local --password change-me

# run the API
& $PYTHON -m uvicorn api.main:app --reload --port 8000

# run API tests
& $PYTHON -m pytest api/tests/ -v
```

Auth: cookie-based JWT, 24h, `gamefydb_session` cookie. POST `/api/auth/login` with form fields `username` + `password`. `/api/auth/me` returns the current user. `/api/auth/logout` clears the cookie.
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add API quickstart to CLAUDE.md"
```

---

## Done criteria for Phase 1

- `pytest -v` passes everything (existing + new).
- `uvicorn api.main:app --reload` starts cleanly.
- Admin and viewer users exist in the SQLite DB.
- `curl` proof of cookie-auth flow works (login → me → logout).
- `/api/_admin_ping` returns 200 for admin, 403 for viewer, 401 for unauthenticated.
- `git log --oneline -20` shows ~15 small commits, one per task.

**Next phase:** Phase 2 — data cache + read endpoints (KPIs, facts, dims).
