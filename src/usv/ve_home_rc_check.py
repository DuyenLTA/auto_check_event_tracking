"""Bước `ve_home`: đưa app từ splash về Home bằng trình lái của rc-check (`rcr-sub ve-home`).

Màn đầu app (splash ad, xin quyền, chọn ngôn ngữ, onboarding, question, paywall, popup Add Widget) đổi theo bản SDK
và theo từng app. rc-check đã có walker chung `rcr.fo_flow.walk_to` đi qua đủ các màn đó cho mọi app VisionLab;
check-event không tự dò lại từng bước (app chưa có flow từng kẹt ở màn ngôn ngữ, AIP893 12/11/2026). Flow mới
mở đầu bằng `launch` + `ve_home` rồi mới tới các bước của SDK cần chấm.

Gọi qua tiến trình con thay vì import: hai repo có venv riêng.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

from .adb_parsers import AdbError

TIMEOUT_MAC_DINH = 300.0          # splash ad + onboarding nhiều trang + paywall: walker đo được 1-4 phút


def tim_rcr_sub() -> str:
    """Đường dẫn lệnh `rcr-sub`: env `RCR_SUB` → venv repo rc-check (env `RC_CHECK_REPO` / ~/Desktop) → PATH."""
    if os.environ.get("RCR_SUB"):
        return os.environ["RCR_SUB"]
    ten = "rcr-sub.exe" if sys.platform == "win32" else "rcr-sub"
    thu_muc = "Scripts" if sys.platform == "win32" else "bin"
    goc = [Path(os.environ["RC_CHECK_REPO"])] if os.environ.get("RC_CHECK_REPO") else []
    goc += [Path.home() / "Desktop" / "check_remote_config", Path.home() / "check_remote_config"]
    for g in goc:
        f = g / ".venv" / thu_muc / ten
        if f.is_file():
            return str(f)
    return shutil.which("rcr-sub") or ""


def doc_ket_qua(stdout: str) -> dict:
    """Dòng JSON cuối của `rcr-sub` → dict; không có JSON → {}."""
    for dong in reversed(stdout.strip().splitlines()):
        try:
            v = json.loads(dong)
        except ValueError:
            continue
        if isinstance(v, dict):
            return v
    return {}


async def ve_home(serial: str, package: str, timeout: float = TIMEOUT_MAC_DINH, out_dir: str = "out") -> str:
    """Chạy `rcr-sub ve-home`. Về được Home -> mô tả đường đi (ghi vào notes case); không -> AdbError."""
    lenh = tim_rcr_sub()
    if not lenh:
        raise AdbError("Không tìm thấy `rcr-sub` của rc-check (đặt RCR_SUB hoặc RC_CHECK_REPO) — "
                       "bước ve_home cần trình lái splash → Home của rc-check.")
    # Khoá máy của rcr-sub nằm trong out_dir của check-event: không đụng khoá của bot rc-check đang giữ lượt.
    p = await asyncio.create_subprocess_exec(
        lenh, "ve-home", "--serial", serial, "--package", package, "--out-dir", out_dir,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        ra, loi = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        p.kill()
        await p.wait()
        raise AdbError(f"ve_home quá {timeout:g}s chưa về được Home.") from None
    kq = doc_ket_qua(ra.decode("utf-8", "replace"))
    if p.returncode != 0 or not kq.get("reached"):
        dang_o = kq.get("activity") or (loi.decode("utf-8", "replace").strip().splitlines() or ["?"])[-1]
        raise AdbError(f"ve_home (trình lái rc-check) không về được Home, đang ở {dang_o}.")
    return f"về Home bằng trình lái rc-check ({kq.get('activity', '')}, đóng {kq.get('dong_popup', 0)} popup)"
