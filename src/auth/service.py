import base64
import io
import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import pyotp
import qrcode
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config.settings import settings
from src.auth.models import AdminUser
from src.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

_ACCESS_TYPE = "access"
_REFRESH_TYPE = "refresh"


# ── Password ──────────────────────────────────────────────────────────────────

import hashlib

def _prepare(plain: str) -> bytes:
    # SHA-256 + base64 keeps input within bcrypt's 72-byte limit for any password length.
    return base64.b64encode(hashlib.sha256(plain.encode()).digest())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_prepare(plain), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode())
    except Exception:
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.AUTH_ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": username, "type": _ACCESS_TYPE, "exp": expire},
        settings.AUTH_SECRET_KEY,
        algorithm="HS256",
    )


def create_refresh_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.AUTH_REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": username, "type": _REFRESH_TYPE, "exp": expire},
        settings.AUTH_SECRET_KEY,
        algorithm="HS256",
    )


def verify_token(token: str, expected_type: str = _ACCESS_TYPE) -> str:
    """Decode and validate JWT; return username or raise AuthenticationError."""
    try:
        payload = jwt.decode(token, settings.AUTH_SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            raise AuthenticationError("Invalid token type")
        sub = payload.get("sub")
        if not sub:
            raise AuthenticationError("Token missing subject")
        return sub
    except JWTError as e:
        raise AuthenticationError(str(e)) from e


# ── Admin authentication ──────────────────────────────────────────────────────

async def authenticate_admin(
    username: str, password: str, totp_code: str | None, db: AsyncSession
) -> AdminUser:
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()

    # Always run bcrypt to prevent timing attacks even when user not found
    dummy_hash = "$2b$12$dummyhashfordummytimingprotection000000000000000000000"
    stored_hash = user.password_hash if user else dummy_hash
    valid = verify_password(password, stored_hash)

    if not user or not valid or not user.is_active:
        raise AuthenticationError("Authentication failed")

    if settings.ADMIN_TOTP_ENABLED:
        if not totp_code:
            raise AuthenticationError("Authentication failed")
        secret = decrypt_totp_secret(user.totp_secret_enc or "")
        if not pyotp.TOTP(secret).verify(totp_code, valid_window=1):
            raise AuthenticationError("Authentication failed")

    user.last_login = datetime.utcnow()
    await db.commit()
    return user


async def change_password(
    user: AdminUser, current_password: str, new_password: str, db: AsyncSession
) -> None:
    if len(new_password) < 12:
        raise ValueError("Password must be at least 12 characters")
    if not verify_password(current_password, user.password_hash):
        raise AuthenticationError("Authentication failed")
    user.password_hash = hash_password(new_password)
    await db.commit()


# ── TOTP ──────────────────────────────────────────────────────────────────────

def encrypt_totp_secret(secret: str) -> str:
    key = settings.ADMIN_TOTP_ENCRYPTION_KEY.encode()
    return Fernet(key).encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted: str) -> str:
    key = settings.ADMIN_TOTP_ENCRYPTION_KEY.encode()
    return Fernet(key).decrypt(encrypted.encode()).decode()


def generate_totp_qr_code(username: str, secret: str) -> str:
    """Return base64-encoded PNG of the TOTP QR code."""
    uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="ChatbotAdmin")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
