from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx, secrets

from app.db import get_db
from app.models import User
from app.auth.service import create_access_token
from app.config import settings

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

@router.get("/google/login")
async def google_login():
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = GOOGLE_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)

@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    # Scambia il codice con il token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        })
        if token_resp.status_code != 200:
            raise HTTPException(400, "Errore ottenimento token Google")
        
        tokens = token_resp.json()
        access_token = tokens.get("access_token")

        # Ottieni info utente
        user_resp = await client.get(GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"})
        if user_resp.status_code != 200:
            raise HTTPException(400, "Errore ottenimento info utente Google")
        
        google_user = user_resp.json()

    email = google_user.get("email")
    full_name = google_user.get("name", email)
    
    if not email:
        raise HTTPException(400, "Email non disponibile dall'account Google")

    # Cerca utente esistente
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Registra automaticamente come utente in attesa
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=secrets.token_hex(32),  # password casuale inutilizzabile
            status="pending",
            is_admin=False,
            google_auth=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        # Redirect alla pagina di attesa approvazione
        return RedirectResponse("https://homematrix.iotzator.com/?google=pending")

    if user.status != "active":
        return RedirectResponse("https://homematrix.iotzator.com/?google=pending")

    # Genera token e redirect
    token = create_access_token(str(user.id), user.is_admin)
    return RedirectResponse(f"https://homematrix.iotzator.com/?google_token={token}")
