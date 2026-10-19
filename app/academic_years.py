"""Annual scope for public game records and authenticated administration."""
import json
import urllib.request
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from app.year_scope import current_year_id, initialize_scope, table_name

TABLES = ("goals", "targets", "scenarios", "challengers", "game_sessions", "game_details", "system_settings")
COPY_TABLES = ("goals", "targets", "scenarios", "system_settings")


def valid_public_year(year_id):
    with urllib.request.urlopen("https://sdgs-action-platform.vercel.app/api/academic-years", timeout=15) as response:
        years = json.load(response)
    return any(year["id"] == year_id for year in years)


class InitializeYear(BaseModel):
    id: int = Field(ge=2)
    source_id: int = Field(ge=1)


def install_years(app):
    from app.database import get_db_connection
    from app.auth import verify_admin_token, verified_platform_account

    @app.middleware("http")
    async def annual_scope(request: Request, call_next):
        if not request.url.path.startswith("/api/") or request.url.path.startswith("/api/admin/academic-years"):
            return await call_next(request)
        try:
            hint = request.headers.get("x-academic-year", request.query_params.get("academic_year_id"))
            year_id = int(hint or "1")
            auth = request.headers.get("authorization", "")
            account = None
            if auth.startswith("Bearer platform:"):
                account = await run_in_threadpool(verify_admin_token,authorization=auth,token=None)
                actual = account.get("academic_year_id", 1)
                if hint is not None and year_id != actual:
                    raise HTTPException(403, "請先切換學年度")
                year_id = actual
            if year_id != 1:
                if not await run_in_threadpool(valid_public_year,year_id):
                    raise HTTPException(404, "找不到可使用的學年度")
            scope = current_year_id.set(year_id)
            verified = verified_platform_account.set((auth.removeprefix("Bearer "),account) if account else None)
            try:
                return await call_next(request)
            finally:
                current_year_id.reset(scope)
                verified_platform_account.reset(verified)
        except HTTPException as error:
            return JSONResponse({"detail": error.detail}, status_code=error.status_code)
        except ValueError:
            return JSONResponse({"detail": "學年度參數無效"}, status_code=400)
        except (OSError, TimeoutError):
            return JSONResponse({"detail": "學年度暫時無法驗證"}, status_code=503)

    @app.post("/api/admin/academic-years/initialize")
    def initialize(item: InitializeYear, user=Depends(verify_admin_token)):
        conn = get_db_connection(unscoped=True)
        try:
            initialize_scope(conn, item.id, item.source_id, TABLES, COPY_TABLES)
            conn.commit()
        finally:
            conn.close()
        return {"success": True}

    @app.get("/api/admin/academic-years/{year_id}/dependencies")
    def dependencies(year_id: int, user=Depends(verify_admin_token)):
        if year_id < 1:
            raise HTTPException(400, "學年度參數無效")
        labels = {"goals": "[配對挑戰賽]目標資料", "targets": "[配對挑戰賽]細項資料", "scenarios": "[配對挑戰賽]情境題",
                  "challengers": "[配對挑戰賽]挑戰者", "game_sessions": "[配對挑戰賽]遊戲紀錄", "game_details": "[配對挑戰賽]作答紀錄"}
        conn = get_db_connection(unscoped=True)
        try:
            result = {}
            for name, label in labels.items():
                result[label] = conn.execute(f"SELECT COUNT(*) FROM {table_name(name,year_id)}").fetchone()[0]
            return result
        finally:
            conn.close()
