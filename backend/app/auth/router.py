from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db import get_db
from app.models import User, Session, UserStatus
from app.auth.service import (hash_password, verify_password,
                               create_access_token, create_refresh_token,
                               decode_access_token, validate_password)
from app.config import settings
from app.limiter import limiter
from app.security_log import log_login_ok, log_login_fail, log_register, log_password_change
from fastapi import Request

router = APIRouter()
bearer = HTTPBearer(auto_error=False)

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    request_reason: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    err = validate_password(data.password)
    if err:
        raise HTTPException(400, err)
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email già registrata")
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        request_reason=data.request_reason,
        status=UserStatus.pending,
    )
    db.add(user)
    await db.commit()
    log_register(data.email, request.client.host)
    return {"message": "Registrazione completata. Attendi l'approvazione dell'amministratore."}

@router.post("/login")
@limiter.limit("20/minute")
async def login(request: Request, data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        log_login_fail(data.email, request.client.host)
        raise HTTPException(401, "Credenziali non valide")
    if user.status != UserStatus.active:
        log_login_fail(data.email, request.client.host)
        raise HTTPException(403, "Account non ancora approvato o revocato")
    refresh_token = create_refresh_token()
    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session = Session(user_id=user.id, refresh_token=refresh_token, expires_at=expires)
    db.add(session)
    await db.commit()
    response.set_cookie(
        key="refresh_token", value=refresh_token,
        httponly=True, secure=True, samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )
    # Controlla se 2FA è richiesto
    requires_2fa = user.totp_enabled and (user.is_admin or user.require_2fa or any_role_requires_2fa)
    if requires_2fa:
        # Emetti token temporaneo (5 minuti) per la verifica 2FA
        temp_token = create_access_token(str(user.id), user.is_admin, expires_minutes=5)
        return {"requires_2fa": True, "temp_token": temp_token}

    # Controlla se 2FA è richiesto
    needs_2fa = False
    if user.totp_enabled:
        if user.is_admin or user.require_2fa:
            needs_2fa = True
        else:
            # Controlla se qualche ruolo richiede 2FA
            role_result = await db.execute(select(UserRole).where(UserRole.user_id == user.id))
            user_roles = role_result.scalars().all()
            for ur in user_roles:
                role = await db.get(Role, ur.role_id)
                if role and role.require_2fa:
                    needs_2fa = True
                    break

    if needs_2fa:
        temp_token = create_access_token(str(user.id), user.is_admin, expires_minutes=5)
        return {"requires_2fa": True, "temp_token": temp_token}

    log_login_ok(user.email, request.client.host)
    return {"access_token": create_access_token(str(user.id), user.is_admin)}

@router.post("/refresh", response_model=TokenResponse)
async def refresh(response: Response, refresh_token: Optional[str] = Cookie(None),
                  db: AsyncSession = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(401, "Nessun refresh token")
    result = await db.execute(
        select(Session).where(Session.refresh_token == refresh_token,
                              Session.revoked == False))
    session = result.scalar_one_or_none()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(401, "Sessione scaduta o non valida")
    user = await db.get(User, session.user_id)
    if not user or user.status != UserStatus.active:
        raise HTTPException(403, "Utente non attivo")
    return {"access_token": create_access_token(str(user.id), user.is_admin)}

@router.post("/logout")
async def logout(response: Response, refresh_token: Optional[str] = Cookie(None),
                 db: AsyncSession = Depends(get_db)):
    if refresh_token:
        result = await db.execute(select(Session).where(Session.refresh_token == refresh_token))
        session = result.scalar_one_or_none()
        if session:
            session.revoked = True
            await db.commit()
    response.delete_cookie("refresh_token")
    return {"message": "Logout effettuato"}

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer),
                           db: AsyncSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(401, "Token mancante")
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Token non valido o scaduto")
    user = await db.get(User, payload["sub"])
    if not user or user.status != UserStatus.active:
        raise HTTPException(403, "Utente non attivo")
    return user

async def require_admin(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(403, "Accesso riservato agli amministratori")
    return user

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
async def change_password(data: ChangePasswordRequest,
                          credentials: HTTPAuthorizationCredentials = Depends(bearer),
                          db: AsyncSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(401, "Token mancante")
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Token non valido")
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(404, "Utente non trovato")
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(400, "Password attuale non corretta")
    err = validate_password(data.new_password)
    if err:
        raise HTTPException(400, err)
    user.hashed_password = hash_password(data.new_password)
    # Revoca tutte le sessioni attive
    from sqlalchemy import select as sa_select
    sessions_result = await db.execute(
        sa_select(Session).where(Session.user_id == user.id, Session.revoked == False))
    for s in sessions_result.scalars().all():
        s.revoked = True
    await db.commit()
    return {"message": "Password aggiornata, tutte le sessioni revocate"}
