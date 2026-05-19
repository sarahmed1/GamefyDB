import asyncio
import uuid

# Allow reserved test TLDs like `.test` in EmailStr validation. Pydantic and
# fastapi-users call `email_validator.validate_email` without `test_environment=True`,
# which rejects `admin@gamefy.test`. Patch the module-level function so the test
# environment domains are accepted everywhere (pydantic looks it up by attribute).
import email_validator as _email_validator

_original_validate_email = _email_validator.validate_email


def _validate_email_allow_test(email, *args, **kwargs):
    kwargs.setdefault("test_environment", True)
    return _original_validate_email(email, *args, **kwargs)


_email_validator.validate_email = _validate_email_allow_test

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


from api.services import data_cache as _data_cache_mod
from api.services.data_cache import cache as data_cache
from api.tests._fixtures.synthetic_schema import build_synthetic_schema


@pytest.fixture(scope="session", autouse=True)
def _disable_real_cache_build():
    """Prevent the lifespan startup from hitting the real ``excel/`` dir on every
    TestClient context entry. Patches the singleton instance only, so fresh
    ``DataCache()`` instances created inside individual tests still get the
    real ``build`` method (and tests that need to verify build behavior on a
    fresh instance work correctly)."""
    original = data_cache.build
    data_cache.build = lambda input_dir: None
    yield
    data_cache.build = original


@pytest.fixture(scope="function")
def synthetic_schema():
    """A small deterministic star schema for KPI/facts/dims tests."""
    return build_synthetic_schema()


@pytest.fixture(scope="function")
def cached_app(client, synthetic_schema):
    """Reuse the authenticated TestClient from `client`, but install
    the synthetic schema into the module-level DataCache singleton.
    Logs in as admin so that authenticated endpoints are reachable."""
    previous = data_cache.schema, data_cache.loaded
    data_cache.schema = synthetic_schema
    data_cache.loaded = True
    client.post("/api/auth/login", data={"username": "admin@gamefy.test", "password": "admin12345"})
    yield client
    data_cache.schema, data_cache.loaded = previous
