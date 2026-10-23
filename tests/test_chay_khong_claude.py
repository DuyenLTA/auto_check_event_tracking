"""`usv-check --khong-claude`: mot lenh chay xong ca luot, khong can agent.

Ba dieu khong duoc pha:
  - Case lai hut tu chay lai (qua `--case` + `--base`), lan sau chay duoc thi
    report lay ket qua moi - day la viec agent tung lam tay.
  - Chay lai van hut thi report ghi "Can nguoi xem", KHONG phai "Luot chua xong,
    khong publish": khong co agent nao di sua nua.
  - Khong co co thi hanh vi y nhu cu: khong tu chay lai, van bang "Luot chua xong".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from test_cli_check import PACKAGE, SPEC_TSV, CliFakeAdb
from usv import cli_chay_lai, cli_main, logcat_stream

TRONG = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
         "<hierarchy rotation=\"0\"></hierarchy>")

FLOW_YAML = (f"package: {PACKAGE}\n"
             "cases:\n"
             "  - event: rating_placement_viewed\n"
             "    label: tai home\n"
             "    expect_params: {placement_name: home}\n"
             "    steps:\n"
             "      - {kind: tap, resource_id: btnHome}\n")


@pytest.fixture(autouse=True)
def _nhanh(monkeypatch):
    async def instant(_seconds):
        return None
    monkeypatch.setattr("usv.event_flow_run.asyncio.sleep", instant)
    monkeypatch.setattr(logcat_stream, "LAUNCH_SETTLE", 0)
    monkeypatch.setenv("DISCORD_NOTIFY", "0")


class ManLenCham(CliFakeAdb):
    """Lan dau nut chua len (man trong) - y nhu quang cao load lau. Tu luc
    `hien = True` thi nut co tren man."""

    def __init__(self) -> None:
        super().__init__()
        self.hien = False

    async def dump_ui(self, serial):
        return await super().dump_ui(serial) if self.hien else TRONG


def _chay(adb, tmp_path, monkeypatch, capsys, *co: str) -> tuple[int, dict, str]:
    spec_file = tmp_path / "spec.tsv"
    spec_file.write_text(SPEC_TSV, encoding="utf-8")
    flow_file = tmp_path / "flow.yaml"
    flow_file.write_text(FLOW_YAML, encoding="utf-8")
    monkeypatch.setattr(cli_main, "make_client", lambda: adb)
    code = cli_main.main(["--spec-tsv", str(spec_file), "--package", PACKAGE,
                          "--flows", str(flow_file), "--out", str(tmp_path), *co])
    out = capsys.readouterr()
    return code, json.loads(out.out) if out.out.strip() else {}, out.err


def _presence(payload: dict, event: str) -> str:
    return next(r["verdict"] for r in payload["results"]
                if r["element"] == event and r["check"] == "event_presence")


def test_case_hut_tu_chay_lai_va_lay_ket_qua_lan_sau(tmp_path, monkeypatch, capsys):
    adb = ManLenCham()
    ghi_that = cli_chay_lai.ghi_base

    def ghi_roi_cho_man_len(payload):
        adb.hien = True          # giua hai lan: quang cao da tat, nut da len
        return ghi_that(payload)

    monkeypatch.setattr(cli_chay_lai, "ghi_base", ghi_roi_cho_man_len)
    code, payload, err = _chay(adb, tmp_path, monkeypatch, capsys, "--khong-claude")

    assert code == 0
    assert "[chạy lại 1/1] 1 case hụt: tai home" in err
    assert payload["cases"][0]["status"] == "ok"
    assert _presence(payload, "rating_placement_viewed") == "PASS"
    assert payload["khong_claude"] is True


def test_chay_lai_van_hut_thi_report_ghi_can_nguoi_xem(tmp_path, monkeypatch, capsys):
    code, payload, err = _chay(ManLenCham(), tmp_path, monkeypatch, capsys,
                               "--khong-claude")

    assert code == 0
    assert "[chạy lại 1/1]" in err
    assert payload["cases"][0]["status"] == "not_tested"
    html = Path(payload["report"]).read_text(encoding="utf-8")
    assert "Cần người xem" in html
    assert "Lượt chưa xong" not in html


def test_khong_co_co_thi_khong_tu_chay_lai(tmp_path, monkeypatch, capsys):
    code, payload, err = _chay(ManLenCham(), tmp_path, monkeypatch, capsys)

    assert code == 0
    assert "chạy lại" not in err
    assert payload["khong_claude"] is False
    html = Path(payload["report"]).read_text(encoding="utf-8")
    assert "Lượt chưa xong" in html


def test_tu_chay_lai_0_thi_khong_chay_lai_du_khong_claude(tmp_path, monkeypatch, capsys):
    _, payload, err = _chay(ManLenCham(), tmp_path, monkeypatch, capsys,
                            "--khong-claude", "--tu-chay-lai", "0")
    assert "chạy lại" not in err
    assert payload["cases"][0]["status"] == "not_tested"


def test_case_hut_lay_dung_nhan_bo_trung_bo_case_ok():
    payload = {"cases": [{"case": "a", "status": "not_tested"},
                         {"case": "b", "status": "ok"},
                         {"case": "c", "status": "blocked"},
                         {"case": "a", "status": "not_tested"}]}
    assert cli_chay_lai.case_hut(payload) == ("a", "c")
    assert cli_chay_lai.case_hut({}) == ()


def test_chay_lai_khop_dung_nhan_khong_keo_case_co_nhan_chua_no():
    """"tu Home" nam trong "bam tab tu Home": khop chuoi con la chay lai ca case
    da PASS va de ket qua cua no."""
    from test_cli_check import _case
    from usv.cli_check import chon_case
    a, b = _case("ev_a", "từ Home"), _case("ev_b", "bấm tab từ Home")
    assert chon_case((a, b), ("từ Home",), chinh_xac=True) == (a,)
    # Go tay `--case` van la tu khoa, giu hanh vi cu.
    assert chon_case((a, b), ("từ Home",)) == (a, b)


def test_chay_lai_hong_thi_giu_ket_qua_luot_day_du(tmp_path, monkeypatch, capsys):
    def hong(_payload):
        raise OSError("đĩa đầy")

    monkeypatch.setattr(cli_chay_lai, "ghi_base", hong)
    code, payload, err = _chay(ManLenCham(), tmp_path, monkeypatch, capsys,
                               "--khong-claude")
    assert code == 0
    assert "bỏ dở, giữ kết quả lượt trước" in err
    assert payload["cases"][0]["status"] == "not_tested"
    assert Path(payload["report"]).exists()
