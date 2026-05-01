import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings
from src.ai.registry import init_registry
from src.auth.models import AdminUser, Base
from src.auth.service import hash_password
from src.core.embedder import get_embedder
from src.core.exceptions import (
    AppNotFoundError,
    AuthenticationError,
    DocumentNotFoundError,
    ModelNotFoundError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


async def init_db(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_admin(session_factory) -> None:
    async with session_factory() as db:
        from sqlalchemy.future import select
        result = await db.execute(
            select(AdminUser).where(AdminUser.username == settings.MASTER_ADMIN_USERNAME)
        )
        existing = result.scalar_one_or_none()
        if not existing and settings.MASTER_ADMIN_PASSWORD_HASH:
            admin = AdminUser(
                username=settings.MASTER_ADMIN_USERNAME,
                password_hash=settings.MASTER_ADMIN_PASSWORD_HASH,
            )
            db.add(admin)
            await db.commit()
            logger.info("Master admin user created: %s", settings.MASTER_ADMIN_USERNAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    settings.CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(settings.HISTORY_DB_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    app.state.db_session = session_factory

    await init_db(engine)
    await ensure_admin(session_factory)
    init_registry()
    get_embedder()
    logger.info("Chatbot API started. Providers: %s", __import__("src.ai.registry", fromlist=["registry"]).registry.get_all_ids())
    yield
    await engine.dispose()


app = FastAPI(title="Multi-App Chatbot API", version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to specific origins in production
    allow_credentials=False,      # must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.mount("/static", StaticFiles(directory="admin_ui/static"), name="static")
app.mount("/widget", StaticFiles(directory="widget"), name="widget")

# ── Import routers ────────────────────────────────────────────────────────────
from src.api.routers.admin_portal import router as admin_portal_router
from src.api.routers.apps import router as apps_router
from src.api.routers.audit import router as audit_router
from src.api.routers.chat import router as chat_router
from src.api.routers.chunks import router as chunks_router
from src.api.routers.docs import router as docs_router
from src.api.routers.health import router as health_router
from src.api.routers.providers import router as providers_router

app.include_router(health_router)
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(apps_router, prefix="/apps", tags=["apps"])
app.include_router(docs_router, prefix="/docs", tags=["docs"])
app.include_router(chunks_router, prefix="/chunks", tags=["chunks"])
app.include_router(providers_router, prefix="/providers", tags=["providers"])
app.include_router(audit_router, prefix="/audit", tags=["audit"])
app.include_router(admin_portal_router, prefix="/admin", tags=["portal"])

# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(ProviderAuthError)
async def provider_auth(req: Request, exc: ProviderAuthError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"error": str(exc)})


@app.exception_handler(ProviderRateLimitError)
async def provider_rate(req: Request, exc: ProviderRateLimitError) -> JSONResponse:
    return JSONResponse(status_code=429, content={"error": str(exc)})


@app.exception_handler(ProviderTimeoutError)
async def provider_timeout(req: Request, exc: ProviderTimeoutError) -> JSONResponse:
    return JSONResponse(status_code=504, content={"error": str(exc)})


@app.exception_handler(ProviderUnavailableError)
async def provider_unavail(req: Request, exc: ProviderUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": str(exc)})


@app.exception_handler(ModelNotFoundError)
async def model_not_found(req: Request, exc: ModelNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": str(exc)})


@app.exception_handler(AppNotFoundError)
async def app_not_found(req: Request, exc: AppNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(DocumentNotFoundError)
async def doc_not_found(req: Request, exc: DocumentNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(AuthenticationError)
async def auth_err(req: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"error": "Authentication required"})
