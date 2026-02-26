from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db import get_db
from app.models import User, UserRole, Role, TrustedDevice
from app.auth.router import get_current_user
from app.totp import generate_totp_secret, get_totp_uri, verify_totp, generate_qr_base64, generate_device_token
from app.auth.service import create_access_token

router = APIRouter()

DEVICE_COOKIE = "hm_device"
DEVICE_EXPIRY_DAYS = 180

class VerifyTOTPRequest(BaseModel):
    code: str
    remember_device: bool = False
    device_name: str = ""

class ConfirmTOTPRequest(BaseModel):
    code: str

# ══════════════════════════════════════════
# SETUP 2FA
# ══════════════════════════════════════════

@router.post("/setup")
async def setup_2fa(db: AsyncSession = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Genera secret e QR code per il setup."""
    if user.totp_enabled:
        raise HTTPException(400, "2FA già abilitato")
    secret = generate_totp_secret()
    user.totp_secret = secret
    await db.commit()
    uri = get_totp_uri(secret, user.email)
    qr = generate_qr_base64(uri)
    return {"secret": secret, "qr": qr, "uri": uri}

@router.post("/confirm")
async def confirm_2fa(data: ConfirmTOTPRequest,
                      db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Conferma il codice per attivare il 2FA."""
    if not user.totp_secret:
        raise HTTPException(400, "Prima avvia il setup 2FA")
    if not verify_totp(user.totp_secret, data.code):
        raise HTTPException(400, "Codice non valido")
    user.totp_enabled = True
    await db.commit()
    return {"message": "2FA attivato con successo"}

@router.post("/disable")
async def disable_2fa(data: ConfirmTOTPRequest,
                      db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Disabilita il 2FA (richiede codice valido)."""
    if not user.totp_enabled:
        raise HTTPException(400, "2FA non abilitato")
    if not verify_totp(user.totp_secret, data.code):
        raise HTTPException(400, "Codice non valido")
    user.totp_enabled = False
    user.totp_secret = None
    await db.commit()
    return {"message": "2FA disabilitato"}

@router.get("/status")
async def totp_status(db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Stato 2FA dell'utente corrente."""
    # Controlla se il ruolo richiede 2FA
    required = False
    result = await db.execute(select(UserRole).where(UserRole.user_id == user.id))
    for ur in result.scalars().all():
        role = await db.get(Role, ur.role_id)
        if role and role.require_2fa:
            required = True
            break
    return {
        "enabled": user.totp_enabled,
        "required": required or user.require_2fa or user.is_admin
    }

# ══════════════════════════════════════════
# VERIFICA 2FA AL LOGIN
# ══════════════════════════════════════════

@router.post("/verify")
async def verify_2fa(data: VerifyTOTPRequest,
                     request: Request,
                     response: Response,
                     db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Verifica codice TOTP dopo il login. Emette access token definitivo."""
    if not user.totp_enabled:
        raise HTTPException(400, "2FA non abilitato")
    if not verify_totp(user.totp_secret, data.code):
        raise HTTPException(400, "Codice non valido")

    if data.remember_device:
        device_token = generate_device_token()
        expires = datetime.utcnow() + timedelta(days=DEVICE_EXPIRY_DAYS)
        device = TrustedDevice(
            user_id=user.id,
            device_token=device_token,
            device_name=data.device_name or request.headers.get("User-Agent", "")[:200],
            expires_at=expires,
        )
        db.add(device)
        await db.commit()
        response.set_cookie(
            key=DEVICE_COOKIE,
            value=device_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=DEVICE_EXPIRY_DAYS * 86400,
            path="/",
        )

    return {"access_token": create_access_token(str(user.id), user.is_admin), "2fa_verified": True}

# ══════════════════════════════════════════
# CONTROLLA DISPOSITIVO DI FIDUCIA
# ══════════════════════════════════════════

@router.post("/check-device")
async def check_device(request: Request,
                       response: Response,
                       db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    """Controlla se il dispositivo corrente è trusted. Se sì, emette access token definitivo."""
    device_token = request.cookies.get(DEVICE_COOKIE)
    if not device_token:
        return {"trusted": False}

    result = await db.execute(
        select(TrustedDevice).where(
            TrustedDevice.user_id == user.id,
            TrustedDevice.device_token == device_token,
            TrustedDevice.expires_at > datetime.utcnow()
        ))
    device = result.scalar_one_or_none()
    if not device:
        return {"trusted": False}

    # Aggiorna last_seen
    device.last_seen = datetime.utcnow()
    await db.commit()
    return {
        "trusted": True,
        "access_token": create_access_token(str(user.id), user.is_admin)
    }
