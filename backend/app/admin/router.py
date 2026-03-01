from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
import json
from app.db import get_db
from app.activity import log_activity
from app.models import User, UserStatus, HAHost, Role, UserRole, RolePermission
from app.auth.router import require_admin
from app.auth.service import hash_password
from app.crypto import encrypt, decrypt
from app.security_log import log_admin_action

router = APIRouter()

# ══════════════════════════════════════════
# UTENTI
# ══════════════════════════════════════════

class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    is_admin: bool = False

class ResetPasswordRequest(BaseModel):
    new_password: str

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "full_name": u.full_name,
             "status": u.status, "is_admin": u.is_admin,
             "require_2fa": u.require_2fa,
             "request_reason": u.request_reason,
             "created_at": u.created_at} for u in users]

@router.get("/users/pending")
async def list_pending(db: AsyncSession = Depends(get_db),
                       admin: User = Depends(require_admin)):
    result = await db.execute(select(User).where(User.status == UserStatus.pending))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "full_name": u.full_name,
             "request_reason": u.request_reason, "created_at": u.created_at} for u in users]

@router.post("/users", status_code=201)
async def create_user(data: CreateUserRequest, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email già registrata")
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        status=UserStatus.active,
        is_admin=data.is_admin,
        approved_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    return {"message": f"Utente {data.email} creato", "id": str(user.id)}

@router.post("/users/{user_id}/approve")
async def approve_user(user_id: str, db: AsyncSession = Depends(get_db),
                       admin: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    user.status = UserStatus.active
    user.approved_at = datetime.utcnow()
    await db.commit()
    log_admin_action(admin.email, "APPROVE_USER", user.email)
    return {"message": f"Utente {user.email} approvato"}

@router.post("/users/{user_id}/revoke")
async def revoke_user(user_id: str, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    user.status = UserStatus.revoked
    await db.commit()
    log_admin_action(admin.email, "REVOKE_USER", user.email)
    return {"message": f"Utente {user.email} revocato"}

@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: str, data: ResetPasswordRequest,
                         db: AsyncSession = Depends(get_db),
                         admin: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    user.hashed_password = hash_password(data.new_password)
    # Revoca tutte le sessioni attive
    sessions_result = await db.execute(
        select(__import__('app.models', fromlist=['Session']).Session).where(
            __import__('app.models', fromlist=['Session']).Session.user_id == user.id,
            __import__('app.models', fromlist=['Session']).Session.revoked == False))
    for s in sessions_result.scalars().all():
        s.revoked = True
    await db.commit()
    return {"message": f"Password di {user.email} aggiornata, sessioni revocate"}

@router.post("/users/{user_id}/make-admin")
async def make_admin(user_id: str, db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    user.is_admin = True
    await db.commit()
    return {"message": f"{user.email} è ora amministratore"}

@router.get("/users/{user_id}/roles")
async def get_user_roles(user_id: str, db: AsyncSession = Depends(get_db),
                         admin: User = Depends(require_admin)):
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id))
    user_roles = result.scalars().all()
    out = []
    for ur in user_roles:
        role = await db.get(Role, ur.role_id)
        if role:
            out.append({"assignment_id": str(ur.id), "role_id": str(role.id), "role_name": role.name})
    return out


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    if str(user.id) == str(current.id):
        raise HTTPException(400, "Non puoi eliminare il tuo account")
    # Cancella dipendenze in cascata
    await db.execute(text("DELETE FROM sessions WHERE user_id = :uid"), {"uid": user_id})
    await db.execute(text("DELETE FROM trusted_devices WHERE user_id = :uid"), {"uid": user_id})
    await db.execute(text("DELETE FROM user_roles WHERE user_id = :uid"), {"uid": user_id})
    await db.delete(user)
    await db.commit()
    await log_activity(db, "admin_delete_user", f"Eliminato utente {user.email}", str(current.id), current.email)
    return {"message": "Utente eliminato"}

@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_user_role(user_id: str, role_id: str,
                           db: AsyncSession = Depends(get_db),
                           admin: User = Depends(require_admin)):
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id,
                               UserRole.role_id == role_id))
    ur = result.scalar_one_or_none()
    if not ur:
        raise HTTPException(404, "Assegnazione non trovata")
    await db.delete(ur)
    await db.commit()
    return {"message": "Ruolo rimosso"}

# ══════════════════════════════════════════
# HOST HA — token cifrati, mai esposti
# ══════════════════════════════════════════

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
    # token NON incluso nella risposta
    return [{"id": str(h.id), "name": h.name, "base_url": h.base_url,
             "description": h.description, "active": h.active,
             "created_at": h.created_at} for h in hosts]

@router.post("/hosts", status_code=201)
async def create_host(data: HAHostCreate, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    host = HAHost(
        name=data.name,
        base_url=data.base_url.rstrip("/"),
        token=encrypt(data.token),  # cifrato
        description=data.description
    )
    db.add(host)
    await db.commit()
    log_admin_action(admin.email, "CREATE_HOST", data.name)
    return {"message": f"Host '{data.name}' aggiunto", "id": str(host.id)}

class HAHostUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    token: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

@router.patch("/hosts/{host_id}")
async def update_host(host_id: str, data: HAHostUpdate,
                      db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    host = await db.get(HAHost, host_id)
    if not host:
        raise HTTPException(404, "Host non trovato")
    if data.name is not None: host.name = data.name
    if data.base_url is not None: host.base_url = data.base_url.rstrip("/")
    if data.token is not None: host.token = encrypt(data.token)
    if data.description is not None: host.description = data.description
    if data.active is not None: host.active = data.active
    await db.commit()
    log_admin_action(admin.email, "UPDATE_HOST", host.name)
    return {"message": f"Host '{host.name}' aggiornato"}

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

# ══════════════════════════════════════════
# RUOLI
# ══════════════════════════════════════════

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    require_2fa: bool = False

class PermissionCreate(BaseModel):
    host_id: str
    allowed_domains: Optional[list[str]] = None
    allowed_entities: Optional[list[str]] = None

@router.get("/roles")
async def list_roles(db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    out = []
    for r in roles:
        perms_result = await db.execute(
            select(RolePermission).where(RolePermission.role_id == r.id))
        perms = perms_result.scalars().all()
        out.append({
            "id": str(r.id), "name": r.name, "description": r.description,
            "require_2fa": r.require_2fa, "created_at": r.created_at,
            "permissions": [{
                "id": str(p.id),
                "host_id": str(p.host_id),
                "allowed_domains": json.loads(p.allowed_domains) if p.allowed_domains else None,
                "allowed_entities": json.loads(p.allowed_entities) if p.allowed_entities else None,
            } for p in perms]
        })
    return out

@router.post("/roles", status_code=201)
async def create_role(data: RoleCreate, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    role = Role(name=data.name, description=data.description, require_2fa=data.require_2fa)
    db.add(role)
    await db.commit()
    return {"message": f"Ruolo '{data.name}' creato", "id": str(role.id)}

@router.post("/roles/{role_id}/permissions", status_code=201)
async def add_permission(role_id: str, data: PermissionCreate,
                         db: AsyncSession = Depends(get_db),
                         admin: User = Depends(require_admin)):
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Ruolo non trovato")
    perm = RolePermission(
        role_id=role.id,
        host_id=data.host_id,
        allowed_domains=json.dumps(data.allowed_domains) if data.allowed_domains else None,
        allowed_entities=json.dumps(data.allowed_entities) if data.allowed_entities else None,
    )
    db.add(perm)
    await db.commit()
    return {"message": "Permesso aggiunto"}

@router.delete("/roles/{role_id}/permissions/{perm_id}")
async def delete_permission(role_id: str, perm_id: str,
                            db: AsyncSession = Depends(get_db),
                            admin: User = Depends(require_admin)):
    perm = await db.get(RolePermission, perm_id)
    if not perm:
        raise HTTPException(404, "Permesso non trovato")
    await db.delete(perm)
    await db.commit()
    return {"message": "Permesso rimosso"}

@router.post("/roles/{role_id}/assign/{user_id}")
async def assign_role(role_id: str, user_id: str,
                      db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    existing = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id,
                               UserRole.role_id == role_id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Ruolo già assegnato")
    ur = UserRole(user_id=user_id, role_id=role_id)
    db.add(ur)
    await db.commit()
    return {"message": "Ruolo assegnato"}

@router.delete("/roles/{role_id}/assign/{user_id}")
async def remove_role(role_id: str, user_id: str,
                      db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id,
                               UserRole.role_id == role_id))
    ur = result.scalar_one_or_none()
    if not ur:
        raise HTTPException(404, "Assegnazione non trovata")
    await db.delete(ur)
    await db.commit()
    return {"message": "Ruolo rimosso"}

@router.patch("/roles/{role_id}")
async def rename_role(role_id: str, data: dict, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    from sqlalchemy import text as sql_text
    role = await db.get(Role, role_id)
    if not role: raise HTTPException(404, "Ruolo non trovato")
    if "name" in data and data["name"].strip():
        role.name = data["name"].strip()
    await db.commit()
    return {"message": "Ruolo aggiornato", "id": str(role.id), "name": role.name}

@router.delete("/roles/{role_id}")
async def delete_role(role_id: str, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    from sqlalchemy import text as sql_text
    role = await db.get(Role, role_id)
    if not role: raise HTTPException(404, "Ruolo non trovato")
    await db.execute(sql_text("DELETE FROM user_roles WHERE role_id = :rid"), {"rid": role_id})
    await db.execute(sql_text("DELETE FROM role_permissions WHERE role_id = :rid"), {"rid": role_id})
    await db.execute(sql_text("UPDATE custom_views SET role_id = NULL WHERE role_id = :rid"), {"rid": role_id})
    await db.delete(role)
    await db.commit()
    return {"message": "Ruolo eliminato"}

@router.patch("/roles/{role_id}/require-2fa")
async def toggle_require_2fa(role_id: str, db: AsyncSession = Depends(get_db),
                              admin: User = Depends(require_admin)):
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Ruolo non trovato")
    role.require_2fa = not role.require_2fa
    await db.commit()
    log_admin_action(admin.email, "TOGGLE_2FA_REQUIRED", f"{role.name}={role.require_2fa}")
    return {"message": f"2FA obbligatorio per '{role.name}': {role.require_2fa}"}

@router.post("/users/{user_id}/remove-admin")
async def remove_admin(user_id: str, db: AsyncSession = Depends(get_db),
                       admin: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    if str(user.id) == str(admin.id):
        raise HTTPException(400, "Non puoi revocare i tuoi stessi privilegi admin")
    user.is_admin = False
    await db.commit()
    log_admin_action(admin.email, "REMOVE_ADMIN", user.email)
    return {"message": f"{user.email} non è più amministratore"}

@router.post("/users/{user_id}/require-2fa")
async def set_require_2fa(user_id: str, db: AsyncSession = Depends(get_db),
                          admin: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utente non trovato")
    user.require_2fa = not user.require_2fa
    await db.commit()
    log_admin_action(admin.email, "TOGGLE_USER_2FA", f"{user.email}={user.require_2fa}")
    return {"message": f"2FA obbligatorio per {user.email}: {user.require_2fa}", "require_2fa": user.require_2fa}
