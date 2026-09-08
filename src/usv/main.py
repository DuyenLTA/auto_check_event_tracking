"""FastAPI app: middleware bao ve loopback, serve web/.

Route nghiep vu nam o routes_*.py.

CHUA CO ROUTE NAO: tang may (nap spec, ghi logcat, cat cua so, cham check,
render report) da xong va co test, nhung route HTTP + tab web la buoc sau. Xem
plans/260908-1521-event-tracking-auto-verify/phase-06-route-va-tab-web.md.
Den luc do goi truc tiep tu Python:

    from usv.event_spec_parse import parse_paste
    from usv.event_window import cut_log
    from usv import event_check_runner, report_event_html
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .resources import web_dir

WEB_DIR = web_dir()
LOOPBACK = {"127.0.0.1", "::1", "localhost"}

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Auto Check Event Tracking")


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
            {"detail": "Chua co tab web - xem docstring usv/main.py va "
                       "phase-06 trong plans/."},
            status_code=501,
        )
    return FileResponse(path)


if WEB_DIR and WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
