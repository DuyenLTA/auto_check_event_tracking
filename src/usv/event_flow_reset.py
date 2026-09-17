"""Dua app ve trang thai can thiet TRUOC khi chay step cua mot case.

Tach khoi `event_flow_run` vi day la phan duy nhat DOI trang thai may (sua
Remote Config, xoa prefs, mo lai app) - phan con lai chi doc man va bam. Reset
khong an -> BLOCKED chu khong bao gio FAIL: tien de chua dat thi chua do gi ca.
"""

from __future__ import annotations

import asyncio

from . import remote_config
from .event_flow_models import FlowCase

# Cho app ve man dau sau khi mo lai. Khong cho thi step dau bam vao splash.
# 1.5s la du: flow nao can lau hon thi dung `wait_text` cho DUNG man,
# cho cung them giay chi lam moi case dai them ma khong chac hon.
LAUNCH_SETTLE = 1.5


async def prepare(client, serial: str, package: str,
                  case: FlowCase) -> tuple[bool, str, list[str]]:
    """Reset + mo lai app + verify. Tra (di tiep duoc, ly do, ghi chu)."""
    notes: list[str] = []
    reset = case.reset

    if reset.clear_prefs:
        cleared = await remote_config.clear_prefs(
            client, serial, package, list(reset.clear_prefs))
        if not cleared.ok:
            return False, cleared.blocked, notes
        notes.extend(cleared.notes)

    if reset.remote_config:
        applied = await remote_config.override(
            client, serial, package, reset.remote_config)
        if not applied.ok:
            return False, applied.blocked, notes
        notes.extend(applied.notes)
        if applied.mirrors:
            notes.append("prefs mirror đã sửa: " + ", ".join(sorted(applied.mirrors)))

    if reset.relaunch:
        await client.force_stop(serial, package)
        await client.launch(serial, package)
        await asyncio.sleep(LAUNCH_SETTLE)

    if reset.remote_config:
        # Doc lai SAU khi mo lai app: build dev dat minimumFetchInterval = 0 thi
        # throttle vo hieu, app fetch that va de mat patch. Luc do tien de chua
        # dat -> BLOCKED, tuyet doi khong ket luan app sai.
        got = await remote_config.verify(client, serial, package, reset.remote_config)
        lech = {k: (v, got.get(k, "")) for k, v in reset.remote_config.items()
                if got.get(k, "") != str(v)}
        if lech:
            detail = ", ".join(f"{k}: cần {want!r} nhưng đang {have!r}"
                               for k, (want, have) in lech.items())
            return False, (
                "Remote Config không giữ được giá trị sau khi mở lại app "
                f"({detail}). Thường là bản build đặt minimumFetchInterval = 0 "
                "nên throttle vô hiệu và app fetch thật đè lên."), notes
    return True, "", notes
