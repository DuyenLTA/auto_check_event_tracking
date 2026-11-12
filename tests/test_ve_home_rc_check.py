"""Buoc `ve_home`: qua splash / ngon ngu / onboarding bang trinh lai cua rc-check (`rcr-sub ve-home`)."""

import asyncio
import sys

import pytest

from usv import ve_home_rc_check as vh
from usv.adb_parsers import AdbError
from usv.flow_yaml import parse


def test_flow_doc_buoc_ve_home_timeout_mac_dinh_dai():
    flow = parse({"package": "p.ai", "cases": [{"event": "widget_show", "steps": [
        {"kind": "launch"}, {"kind": "ve_home"}, {"kind": "tap", "resource_id": "btn", "index": 0}]}]})
    assert not flow.errors
    buoc = flow.cases[0].steps[1]
    assert buoc.kind == "ve_home" and buoc.timeout == 300.0
    assert flow.cases[0].trigger_index == 2            # ve_home khong phai buoc kich hoat event


def test_doc_ket_qua_lay_dong_json_cuoi():
    assert vh.doc_ket_qua('log rac\n{"reached": true, "activity": "MainActivity"}\n') == {
        "reached": True, "activity": "MainActivity"}
    assert vh.doc_ket_qua("khong co json") == {}


def test_tim_rcr_sub_uu_tien_env_roi_venv_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("RCR_SUB", "/x/rcr-sub")
    assert vh.tim_rcr_sub() == "/x/rcr-sub"
    monkeypatch.delenv("RCR_SUB")
    thu_muc = "Scripts" if sys.platform == "win32" else "bin"
    f = tmp_path / ".venv" / thu_muc / ("rcr-sub.exe" if sys.platform == "win32" else "rcr-sub")
    f.parent.mkdir(parents=True)
    f.write_text("")
    monkeypatch.setenv("RC_CHECK_REPO", str(tmp_path))
    assert vh.tim_rcr_sub() == str(f)


def _gia_lap(monkeypatch, ma: int, ra: str):
    class P:
        returncode = ma

        async def communicate(self):
            return ra.encode(), b"LOI: may ban\n"

    goi = []

    async def tao(*lenh, **_kw):
        goi.append(lenh)
        return P()

    monkeypatch.setenv("RCR_SUB", "rcr-sub")
    monkeypatch.setattr(vh.asyncio, "create_subprocess_exec", tao)
    return goi


def test_ve_home_toi_home_tra_duong_di(monkeypatch):
    goi = _gia_lap(monkeypatch, 0, '{"reached": true, "activity": "HomeActivity", "dong_popup": 1}')
    duong = asyncio.run(vh.ve_home("S1", "p.ai", 5))
    assert goi[0][:6] == ("rcr-sub", "ve-home", "--serial", "S1", "--package", "p.ai")
    assert "HomeActivity" in duong and "1 popup" in duong


def test_ve_home_khong_toi_bao_dang_o_dau(monkeypatch):
    _gia_lap(monkeypatch, 0, '{"reached": false, "activity": "LanguageActivity"}')
    with pytest.raises(AdbError, match="LanguageActivity"):
        asyncio.run(vh.ve_home("S1", "p.ai", 5))
    _gia_lap(monkeypatch, 1, "")
    with pytest.raises(AdbError, match="may ban"):
        asyncio.run(vh.ve_home("S1", "p.ai", 5))
