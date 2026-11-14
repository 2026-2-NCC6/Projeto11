import os
import time
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.environ.get("TENNISYNC_SECRET_KEY", "tennisync-super-secret-jwt-key-2026-fecap")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

ADMIN_USERNAME = os.environ.get("TENNISYNC_USER", "admin")
ADMIN_PASSWORD = os.environ.get("TENNISYNC_PASSWORD", "tennis2026")

security_bearer = HTTPBearer(auto_error=False)

def verify_credentials(username: str, password: str) -> bool:
    """Validação em tempo constante contra timing-attacks."""
    user_match = hmac.compare_digest(username.strip(), ADMIN_USERNAME.strip())
    pass_match = hmac.compare_digest(password.strip(), ADMIN_PASSWORD.strip())
    return user_match and pass_match

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None

def extract_token_from_request(request: Request) -> Optional[str]:
    """
    Extrator Triplo:
    1. Header: Authorization: Bearer <token>
    2. Query param: ?token=<token> (WebSockets, <img>, <video>)
    3. Cookie: tennisync_token (enviado nativamente pelo navegador)
    """
    # 1. Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()

    # 2. Query param
    query_token = request.query_params.get("token")
    if query_token:
        return query_token.strip()

    # 3. Cookie
    cookie_token = request.cookies.get("tennisync_token")
    if cookie_token:
        return cookie_token.strip()

    return None

async def get_current_user(request: Request) -> dict:
    """
    Dependência FastAPI que garante autenticação estrita.
    Permite bypass para chamadas locais de manutenção (ex: 127.0.0.1 em scripts .bat).
    """
    # Bypass para manutenção local executada pelo próprio servidor
    client_host = request.client.host if request.client else ""
    is_localhost = client_host in ("127.0.0.1", "localhost", "::1")
    path = request.url.path

    # Endpoints de controle da câmera locais mantêm compatibilidade com scripts .bat
    if is_localhost and path in ("/api/camera/pause", "/api/camera/resume"):
        return {"sub": "system_local", "role": "admin"}

    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária. Token JWT ausente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload

async def get_optional_user(request: Request) -> Optional[dict]:
    token = extract_token_from_request(request)
    if not token:
        return None
    return decode_access_token(token)
