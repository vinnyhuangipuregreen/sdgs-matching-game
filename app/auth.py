import hashlib
import secrets
import time
import json
import urllib.request
import urllib.error
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

    if raw_token.startswith("platform:"):
        request = urllib.request.Request(
            "https://sdgs-action-platform.vercel.app/api/auth/me",
            headers={"Authorization": "Bearer " + raw_token.removeprefix("platform:")},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                account = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (401, 403, 404):
                raise HTTPException(status_code=401, detail="管理登入已失效，請重新登入統一管理後台")
            raise HTTPException(status_code=503, detail="統一管理登入暫時無法驗證")
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise HTTPException(status_code=503, detail="統一管理登入暫時無法驗證")
        if account.get("account_type") != "staff" or account.get("role") not in ("admin", "teacher"):
            raise HTTPException(status_code=403, detail="此帳號沒有管理權限")
        return {"username": account["email"], "role": account["role"]}

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
