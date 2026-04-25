import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app import settings_store
from app.auth import require_admin
from app.database import get_db
from app.monitor import logger

router = APIRouter(tags=["settings"])

_EDITABLE = {
    "gallery_name": "Gallery Name",
}

_ENV_DISPLAY = [
    ("POS Provider",     "POS_PROVIDER",     "manual"),
    ("Email Provider",   "EMAIL_PROVIDER",   "log"),
    ("Payment Provider", "PAYMENT_PROVIDER", "check"),
    ("Base URL",         "BASE_URL",         "http://localhost:8000"),
]


@router.get("/admin/settings", response_class=HTMLResponse)
async def settings_page(request: Request, _: str = Depends(require_admin)):
    fields = {k: settings_store.get(k) for k in _EDITABLE}
    env_vars = [
        {"label": label, "key": key, "value": os.environ.get(key, default)}
        for label, key, default in _ENV_DISPLAY
    ]
    return templates.TemplateResponse(request, "admin/settings.html", {
        "active": "settings",
        "fields": fields,
        "env_vars": env_vars,
        "app_version": settings_store.APP_VERSION,
        "saved": request.query_params.get("saved") == "1",
    })


@router.post("/admin/settings")
async def settings_save(
    request: Request,
    gallery_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    await settings_store.save("gallery_name", gallery_name.strip(), db)
    logger.info("commonartist.settings.saved", gallery_name=gallery_name.strip())
    return RedirectResponse("/admin/settings?saved=1", status_code=303)
