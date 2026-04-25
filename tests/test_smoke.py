"""
Smoke tests — every admin route returns 2xx or 303 (redirect), not 500.
Uses SQLite in-memory so no Postgres required.
"""
import os
import pytest
import pytest_asyncio

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("POS_PROVIDER", "manual")
os.environ.setdefault("PAYMENT_PROVIDER", "check")
os.environ.setdefault("ACCOUNTING_PROVIDER", "none")
os.environ.setdefault("EMAIL_PROVIDER", "log")
os.environ.setdefault("GALLERY_NAME", "Test Gallery")

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


from contextlib import asynccontextmanager

@pytest.fixture
def transport():
    return ASGITransport(app=app)


@asynccontextmanager
async def _authed_client(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/admin/login", data={"password": "testpass"},
                                 follow_redirects=False)
        token = resp.cookies.get("admin_token")
        if token:
            client.cookies.set("admin_token", token)
        yield client


@pytest.mark.asyncio
async def test_health(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_login_page(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/admin/login")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_login_wrong_password(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/admin/login", data={"password": "wrong"})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_correct_password(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/admin/login", data={"password": "testpass"},
                         follow_redirects=False)
        assert r.status_code == 303
        assert "admin_token" in r.cookies


@pytest.mark.asyncio
async def test_dashboard(transport):
    async with _authed_client(transport) as c:
        r = await c.get("/admin/")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_artist_list(transport):
    async with _authed_client(transport) as c:
        r = await c.get("/admin/artists")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_artist_create_and_detail(transport):
    async with _authed_client(transport) as c:
        r = await c.post("/admin/artists/new", data={
            "name": "Test Artist", "email": "test@example.com",
        }, follow_redirects=False)
        assert r.status_code == 303
        location = r.headers["location"]

        r2 = await c.get(location)
        assert r2.status_code == 200
        assert "Test Artist" in r2.text


@pytest.mark.asyncio
async def test_booth_list(transport):
    async with _authed_client(transport) as c:
        r = await c.get("/admin/booths")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_booth_create(transport):
    async with _authed_client(transport) as c:
        r = await c.post("/admin/booths/new", data={
            "name": "Booth 1", "tier": "small", "monthly_rate": "150.00",
        }, follow_redirects=False)
        assert r.status_code == 303


@pytest.mark.asyncio
async def test_sales_list(transport):
    async with _authed_client(transport) as c:
        r = await c.get("/admin/sales")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_applications_list(transport):
    async with _authed_client(transport) as c:
        r = await c.get("/admin/applications")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_payouts_list(transport):
    async with _authed_client(transport) as c:
        r = await c.get("/admin/payouts")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_monitor(transport):
    async with _authed_client(transport) as c:
        r = await c.get("/admin/monitor")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_public_apply(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/apply")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_portal_login_page(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/portal/login")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_portal_dashboard_redirects_unauthenticated(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/portal/dashboard", follow_redirects=False)
        assert r.status_code == 303
        assert "/portal/login" in r.headers["location"]


@pytest.mark.asyncio
async def test_sync_status(transport):
    async with _authed_client(transport) as c:
        r = await c.get("/sync/status")
        assert r.status_code == 200
        assert r.json()["provider"] == "manual"
