from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.auth.models import AdminUser
from src.auth.service import verify_token
from src.core.exceptions import AuthenticationError
from src.core.utils import get_client_ip as _resolve_ip

_bearer = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.db_session() as session:
        yield session


def get_client_ip(request: Request) -> str:
    return _resolve_ip(request) or "unknown"


async def get_current_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        username = verify_token(credentials.credentials)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_cookie_session(request: Request, db: AsyncSession = Depends(get_db)) -> AdminUser:
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/admin/login", status_code=302)
    try:
        username = verify_token(token)
    except AuthenticationError:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return RedirectResponse(url="/admin/login", status_code=302)
    return user
