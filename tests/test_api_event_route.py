"""Route HTTP - goi QUA TestClient, khong goi ham truc tiep.

Vi sao bat buoc: mot lan thieu `import` trong than ham da khong bi 410 test bat,
vi moi test e2e luc do goi ham truc tiep va bo qua tang route. Test o day phai
di qua dung duong ma browser di.

Co test tu chung minh dieu do: test_thieu_import_bi_bat.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from usv import logcat_stream, routes_event

FIXTURES = Path(__file__).parent / "fixtures"
SPEC_TSV = (FIXTURES / "event-spec-rating.tsv").read_text(encoding="utf-8")
BROKEN_TSV = (FIXTURES / "event-spec-broken.tsv").read_text(encoding="utf-8")
RAW_LOG = (FIXTURES / "fa-events-aip922.log").read_text(encoding="utf-8")

_LINE = re.compile(r"Logging event: origin=app,name=([^,(]+)[^,]*,params=Bundle\[\{(.*)\}\]")
# Ten event -> phan params, lay tu log THAT.
PARAMS = {m.group(1): m.group(2) for m in
          (_LINE.search(line) for line in RAW_LOG.splitlines()) if m}


class FakeStdout:
    """Doi khi rong thi CHO chu khong tra EOF - stream that cung vay.

    Tra EOF ngay khi rong thi task doc ket thuc som, roi moc chen sau do khong
    ai doc nua.
    """

    def __init__(self) -> None:
        self.queue: list[bytes] = []
        self.closed = False

    async def readline(self) -> bytes:
        while not self.queue and not self.closed:
            await asyncio.sleep(0.001)
        return self.queue.pop(0) if self.queue else b""


class FakeProcess:
    def __init__(self) -> None:
        self.stdout = FakeStdout()
        self.returncode = None

    def kill(self) -> None:
        self.stdout.closed = True
        self.returncode = -9

    async def wait(self) -> int:
        return -9


class FakeAdb:
    """AdbClient gia. shell_log chen moc RO! roi bom luon event cua buoc do -
    dung thu tu that: bam moc -> thao tac -> app ban event."""

    adb = "/fake/adb"

    def __init__(self) -> None:
        self.process = FakeProcess()
        self.step = 0
        self.marks: list[str] = []

    async def setprop(self, serial, key, value): return None
    async def getprop(self, serial, key): return "VERBOSE"
    async def logcat_clear(self, serial): return None
    async def force_stop(self, serial, package): return None
    async def launch(self, serial, package): return None

    async def logcat_spawn(self, serial, tags):
        return self.process

    async def shell_log(self, serial, tag, message):
        self.marks.append(message)
        self.step += 1
        stamp = f"09-08 15:00:{self.step:02d}"
        self.process.stdout.queue.append(
            f"{stamp}.000 I/USV_MARK( 9): {message}\n".encode())
        name = message.split(" | ")[0]
        if name in PARAMS:
            self.process.stdout.queue.append(
                (f"{stamp}.500 V/FA-SVC ( 9): Logging event: origin=app,"
                 f"name={name},params=Bundle[{{{PARAMS[name]}}}]\n").encode())

    async def devices(self):
        from usv.adb_parsers import Device
        return [Device(serial="FAKE1", state="device", model="Pixel")]

    async def packages(self, serial):
        return ["com.example.app", "com.other.app"]


@pytest.fixture
def fake_adb(monkeypatch):
    adb = FakeAdb()
    monkeypatch.setattr(routes_event, "client", lambda: adb)
    monkeypatch.setattr("usv.routes_device.client", lambda: adb)
    monkeypatch.setattr(logcat_stream, "LAUNCH_SETTLE", 0)
    return adb


# --- spec ---

def test_spec_that_tra_2_event(client):
    response = client.post("/event/spec", json={"text": SPEC_TSV})
    assert response.status_code == 200
    body = response.json()
    assert body["event_count"] == 2
    assert body["param_count"] == 3
    assert body["errors"] == []
    assert body["stage"] == "ready_to_record"


def test_spec_gay_dong_tra_200_kem_loi_chu_khong_phai_500(client):
    """Spec sai la loi DU LIEU cua tester, khong phai loi server."""
    response = client.post("/event/spec", json={"text": BROKEN_TSV})
    assert response.status_code == 200
    body = response.json()
    assert body["errors"], "phai bao loi tung dong"
    assert body["stage"] == "need_spec"


def test_spec_rong_thi_khong_cho_di_tiep(client):
    body = client.post("/event/spec", json={"text": ""}).json()
    assert body["stage"] == "need_spec"


# --- chan sai thu tu ---

def test_ghi_khi_chua_co_spec_tra_409(client, fake_adb):
    response = client.post("/event/record",
                           json={"serial": "FAKE1", "package": "com.example.app"})
    assert response.status_code == 409


def test_ghi_khi_spec_con_loi_tra_409(client, fake_adb):
    client.post("/event/spec", json={"text": BROKEN_TSV})
    response = client.post("/event/record",
                           json={"serial": "FAKE1", "package": "com.example.app"})
    assert response.status_code == 409


def test_danh_dau_khi_chua_ghi_tra_409(client):
    client.post("/event/spec", json={"text": SPEC_TSV})
    response = client.post("/event/mark",
                           json={"spec_event": "rating_star_clicked"})
    assert response.status_code == 409


def test_cham_khi_chua_dung_tra_409(client, fake_adb):
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    assert client.post("/event/check").status_code == 409


def test_report_khi_chua_cham_tra_409(client):
    assert client.get("/event/report").status_code == 409
    assert client.get("/event/report.xlsx").status_code == 409


def test_danh_dau_event_khong_co_trong_spec_tra_400(client, fake_adb):
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    response = client.post("/event/mark", json={"spec_event": "khong_ton_tai"})
    assert response.status_code == 400


# --- luong day du ---

def _full_flow(client):
    assert client.post("/event/spec", json={"text": SPEC_TSV}).json()["errors"] == []
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    for name in ("rating_placement_viewed", "rating_star_clicked"):
        assert client.post("/event/mark", json={"spec_event": name, "note": "khi nao"}
                           ).status_code == 200
    stop = client.post("/event/stop").json()
    return stop, client.post("/event/check").json()


def test_luong_day_du_ra_ket_qua_dung(client, fake_adb):
    stop, check = _full_flow(client)
    assert stop["marker_count"] == 2
    assert stop["window_count"] == 2
    summary = check["summary"]
    assert summary["fail"] == 0, [r for r in check["results"] if r["verdict"] != "PASS"]
    assert summary["pass"] == 5     # 2 presence + 3 param
    assert check["fa_silent"] is False
    assert check["stage"] == "done"


def test_report_html_render_duoc_sau_khi_cham(client, fake_adb):
    _full_flow(client)
    response = client.get("/event/report")
    assert response.status_code == 200
    assert "Event Tracking Diff" in response.text
    assert "rating_placement_viewed" in response.text


def test_xlsx_tai_duoc_sau_khi_cham(client, fake_adb):
    """exporter.build tung tham chieu summary.unmatched - field da bo. Khong co
    test nao goi qua route thi loi do khong ai thay."""
    _full_flow(client)
    response = client.get("/event/report.xlsx")
    assert response.status_code == 200
    assert response.content[:2] == b"PK", "xlsx la file zip"
    assert "attachment" in response.headers["content-disposition"]


def test_reset_xoa_sach_trang_thai(client, fake_adb):
    _full_flow(client)
    body = client.post("/event/reset").json()
    assert body["stage"] == "need_spec"
    assert body["spec"] is None
    assert client.get("/event/report").status_code == 409


def test_state_tra_rong_khi_chua_nap_gi(client):
    body = client.get("/event/state").json()
    assert body["stage"] == "need_spec"
    assert body["spec"] is None


def test_config_doc_duoc(client):
    body = client.get("/event/config").json()
    assert "event_presence" in body["enabled_checks"]
    assert "event_params" in body["enabled_checks"]


# --- device ---

def test_liet_ke_may_va_app(client, fake_adb):
    devices = client.get("/devices").json()
    assert devices["devices"][0]["serial"] == "FAKE1"
    packages = client.get("/packages?serial=FAKE1").json()
    assert "com.example.app" in packages["packages"]


def test_loi_adb_thanh_502_chu_khong_phai_500(client, monkeypatch):
    from usv.adb_parsers import AdbError

    class Broken:
        adb = "/fake/adb"

        async def devices(self):
            raise AdbError("device offline")

    monkeypatch.setattr("usv.routes_device.client", lambda: Broken())
    response = client.get("/devices")
    assert response.status_code == 502
    assert "offline" in response.json()["detail"]


# --- middleware + web asset ---

def test_middleware_chan_non_loopback():
    from fastapi.testclient import TestClient

    from usv import main

    with TestClient(main.app, base_url="http://10.0.0.5",
                    client=("10.0.0.5", 5000)) as outside:
        assert outside.get("/event/state").status_code == 403


def test_trang_chu_tra_ve_html_va_tro_dung_asset(client):
    response = client.get("/")
    assert response.status_code == 200
    for asset in ("/static/style.css", "/static/event-marks.js",
                  "/static/event-render.js", "/static/event.js"):
        assert asset in response.text, f"index.html thieu {asset}"


@pytest.mark.parametrize("name", ["style.css", "event.js", "event-marks.js",
                                  "event-render.js"])
def test_asset_serve_duoc(client, name):
    assert client.get(f"/static/{name}").status_code == 200


def test_thieu_import_bi_bat(client, fake_adb, monkeypatch):
    """Chung minh test nay CO TAC DUNG.

    Xoa mot ten module dung trong than ham -> route phai 500. Neu test suite
    khong di qua route thi loi kieu nay lot luoi.
    """
    monkeypatch.delattr(routes_event, "parse_log")
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    with pytest.raises(Exception):
        client.post("/event/stop")


# --- che do nhanh: khong danh dau buoc ---

def _quick_flow(client, fake_adb):
    """Ghi che do nhanh: khong bam moc, chi bom event vao stream."""
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app",
                                       "quick": True})
    step = 0
    for name in ("rating_placement_viewed", "rating_star_clicked"):
        step += 1
        stamp = f"09-08 15:00:{step:02d}"
        fake_adb.process.stdout.queue.append(
            (f"{stamp}.000 V/FA-SVC ( 9): Logging event: origin=app,"
             f"name={name},params=Bundle[{{{PARAMS[name]}}}]\n").encode())
    return client.post("/event/stop").json(), client.post("/event/check").json()


def test_che_do_nhanh_khong_can_moc_van_cham_duoc(client, fake_adb):
    """Cat theo moc thi 0 moc = 0 cua so = moi dong 'chua test'."""
    stop, check = _quick_flow(client, fake_adb)
    assert stop["quick"] is True
    assert stop["marker_count"] == 0
    assert stop["window_count"] == 2, "mot cua so cho moi event trong spec"
    assert check["summary"]["not_tested"] == 0
    assert check["summary"]["fail"] == 0
    assert check["summary"]["pass"] == 5


def test_che_do_nhanh_bao_ra_trong_ket_qua_va_trong_report(client, fake_adb):
    _, check = _quick_flow(client, fake_adb)
    assert check["quick"] is True
    page = client.get("/event/report").text
    assert "chế độ nhanh" in page.lower()


def test_che_do_nhanh_ghi_canh_bao_vao_xlsx(client, fake_adb):
    """Nguoi doc xlsx thuong la dev, ho khong thay callout ban HTML."""
    _quick_flow(client, fake_adb)
    assert client.get("/event/report.xlsx").status_code == 200


def test_che_do_thuong_van_can_moc(client, fake_adb):
    """Khong bam moc o che do thuong -> chua test, KHONG phai fail."""
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app",
                                       "quick": False})
    client.post("/event/stop")
    check = client.post("/event/check").json()
    assert check["quick"] is False
    assert check["summary"]["not_tested"] == 2
    assert check["summary"]["fail"] == 0


def test_state_giu_co_quick(client, fake_adb):
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app",
                                       "quick": True})
    assert client.get("/event/state").json()["quick"] is True
    client.post("/event/reset")
    assert client.get("/event/state").json()["quick"] is False


def test_index_tro_dung_ca_5_file_js(client):
    response = client.get("/")
    for asset in ("event-marks.js", "event-api.js", "event-device.js",
                  "event-render.js", "event.js"):
        assert f"/static/{asset}" in response.text, f"index.html thieu {asset}"


@pytest.mark.parametrize("name", ["event-api.js", "event-device.js"])
def test_asset_moi_serve_duoc(client, name):
    assert client.get(f"/static/{name}").status_code == 200
