import hashlib
import secrets
import time
from typing import Optional
from fastapi import Header, Query, HTTPException, status
from app.database import get_db_connection

SESSION_DURATION_SECONDS = 86400

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def create_admin_session(username: str, role: str = "admin") -> str:
    token = secrets.token_hex(24)
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM admin_sessions WHERE expires_at <= ?", (time.time(),))
        conn.execute(
            "INSERT INTO admin_sessions (token_hash, username, role, expires_at) VALUES (?, ?, ?, ?)",
            (hash_password(token), username, role, time.time() + SESSION_DURATION_SECONDS),
        )
        conn.commit()
    finally:
        conn.close()
    return token

def verify_admin_token(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> dict:
    raw_token = None
    if authorization:
        parts = authorization.split(" ")
        raw_token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少管理員認證標頭 (Missing Authorization header)"
        )

    conn = get_db_connection()
    try:
        session = conn.execute(
            "SELECT username, role, expires_at FROM admin_sessions WHERE token_hash = ? AND expires_at > ?",
            (hash_password(raw_token), time.time()),
        ).fetchone()
    finally:
        conn.close()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效或已過期的管理員憑證 (Invalid or expired admin token)"
        )
    return dict(session)
