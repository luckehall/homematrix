from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import timedelta
import secrets, smtplib, redis
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.db import get_db
from app.models import User
from app.auth.service import hash_password, validate_password
from app.config import settings

router = APIRouter()

redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
RESET_EXPIRY = 1800  # 30 minuti

class ForgotRequest(BaseModel):
    email: str

class ResetRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

def send_reset_email(to_email: str, reset_url: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "HomeMatrix — Reset password"
    msg["From"] = "HomeMatrix <seriole47@gmail.com>"
    msg["To"] = to_email

    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #111318; color: #e8eaf0; border-radius: 16px;">
      <h2 style="color: #00e5c0;">HomeMatrix</h2>
      <p>Hai richiesto il reset della password.</p>
      <p>Clicca sul pulsante qui sotto per impostare una nuova password. Il link scade in <strong>30 minuti</strong>.</p>
      <a href="{reset_url}" style="display:inline-block; margin: 24px 0; padding: 14px 28px; background: #00e5c0; color: #111318; border-radius: 10px; text-decoration: none; font-weight: bold;">
        Reimposta password
      </a>
      <p style="color: #888; font-size: 13px;">Se non hai richiesto il reset, ignora questa email.</p>
      <p style="color: #888; font-size: 12px;">Link diretto: {reset_url}</p>
    </div>
    """

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, to_email, msg.as_string())

@router.post("/forgot-password")
async def forgot_password(data: ForgotRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Risposta sempre uguale per sicurezza
    if not user or user.status != "active":
        return {"message": "Se l'email è registrata, riceverai le istruzioni."}

    # Genera token e salva su Redis
    token = secrets.token_urlsafe(32)
    redis_client.setex(f"reset:{token}", RESET_EXPIRY, str(user.id))

    # Invia email
    reset_url = f"https://homematrix.iotzator.com/reset-password?token={token}"
    try:
        send_reset_email(user.email, reset_url)
    except Exception as e:
        raise HTTPException(500, f"Errore invio email: {str(e)}")

    return {"message": "Se l'email è registrata, riceverai le istruzioni."}

@router.post("/reset-password")
async def reset_password(data: ResetRequest, db: AsyncSession = Depends(get_db)):
    if data.new_password != data.confirm_password:
        raise HTTPException(400, "Le password non coincidono")

    err = validate_password(data.new_password)
    if err:
        raise HTTPException(400, err)

    user_id = redis_client.get(f"reset:{data.token}")
    if not user_id:
        raise HTTPException(400, "Token non valido o scaduto")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Utente non trovato")

    user.hashed_password = hash_password(data.new_password)
    await db.commit()
    redis_client.delete(f"reset:{data.token}")
    return {"message": "Password reimpostata con successo"}

@router.get("/reset-password/validate")
async def validate_token(token: str):
    user_id = redis_client.get(f"reset:{token}")
    if not user_id:
        raise HTTPException(400, "Token non valido o scaduto")
    return {"valid": True}
