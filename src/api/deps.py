from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.auth.models import AdminUser
from src.auth.service import verify_token
from src.core.exceptions import AuthenticationError

_bearer = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.db_session() as session:
        yield session


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
