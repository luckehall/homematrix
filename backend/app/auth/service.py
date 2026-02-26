from datetime import datetime, timedelta
from uuid import uuid4
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str, is_admin: bool, expires_minutes: int = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "is_admin": is_admin, "exp": expire, "temp": expires_minutes is not None},
        settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )

def create_refresh_token() -> str:
    return str(uuid4())

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None

def validate_password(password: str) -> str:
    """Valida la password e restituisce un messaggio di errore o stringa vuota."""
    if len(password) < 8:
        return "La password deve essere di almeno 8 caratteri"
    if not any(c.isupper() for c in password):
        return "La password deve contenere almeno una lettera maiuscola"
    if not any(c.isdigit() for c in password):
        return "La password deve contenere almeno un numero"
    return ""
