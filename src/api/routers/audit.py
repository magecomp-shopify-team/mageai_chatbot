from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.deps import get_current_admin, get_db
from src.auth.models import AdminUser, AuditLog

router = APIRouter()


@router.get("/")
async def list_audit_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> list[dict]:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "username": log.username,
            "action": log.action,
            "target": log.target,
            "ip_address": log.ip_address,
            "success": log.success,
            "detail": log.detail,
        }
        for log in logs
    ]
