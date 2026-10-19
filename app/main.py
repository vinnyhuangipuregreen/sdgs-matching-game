import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, seed_db, is_using_turso, get_db_connection
from app import game_routes, admin_routes

app = FastAPI(
    title="SDGs 17項目標169項細項 配對遊戲系統",
    description="SDGs Matching Game with Challenger Tracking & Admin Management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    if is_using_turso():
        # Initialize once with migrate_to_turso.py, not on every cold start.
        conn = get_db_connection()
        try:
            if conn.execute("SELECT id FROM targets LIMIT 1").fetchone() is None:
                raise RuntimeError("Turso is empty; run python migrate_to_turso.py before deployment")
            conn.execute("SELECT token_hash FROM admin_sessions LIMIT 1")
        finally:
            conn.close()
    else:
        init_db()
        seed_db()

app.include_router(game_routes.router)
app.include_router(admin_routes.router)
from app.academic_years import install_years
install_years(app)

def resolve_static_dir():
    candidates = [
        Path(__file__).resolve().parent.parent / "static",
        Path(__file__).parent.parent / "static",
        Path.cwd() / "static"
    ]
    for c in candidates:
        if c.exists() and (c / "index.html").exists():
            return c
    return candidates[0]

STATIC_DIR = resolve_static_dir()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/healthz")
def healthz():
    conn = get_db_connection()
    try:
        conn.execute("SELECT 1").fetchone()
    finally:
        conn.close()
    return {"status": "ok", "database": "turso" if is_using_turso() else "sqlite"}

@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/admin")
def serve_admin():
    return FileResponse(STATIC_DIR / "admin.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
