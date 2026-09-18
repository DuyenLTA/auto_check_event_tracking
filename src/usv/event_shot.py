"""Chup man hinh ngay khi mot event trong spec ban ra, de lam bang chung.

Vi sao can: cham "co ban hay khong" khong tra loi duoc "ban DUNG MAN khong".
Mot event ban dung ten nhung o man khac van la bug, ma log mot minh khong nhin
thay duoc.

HAI BANG CHUNG, gia tri khac han nhau - dung gop lam mot:

1. `screen_class` - lay tu chinh param `ga_screen_class` cua event. CHINH XAC
   tuyet doi, khong tre mot mili giay nao, vi no do Firebase gan vao dung luc
   logEvent. Nhung no chi biet ACTIVITY, khong biet tren Activity do dang co
   dialog gi. Do duoc: 40/42 event co param nay.

2. Anh chup - nhin thay duoc dialog/popup, thu ma screen_class mu tit. Doi lai
   no TRE: doc duoc dong log roi moi chup, tong cong ~0.7s tren may that
   (screencap do duoc 0.65s). Man nao doi nhanh hon thang do la anh chup ra
   man KE TIEP chu khong phai man luc event ban.

Nen `delay_ms` luon duoc ghi kem va luon in ra: mot tam anh khong noi no chup
tre bao lau la mot tam anh de nguoi doc ket luan sai ma rat tin tuong.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# Bat ten event ngay tren dong log tho, khong parse ca dong: viec nay chay
# trong vong doc stream, moi dong deu di qua day.
_DONG_EVENT = re.compile(r"origin=(?P<origin>\w+),name=(?P<name>[A-Za-z0-9_]+)")
_SCREEN_CLASS = re.compile(r"ga_screen_class\(_sc\)=(?P<v>[^,}]+)")
_TIME = re.compile(r"^(?P<ts>\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})")


@dataclass(frozen=True, slots=True)
class Shot:
    """Mot tam anh chup vi mot event."""

    event: str
    log_ts: str = ""            # gio dong log ghi event
    delay_ms: int = 0           # tre bao lau tu luc doc duoc dong den luc chup xong
    path: str = ""              # duong dan file PNG, rong = chup that bai
    screen_class: str = ""      # ga_screen_class cua chinh event do
    loi: str = ""               # vi sao khong chup duoc

    @property
    def dang_tin(self) -> bool:
        """Anh chup duoi 1 giay thi coi nhu con dung man.

        Nguong nay la quy uoc de trinh bay, KHONG phai do duoc: man nao doi
        nhanh hon 1s thi anh van sai. No chi de report thoi cai nao can doc ky.
        """
        return bool(self.path) and self.delay_ms < 1000

    def payload(self) -> dict:
        return {"event": self.event, "log_ts": self.log_ts,
                "delay_ms": self.delay_ms, "path": self.path,
                "screen_class": self.screen_class, "dang_tin": self.dang_tin,
                "loi": self.loi}


def doc_dong(line: str) -> tuple[str, str, str] | None:
    """Dong logcat -> (ten event, gio, screen_class), None neu khong phai event.

    Chi nhan `origin=app`: event Firebase tu ban (auto/am) khong thuoc pham vi
    spec, chup anh cho chung la tra tien 0.65s cho mot thu khong ai doc.
    """
    found = _DONG_EVENT.search(line)
    if found is None or found.group("origin") != "app":
        return None
    sc = _SCREEN_CLASS.search(line)
    ts = _TIME.match(line)
    return (found.group("name"),
            ts.group("ts") if ts else "",
            sc.group("v").strip() if sc else "")


async def chup(client, serial: str, thu_muc: Path, event: str,
               log_ts: str, screen_class: str, doc_luc: float) -> Shot:
    """Chup mot tam cho `event`. `doc_luc` la time.monotonic() luc doc duoc dong."""
    def ket_qua(path: str = "", loi: str = "") -> Shot:
        return Shot(event=event, log_ts=log_ts,
                    delay_ms=int((time.monotonic() - doc_luc) * 1000),
                    path=path, screen_class=screen_class, loi=loi)

    try:
        # Man tat thi screencap tra ve mot tam anh den hoan toan, khong bao loi.
        # `is_awake` doc dumpsys power - 0.03s, re hon nhieu so voi 0.65s chup
        # ra mot tam den roi moi biet.
        # Luu no lai con te hon khong luu: nguoi doc thay o trong va tuong app
        # hong chu khong tuong may dang khoa.
        if not await client.is_awake(serial):
            return ket_qua(loi="Màn hình đang tắt nên không chụp (ảnh sẽ đen).")
        png = await client.screencap(serial)
    except Exception as exc:       # noqa: BLE001 - chup hong khong duoc lam sap phien ghi
        log.warning("Chup man hinh cho %s that bai: %s", event, exc)
        return ket_qua(loi=str(exc))

    thu_muc.mkdir(parents=True, exist_ok=True)
    ten = f"{event}-{log_ts.replace(':', '').replace(' ', '-').replace('.', '')}.png"
    duong_dan = thu_muc / ten
    try:
        duong_dan.write_bytes(png)
    except OSError as exc:
        return ket_qua(loi=f"Không ghi được file: {exc}")
    return ket_qua(path=str(duong_dan))


async def chup_neu_can(client, recording, line: str) -> None:
    """Goi tu vong doc stream. Tu quyet dinh co chup hay khong.

    KHONG chan vong doc: chup mat 0.65s, ma vong doc dung 0.65s la pipe 64KB
    day va log bi mat am tham - dung cai bay ma `_pump` da mo ta. Nen ham nay
    chi tao task roi tra ve ngay.

    Bo qua khi dang co mot lan chup chay do: hai event ban cach nhau 50ms thi
    tam thu hai cung chi chup duoc dung man do, tra them 0.65s khong mua duoc
    gi. Tam bi bo duoc ghi lai de report noi ro, khong im lang.
    """
    doc_luc = time.monotonic()
    doc = doc_dong(line)
    if doc is None:
        return
    event, log_ts, screen_class = doc
    if event not in getattr(recording, "watch_events", ()):
        return
    if getattr(recording, "shot_busy", False):
        recording.shots.append(Shot(
            event=event, log_ts=log_ts, screen_class=screen_class,
            loi="Bỏ qua: đang chụp cho event trước đó."))
        return

    recording.shot_busy = True

    async def chay() -> None:
        try:
            recording.shots.append(await chup(
                client, recording.serial, Path(recording.shot_dir),
                event, log_ts, screen_class, doc_luc))
        finally:
            recording.shot_busy = False

    asyncio.create_task(chay())
