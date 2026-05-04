from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def render_template(request: Request, name: str, context: dict | None = None):
    payload = {"request": request}
    if context:
        payload.update(context)
    return templates.TemplateResponse(request, name, payload)


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return render_template(request, "index.html")


@router.get("/quant", response_class=HTMLResponse)
def quant_dashboard(request: Request):
    return render_template(request, "quant/dashboard.html")


@router.get("/predictor", response_class=HTMLResponse)
def predictor_index(request: Request):
    return render_template(request, "predictor/index.html")


@router.get("/assistant", response_class=HTMLResponse)
def assistant_index(request: Request):
    return render_template(request, "assistant/index.html")
