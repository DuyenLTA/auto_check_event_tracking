"""Chot chan cho tang chup man hinh lam bang chung.

Khong test duoc "anh co dung man khong" - cai do phu thuoc may that. Test o day
la nhung thu sai thi im lang: chup cho event ngoai spec (tra tien 0.65s moi
tam), chan vong doc log, va luu mot tam anh den ma khong noi gi.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from usv import event_shot
from usv.event_recording import Recording

DONG = ('09-15 09:50:29.110 29299 28327 V FA-SVC  : Logging event: '
        'origin=app,name=rating_placement_viewed,params=Bundle[{placement_name=home, '
        'ga_screen_class(_sc)=AIP922Main, ga_screen_id(_si)=78}]')
PNG = b"\x89PNG" + b"x" * 64


class Client:
    def __init__(self, awake: bool = True, no: Exception | None = None) -> None:
        self.awake, self.no, self.lan_chup = awake, no, 0

    async def is_awake(self, serial: str) -> bool:
        return self.awake

    async def screencap(self, serial: str) -> bytes:
        self.lan_chup += 1
        if self.no is not None:
            raise self.no
        return PNG


def _rec(tmp: Path, client, watch=("rating_placement_viewed",)) -> Recording:
    return Recording(serial="S", package="p", client=client,
                     shot_dir=str(tmp), watch_events=frozenset(watch))


def test_doc_dong_lay_ten_gio_va_screen_class():
    assert event_shot.doc_dong(DONG) == (
        "rating_placement_viewed", "09-15 09:50:29.110", "AIP922Main")


def test_bo_qua_event_firebase_tu_ban():
    """origin=auto/am khong thuoc pham vi spec - chup cho chung la tra 0.65s
    cho mot thu khong ai doc."""
    assert event_shot.doc_dong(DONG.replace("origin=app", "origin=auto")) is None


def test_bo_qua_dong_khong_phai_event():
    assert event_shot.doc_dong("09-15 09:50:29.110 V FA-SVC: Upload scheduled") is None


def test_man_tat_thi_khong_chup(tmp_path):
    """screencap luc man tat tra ve anh den ma khong bao loi. Luu tam do con te
    hon khong luu: nguoi doc tuong app hong chu khong tuong may dang khoa."""
    client = Client(awake=False)
    shot = asyncio.run(event_shot.chup(
        client, "S", tmp_path, "e", "09-15 09:50:29.110", "Main", 0.0))
    assert client.lan_chup == 0
    assert not shot.path and "tắt" in shot.loi


def test_chup_hong_thi_ghi_ly_do_chu_khong_nem_len(tmp_path):
    shot = asyncio.run(event_shot.chup(
        Client(no=RuntimeError("adb chet")), "S", tmp_path, "e",
        "09-15 09:50:29.110", "Main", 0.0))
    assert not shot.path and "adb chet" in shot.loi


def test_chup_thanh_cong_ghi_file_va_giu_screen_class(tmp_path):
    shot = asyncio.run(event_shot.chup(
        Client(), "S", tmp_path, "rating_placement_viewed",
        "09-15 09:50:29.110", "AIP922Main", 0.0))
    assert Path(shot.path).read_bytes() == PNG
    assert shot.screen_class == "AIP922Main"


def test_chi_chup_event_trong_spec(tmp_path):
    client = Client()
    rec = _rec(tmp_path, client, watch=("event_khac",))
    asyncio.run(event_shot.chup_neu_can(client, rec, DONG))
    assert client.lan_chup == 0 and rec.shots == []


def test_khong_chan_vong_doc_log(tmp_path):
    """chup_neu_can phai tra ve NGAY. Chan vong doc 0.65s la du lam day pipe
    64KB va mat log am tham - xem docstring _pump."""
    async def chay():
        rec = _rec(tmp_path, Client())
        await event_shot.chup_neu_can(rec.client, rec, DONG)
        chua_xong = len(rec.shots)          # task chup chua kip chay
        await asyncio.sleep(0.2)
        return chua_xong, len(rec.shots)
    chua_xong, xong = asyncio.run(chay())
    assert (chua_xong, xong) == (0, 1)


def test_dang_co_lan_chup_chay_do_thi_bo_qua_nhung_van_ghi_lai(tmp_path):
    rec = _rec(tmp_path, Client())
    rec.shot_busy = True
    asyncio.run(event_shot.chup_neu_can(rec.client, rec, DONG))
    assert len(rec.shots) == 1 and not rec.shots[0].path
    assert "Bỏ qua" in rec.shots[0].loi


@pytest.mark.parametrize("tre, mong_doi", [(0, True), (999, True), (1000, False)])
def test_tre_qua_mot_giay_thi_khong_con_dang_tin(tre, mong_doi):
    assert event_shot.Shot(event="e", path="/x.png", delay_ms=tre).dang_tin is mong_doi


def test_khong_co_anh_thi_khong_dang_tin():
    assert event_shot.Shot(event="e", delay_ms=0).dang_tin is False
