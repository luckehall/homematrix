from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ActivityLog

async def log_activity(db: AsyncSession, action: str, detail: str = None,
                       user_id: str = None, user_email: str = None, ip: str = None):
    try:
        entry = ActivityLog(
            user_id=user_id,
            user_email=user_email,
            action=action,
            detail=detail,
            ip=ip
        )
        db.add(entry)
        await db.commit()
    except Exception as e:
        pass  # Non bloccare mai l'operazione principale per un log
