import json
import logging
from datetime import datetime

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import AuditLog
from src.core.utils import get_client_ip

logger = logging.getLogger(__name__)


async def log_action(
    db: AsyncSession,
    username: str,
    action: str,
    target: str | None = None,
    detail: dict | None = None,
    success: bool = True,
    request: Request | None = None,
) -> None:
    """Append-only audit log write. Never raises — failures are logged only."""
    try:
        ip_address: str | None = None
        user_agent: str | None = None
        if request:
            ip_address = get_client_ip(request)
            user_agent = request.headers.get("User-Agent")

        entry = AuditLog(
            timestamp=datetime.utcnow(),
            username=username,
            action=action,
            target=target,
            ip_address=ip_address,
            user_agent=user_agent,
            detail=json.dumps(detail) if detail else None,
            success=success,
        )
        db.add(entry)
        await db.commit()
    except Exception as exc:
        logger.error("Failed to write audit log: %s", exc)
