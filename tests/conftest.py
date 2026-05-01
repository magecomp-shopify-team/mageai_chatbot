import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.main import app
from src.auth.models import Base
from src.auth.service import create_access_token, hash_password


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    app.state.db_session = session_factory

    # Create a test admin user
    async with session_factory() as db:
        from sqlalchemy.future import select
        from src.auth.models import AdminUser
        result = await db.execute(select(AdminUser).where(AdminUser.username == "test_admin"))
        if not result.scalar_one_or_none():
            admin = AdminUser(
                username="test_admin",
                password_hash=hash_password("testpassword123"),
                is_active=True,
            )
            db.add(admin)
            await db.commit()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers() -> dict:
    token = create_access_token("test_admin")
    return {"Authorization": f"Bearer {token}"}
