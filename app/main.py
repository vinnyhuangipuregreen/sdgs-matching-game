import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, seed_db
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
    init_db()
    seed_db()

app.include_router(game_routes.router)
app.include_router(admin_routes.router)

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/admin")
def serve_admin():
    return FileResponse(STATIC_DIR / "admin.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
