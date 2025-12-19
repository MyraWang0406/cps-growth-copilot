from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.merchant import router as merchant_router

app = FastAPI(title="Merchant Copilot API")


@app.get("/health")
def health():
    return {"status": "ok"}


# /merchant/*
app.include_router(merchant_router)


# /ui/merchant.html  (静态前端)
# repo_root/app/frontend/merchant.html
repo_root = Path(__file__).resolve().parents[2]
frontend_dir = repo_root / "app" / "frontend"

app.mount("/ui", StaticFiles(directory=str(frontend_dir), html=True), name="ui")
