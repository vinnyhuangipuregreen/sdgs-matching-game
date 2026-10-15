import uvicorn
from app.main import app

if __name__ == "__main__":
    print("啟動 SDGs 配對遊戲系統 (http://localhost:8000)...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
