from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db import get_db
from app.models import ActivityLog, User
from app.auth.router import require_admin
from typing import Optional

router = APIRouter()

@router.get("/admin/logs")
async def get_logs(
    action: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    q = select(ActivityLog).order_by(desc(ActivityLog.created_at))
    if action:
        q = q.where(ActivityLog.action == action)
    if user_email:
        q = q.where(ActivityLog.user_email.ilike(f"%{user_email}%"))
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    logs = result.scalars().all()
    return [{"id": str(l.id), "user_email": l.user_email, "action": l.action,
             "detail": l.detail, "ip": l.ip,
             "created_at": l.created_at.isoformat()} for l in logs]

@router.delete("/admin/logs")
async def clear_logs(days: int = 30, db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    from sqlalchemy import delete
    from datetime import datetime, timedelta
    from app.models import ActivityLog
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(delete(ActivityLog).where(ActivityLog.created_at < cutoff))
    await db.commit()
    return {"deleted": result.rowcount, "message": f"Eliminati log più vecchi di {days} giorni"}
