"""Ghi flow co nguoi ngoi xem: doc man, bam thu, chot, luu thanh case YAML.

`record` la duong DUY NHAT sinh flow. `check` khong bao gio tu mo UI ra mo -
AI bam loan tren may that co the mua hang, gui form, dang xuat.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from usv import cli_record, record_session
from usv.adb_parsers import AdbError
from usv.flow_yaml import load
from usv.ui_dump_brief import brief

DUMP = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
<node index="0" text="" resource-id="" class="android.widget.FrameLayout"
 package="com.x" content-desc="" clickable="false" enabled="true"
 visible-to-user="true" bounds="[0,0][1080,2280]">
 <node index="0" text="Bắt đầu" resource-id="com.x:id/btnStart"
  class="android.widget.Button" package="com.x" content-desc=""
  clickable="true" enabled="true" visible-to-user="true" bounds="[100,200][300,400]" />
 <node index="1" text="" resource-id="com.x:id/card" class="android.widget.FrameLayout"
  package="com.x" content-desc="thẻ 1" clickable="true" enabled="true"
  visible-to-user="true" bounds="[0,500][540,800]" />
 <node index="2" text="" resource-id="com.x:id/card" class="android.widget.FrameLayout"
  package="com.x" content-desc="thẻ 2" clickable="true" enabled="true"
  visible-to-user="true" bounds="[540,500][1080,800]" />
 <node index="3" text="" resource-id="" class="android.view.View" package="com.x"
  content-desc="" clickable="false" enabled="true" visible-to-user="true"
  bounds="[0,900][1080,1000]" />
</node></hierarchy>"""


class FakeAdb:
    def __init__(self) -> None:
        self.taps: list[tuple[float, float]] = []
        self.keys: list[str] = []

    async def devices(self):
        from usv.adb_parsers import Device
        return [Device(serial="FAKE1", state="device", model="Pixel")]

    async def screen_metrics(self, serial):
        return (1080, 2280), 440

    async def dump_ui(self, serial):
        return DUMP

    async def input_tap(self, serial, x, y):
        self.taps.append((x, y))

    async def input_keyevent(self, serial, name):
        self.keys.append(name)

    async def input_text(self, serial, text):
        self.keys.append(f"type:{text}")

    async def force_stop(self, serial, package):
        self.keys.append("force_stop")

    async def launch(self, serial, package):
        self.keys.append("launch")


@pytest.fixture
def adb(monkeypatch):
    fake = FakeAdb()
    monkeypatch.setattr(cli_record, "make_client", lambda: fake)
    return fake


@pytest.fixture
def phien(tmp_path, monkeypatch):
    """Phien ghi nam trong tmp de test khong dam vao file that."""
    monkeypatch.setattr(record_session, "SESSION_DIR", tmp_path)
    return tmp_path


def chay(argv, phien_dir):
    return cli_record.main([*argv, "--out", str(phien_dir)])


# --- dump gon ---

def test_dump_bo_node_khong_bam_duoc_va_khong_co_chu(metrics):
    from usv.ui_dump import parse_dump

    dong = brief(parse_dump(DUMP, metrics))
    assert not any("android.view.View" in d for d in dong), dong
    assert any("btnStart" in d for d in dong)


def test_dump_danh_so_node_trung_resource_id(metrics):
    """4 card cung mot resource_id la chuyen that - khong danh so thi khong
    viet duoc selector tro dung card nao."""
    from usv.ui_dump import parse_dump

    dong = [d for d in brief(parse_dump(DUMP, metrics)) if "card" in d]
    assert len(dong) == 2
    assert "index=0" in dong[0] and "index=1" in dong[1], dong


def test_dump_du_gon_de_doc_bang_mat(metrics):
    from usv.ui_dump import parse_dump

    assert len(brief(parse_dump(DUMP, metrics))) <= 50


# --- ghi case ---

def test_tap_bam_that_va_ghi_lai_buoc(adb, phien):
    assert chay(["--package", "com.x", "tap", "--id", "btnStart"], phien) == 0
    assert adb.taps == [(200.0, 300.0)]
    steps = json.loads((phien / "record-com.x.json").read_text(encoding="utf-8"))
    assert steps["steps"] == [{"kind": "tap", "resource_id": "btnStart", "index": 0}]


def test_tap_khong_thay_node_thi_khong_ghi_buoc_ma(adb, phien, capsys):
    ma = chay(["--package", "com.x", "tap", "--id", "khong_co"], phien)
    assert ma != 0
    assert not (phien / "record-com.x.json").exists()


def test_selector_theo_chu_bi_canh_bao(adb, phien, capsys):
    """Khop theo chu thi vo khi app doi ngon ngu - nguoi ngoi xem phai biet."""
    chay(["--package", "com.x", "tap", "--text", "Bắt đầu"], phien)
    assert "ngôn ngữ" in capsys.readouterr().err


def test_save_ghi_ra_file_flow_doc_lai_duoc(adb, phien, tmp_path):
    chay(["--package", "com.x", "tap", "--id", "btnStart"], phien)
    chay(["--package", "com.x", "wait", "2"], phien)
    flows = tmp_path / "flows" / "com.x.yaml"
    ma = chay(["--package", "com.x", "save", "--event", "widget_show",
               "--label", "tại home", "--flows", str(flows)], phien)

    assert ma == 0
    flow = load(flows)
    assert flow.ok, flow.errors
    assert flow.cases[0].event == "widget_show"
    assert [s.kind for s in flow.cases[0].steps] == ["tap", "wait"]


def test_save_xong_thi_phien_trong_de_ghi_case_tiep(adb, phien, tmp_path):
    chay(["--package", "com.x", "tap", "--id", "btnStart"], phien)
    flows = tmp_path / "flows" / "com.x.yaml"
    chay(["--package", "com.x", "save", "--event", "e1", "--flows", str(flows)], phien)
    chay(["--package", "com.x", "tap", "--id", "btnStart"], phien)
    chay(["--package", "com.x", "save", "--event", "e2", "--flows", str(flows)], phien)

    flow = load(flows)
    assert [c.event for c in flow.cases] == ["e1", "e2"]
    assert all(len(c.steps) == 1 for c in flow.cases), "buoc cua case truoc bi dinh sang"


def test_save_khi_chua_bam_gi_thi_bao_chu_khong_ghi_case_rong(adb, phien, tmp_path):
    flows = tmp_path / "flows" / "com.x.yaml"
    ma = chay(["--package", "com.x", "save", "--event", "e1", "--flows", str(flows)],
              phien)
    assert ma != 0
    assert not flows.exists()


def test_back_va_launch_cung_duoc_ghi_lai(adb, phien):
    chay(["--package", "com.x", "launch"], phien)
    chay(["--package", "com.x", "back"], phien)
    steps = json.loads((phien / "record-com.x.json").read_text(encoding="utf-8"))
    assert [s["kind"] for s in steps["steps"]] == ["launch", "key"]
    assert adb.keys == ["force_stop", "launch", "KEYCODE_BACK"]


def test_bo_phien_dang_ghi(adb, phien):
    chay(["--package", "com.x", "tap", "--id", "btnStart"], phien)
    chay(["--package", "com.x", "drop"], phien)
    assert not (phien / "record-com.x.json").exists()


def test_adb_chet_thi_bao_ro_khong_traceback(adb, phien, monkeypatch, capsys):
    async def hong(serial):
        raise AdbError("adb rớt cáp")
    monkeypatch.setattr(adb, "dump_ui", hong)
    ma = chay(["--package", "com.x", "dump"], phien)
    assert ma != 0
    assert "adb rớt cáp" in capsys.readouterr().err
