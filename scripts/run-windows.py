"""Chay web UI tren Windows, co nap file .env.

Hai viec ma duong chay chinh (`start.sh`) khong lam duoc o day:

1. `uvicorn` tren Windows dat SelectorEventLoop, ma loop do KHONG lam duoc
   subprocess -> moi lenh adb do NotImplementedError, tuc toan bo phan cham
   may chet. Dat ProactorEventLoop truoc, roi bao uvicorn dung loop dang co
   (`loop="none"`) de no khong doi lai.

2. `confluence_client` doc thang `os.environ`, va start.sh khong doc `.env`.
   Tren Windows khong co `~/.bashrc` de `export`, nen doc `.env` o day.

KHONG in gia tri token ra log - chi bao co hay khong.

Chay tu goc repo:  .venv/Scripts/python.exe scripts/run-windows.py 8000
"""
import asyncio
import os
import sys
from pathlib import Path

import uvicorn

SECRET = ("TOKEN", "PASSWORD", "SECRET", "KEY")


def load_env(path: Path) -> None:
    """KEY=VALUE -> os.environ. Bien da co san trong moi truong thi khong de len:
    export o terminal phai thang file, khong thi khong the tam ghi de."""
    if not path.is_file():
        return
    dat = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if not value or key in os.environ:
            continue
        os.environ[key] = value
        dat += 1
        hidden = any(word in key.upper() for word in SECRET)
        print(f"[env] {key} = {'(da dat)' if hidden else value}", flush=True)
    if not dat:
        print(f"[env] {path} co nhung moi dong deu de trong", flush=True)


async def main(port: int) -> None:
    config = uvicorn.Config("usv.main:app", host="127.0.0.1", port=port,
                            loop="none", log_level="info")
    await uvicorn.Server(config).serve()


if __name__ == "__main__":
    load_env(Path(__file__).resolve().parent / ".env")
    load_env(Path.cwd() / ".env")
    for name in ("CONFLUENCE_BASE_URL", "CONFLUENCE_TOKEN"):
        state = "co" if os.environ.get(name) else "CHUA CO"
        print(f"[confluence] {name}: {state}", flush=True)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8000))
