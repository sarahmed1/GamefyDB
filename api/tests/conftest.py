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
