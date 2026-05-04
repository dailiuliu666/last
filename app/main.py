from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import assistant, pages, predictor, quant


app = FastAPI(title=settings.app_name)
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(pages.router)
app.include_router(assistant.router)
app.include_router(quant.router)
app.include_router(predictor.router)


@app.get("/health")
def health():
    return {"success": True, "app": settings.app_name, "env": settings.app_env}
