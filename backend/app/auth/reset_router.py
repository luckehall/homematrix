from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timedelta
import secrets, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.db import get_db
from app.models import User
from app.auth.service import hash_password, validate_password
from app.config import settings

router = APIRouter()

# Dizionario in memoria per i token di reset {token: (user_id, expires_at)}
reset_tokens = {}

class ForgotRequest(BaseModel):
    email: str

class ResetRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

def send_reset_email(to_email: str, reset_url: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "HomeMatrix — Reset password"
    msg["From"] = settings.SMTP_USER
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

    # Genera token
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(minutes=30)
    reset_tokens[token] = (str(user.id), expires)

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

    token_data = reset_tokens.get(data.token)
    if not token_data:
        raise HTTPException(400, "Token non valido o scaduto")

    user_id, expires = token_data
    if datetime.utcnow() > expires:
        del reset_tokens[data.token]
        raise HTTPException(400, "Token scaduto")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Utente non trovato")

    user.hashed_password = hash_password(data.new_password)
    await db.commit()
    del reset_tokens[data.token]

    return {"message": "Password reimpostata con successo"}

@router.get("/reset-password/validate")
async def validate_token(token: str):
    token_data = reset_tokens.get(token)
    if not token_data:
        raise HTTPException(400, "Token non valido o scaduto")
    _, expires = token_data
    if datetime.utcnow() > expires:
        del reset_tokens[token]
        raise HTTPException(400, "Token scaduto")
    return {"valid": True}
