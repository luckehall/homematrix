from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.db import get_db
from app.models import User, UserStatus, HAHost
from app.auth.router import require_admin

router = APIRouter()

# ── Utenti ──

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "full_name": u.full_name,
             "status": u.status, "is_admin": u.is_admin,
             "request_reason": u.request_reason,
             "created_at": u.created_at} for u in users]

@router.get("/users/pending")
async def list_pending(db: AsyncSession = Depends(get_db),
                       admin: User = Depends(require_admin)):
    result = await db.execute(select(User).where(User.status == UserStatus.pending))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "full_name": u.full_name,
             "request_reason": u.request_reason, "created_at": u.created_at} for u in users]

@router.post("/users/{user_id}/approve")
async def approve_user(user_id: str, db: AsyncSession = Depends(get_db),
                       admin: User = Depends(require_admin)):
    from datetime import datetime
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    user.status = UserStatus.active
    user.approved_at = datetime.utcnow()
    await db.commit()
    return {"message": f"Utente {user.email} approvato"}

@router.post("/users/{user_id}/revoke")
async def revoke_user(user_id: str, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    user.status = UserStatus.revoked
    await db.commit()
    return {"message": f"Utente {user.email} revocato"}

@router.post("/users/{user_id}/make-admin")
async def make_admin(user_id: str, db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    user.is_admin = True
    await db.commit()
    return {"message": f"{user.email} è ora amministratore"}

# ── Host HA ──

class HAHostCreate(BaseModel):
    name: str
    base_url: str
    token: str
    description: Optional[str] = None

@router.get("/hosts")
async def list_hosts(db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    result = await db.execute(select(HAHost))
    hosts = result.scalars().all()
    return [{"id": str(h.id), "name": h.name, "base_url": h.base_url,
             "description": h.description, "active": h.active,
             "created_at": h.created_at} for h in hosts]

@router.post("/hosts", status_code=201)
async def create_host(data: HAHostCreate, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    host = HAHost(name=data.name, base_url=data.base_url.rstrip("/"),
                  token=data.token, description=data.description)
    db.add(host)
    await db.commit()
    return {"message": f"Host '{data.name}' aggiunto", "id": str(host.id)}

@router.delete("/hosts/{host_id}")
async def delete_host(host_id: str, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    host = await db.get(HAHost, host_id)
    if not host:
        raise HTTPException(404, "Host non trovato")
    await db.delete(host)
    await db.commit()
    return {"message": f"Host '{host.name}' eliminato"}

@router.patch("/hosts/{host_id}/toggle")
async def toggle_host(host_id: str, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    host = await db.get(HAHost, host_id)
    if not host:
        raise HTTPException(404, "Host non trovato")
    host.active = not host.active
    await db.commit()
    return {"message": f"Host '{host.name}' {'attivato' if host.active else 'disattivato'}"}
