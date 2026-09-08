"""FastAPI app: middleware bao ve loopback, serve web/.

Route nghiep vu nam o routes_*.py.

Route nghiep vu nam o routes_*.py.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .resources import web_dir
from .routes_device import router as device_router
from .routes_event import router as event_router
from .routes_event_report import router as event_report_router

WEB_DIR = web_dir()
LOOPBACK = {"127.0.0.1", "::1", "localhost"}

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Auto Check Event Tracking")
app.include_router(device_router)
app.include_router(event_router)
app.include_router(event_report_router)


@app.middleware("http")
async def loopback_only(request: Request, call_next):
    """Chan moi thu khong phai loopback, NGAY TRONG CODE.

    start.sh bind 127.0.0.1 nhung khong ngan duoc ai do chay tay
    `uvicorn usv.main:app --host 0.0.0.0` - luc do tool khong co auth ma lai
    dieu khien duoc adb (mo app, chen log, bam man hinh) se mo ra ca LAN.
    Middleware nay khong phu thuoc cach khoi dong.

    Kiem ca Host header -> chan luon DNS rebinding.
    """
    client_host = request.client.host if request.client else ""
    if client_host and client_host not in LOOPBACK:
        log.warning("Tu choi request tu %s", client_host)
        return JSONResponse({"detail": "Chi phuc vu localhost."}, status_code=403)

    host = (request.headers.get("host") or "").split(":")[0]
    if host and host not in LOOPBACK:
        return JSONResponse({"detail": f"Host '{host}' khong duoc phep."},
                            status_code=403)

    origin = request.headers.get("origin")
    if origin and origin.split("://")[-1].split(":")[0] not in LOOPBACK:
        # POST multipart la simple request, khong co preflight -> trang web bat ky
        # tester dang mo cung goi duoc API neu khong chan Origin.
        return JSONResponse({"detail": "Origin khong duoc phep."}, status_code=403)

    return await call_next(request)


@app.get("/")
async def index():
    path = (WEB_DIR / "index.html") if WEB_DIR else None
    if path is None or not path.is_file():
        return JSONResponse(
            {"detail": "Khong tim thay web/index.html. Chay tu thu muc repo, hoac "
                       "cai bang 'pip install -e .' thay vi 'pip install .'"},
            status_code=500,
        )
    return FileResponse(path)


if WEB_DIR and WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
