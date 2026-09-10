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

# Thu tu nap co y nghia: event.js dung window.USV_* cua cac file truoc no.
JS_FILES = ("event-api.js", "event-device.js",
            "event-spec.js", "event-artifact.js", "event-progress.js", "event-render.js", "event.js")

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
        # Thu tu goi co y nghia: logcat -c -> spawn -> force_stop -> launch.
        # Sai thu tu la mat cac event dau tien (first_open, session_start).
        self.calls: list[str] = []

    async def setprop(self, serial, key, value): return None
    async def getprop(self, serial, key): return "VERBOSE"
    async def logcat_clear(self, serial):
        self.calls.append("clear")
        return None
    async def force_stop(self, serial, package):
        self.calls.append("force_stop")
        return None

    foreground: str | None = None

    async def foreground_package(self, serial):
        return self.foreground

    async def home_package(self, serial):
        return "com.launcher"

    running: set | None = None

    async def app_running(self, serial, package):
        # Mac dinh: app "dang chay" khi co trong danh sach cai dat - du de phan
        # biet app that voi app go sai ten. Test doi `running` de dung ca app
        # co cai ma khong chay.
        if self.running is not None:
            return package in self.running
        return package in await self.packages(serial)
    async def launch(self, serial, package):
        self.calls.append("launch")
        return None

    async def logcat_spawn(self, serial, tags):
        self.calls.append("spawn")
        # Ong MOI moi lan spawn, y nhu `adb logcat` that. Tra lai ong cu thi
        # phien ghi thu hai thua luon trang thai dong cua phien truoc.
        self.process = FakeProcess()
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
    """Thieu mot the <script> la ca mot tinh nang im lang khong chay - khong co
    loi nao hien ra. JS o day khong duoc test don vi nen chan o day."""
    response = client.get("/")
    assert response.status_code == 200
    for asset in ("style.css", *JS_FILES):
        assert f"/static/{asset}" in response.text, f"index.html thieu {asset}"


@pytest.mark.parametrize("name", ["style.css", *JS_FILES])
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


# --- khong con o tick che do: tool tu suy ra theo viec CO BAM MOC hay khong ---

def _ghi(client, fake_adb, *, bam_moc: bool):
    """Ghi mot phien roi bom event vao stream. `bam_moc` -> co chen moc."""
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    for step, name in enumerate(("rating_placement_viewed", "rating_star_clicked"), 1):
        if bam_moc:
            # shell_log cua FakeAdb chen moc RO! roi bom luon event cua buoc do.
            client.post("/event/mark", json={"spec_event": name, "note": ""})
            continue
        stamp = f"09-08 15:00:{step:02d}"
        fake_adb.process.stdout.queue.append(
            (f"{stamp}.000 V/FA-SVC ( 9): Logging event: origin=app,"
             f"name={name},params=Bundle[{{{PARAMS[name]}}}]\n").encode())
    return client.post("/event/stop").json(), client.post("/event/check").json()


def test_khong_bam_moc_nao_thi_cham_ca_phien(client, fake_adb):
    """Khong bam moc = khong co bien buoc de so. Cat theo moc thi ra 0 cua so
    va MOI dong thanh 'chua test' - mot bao cao rong trong nhu that.

    Truoc day nguoi dung phai tick 'che do nhanh' TRUOC khi ghi, tuc quyet
    dinh khi chua biet minh co bam moc hay khong. Tick sai thi im lang.
    """
    stop, check = _ghi(client, fake_adb, bam_moc=False)
    assert stop["marker_count"] == 0
    assert stop["quick"] is True, "khong moc -> tu suy ra la cham ca phien"
    assert stop["window_count"] == 2, "mot cua so cho moi event trong spec"
    assert check["summary"]["not_tested"] == 0
    assert check["summary"]["pass"] == 5


def test_co_bam_moc_thi_cat_theo_moc(client, fake_adb):
    """Chieu nguoc lai: co moc thi phai cat theo moc de con cham duoc THOI
    DIEM. Suy ra sai chieu nay thi mat han nang luc do."""
    stop, check = _ghi(client, fake_adb, bam_moc=True)
    assert stop["marker_count"] == 2
    assert stop["quick"] is False, "co moc -> cat theo moc"
    assert check["quick"] is False
    assert check["summary"]["fail"] == 0


def test_bao_cao_noi_ro_da_cham_ca_phien(client, fake_adb):
    _, check = _ghi(client, fake_adb, bam_moc=False)
    assert check["quick"] is True
    page = client.get("/event/report").text
    assert "chế độ nhanh" in page.lower()


def test_record_khong_con_nhan_tham_so_quick(client, fake_adb):
    """Bo o tick roi thi than server cung khong duoc doc `quick` tu client -
    de lai thi mot client cu van lai duoc hanh vi ma UI khong con hien."""
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app",
                                       "quick": False})
    client.post("/event/stop")
    assert client.get("/event/state").json()["quick"] is True, (
        "khong moc nao -> van phai la cham ca phien, bo qua `quick` client gui")


def test_index_co_cho_hien_canh_bao_dut_giua_phien(client):
    """Watcher ghi canh bao vao #record-alert. Thieu the do thi no nem loi vao
    console va tester khong thay gi - dung kieu im lang can chan."""
    assert 'id="record-alert"' in client.get("/").text


# --- may rot giua phien ghi ---

def _record(client, fake_adb):
    client.post("/event/spec", json={"text": SPEC_TSV})
    return client.post("/event/record",
                       json={"serial": "FAKE1", "package": "com.example.app"})


def test_may_rot_thi_ghi_lai_duoc_ngay(client, fake_adb):
    """Stream chet roi thi KHONG con dang ghi - phai cho Ghi lai.

    Truoc day guard chi xem `stopped`, ma `stopped` chi bat o stop(). May rot
    khoi USB -> stopped=False -> bam Ghi lai an 409 "Dang ghi roi" tren mot
    phien ghi da chet. Thong bao sai su that, va tester phai Reset (mat luon
    spec da dan) moi thoat ra duoc.
    """
    assert _record(client, fake_adb).status_code == 200
    fake_adb.process.stdout.closed = True          # may rot khoi USB
    for _ in range(50):                            # cho pump nhan ra EOF
        if client.get("/event/state").json()["recording"]["stream_died"]:
            break
    assert client.get("/event/state").json()["recording"]["stream_died"] is True

    again = client.post("/event/record",
                        json={"serial": "FAKE1", "package": "com.example.app"})
    assert again.status_code == 200, (
        "stream da chet thi phai ghi lai duoc, khong duoc bao 'Dang ghi roi'")
    assert again.json()["recording"]["stream_died"] is False, "phien moi phai sach"


def test_dang_ghi_that_thi_van_chan(client, fake_adb):
    """Chieu nguoc lai: phien con song thi Ghi lan hai phai bi chan.

    Thieu test nay thi mot bug bo han guard cung xanh, va hai process logcat
    cung doc mot may se an mat log cua nhau.
    """
    assert _record(client, fake_adb).status_code == 200
    again = client.post("/event/record",
                        json={"serial": "FAKE1", "package": "com.example.app"})
    assert again.status_code == 409


# --- nap spec tu link Confluence ---

CONFLUENCE_HTML = (FIXTURES / "confluence-event-table.html").read_text(encoding="utf-8")


def test_nap_spec_tu_link_confluence(client, monkeypatch):
    """Duong nay doc duoc bang co rowspan - dan tay thi khong."""
    monkeypatch.setattr(routes_event, "fetch_page",
                        lambda url: ("SDK Widget V 1.0.0", CONFLUENCE_HTML))
    response = client.post("/event/spec/confluence", json={"url": "https://x.vn/pages/1"})
    assert response.status_code == 200
    body = response.json()
    assert body["errors"] == []
    assert body["event_count"] == 1
    assert body["source"] == "SDK Widget V 1.0.0"
    assert body["stage"] == "ready_to_record"


def test_loi_mang_tra_502_chu_khong_phai_500(client, monkeypatch):
    """Token sai/mat mang la loi HE THONG - phai noi cach sua, khong phai stacktrace."""
    from usv.confluence_client import ConfluenceError

    def boom(url):
        raise ConfluenceError("Confluence tra 401 - token sai hoac het han.")

    monkeypatch.setattr(routes_event, "fetch_page", boom)
    response = client.post("/event/spec/confluence", json={"url": "https://x.vn/pages/1"})
    assert response.status_code == 502
    assert "token" in response.json()["detail"]


def test_trang_khong_co_bang_tra_200_kem_loi(client, monkeypatch):
    """Trang doc duoc ma khong co bang = loi DU LIEU, giong duong dan tay."""
    monkeypatch.setattr(routes_event, "fetch_page",
                        lambda url: ("Trang khac", "<p>chi tro sang Google Sheet</p>"))
    response = client.post("/event/spec/confluence", json={"url": "https://x.vn/pages/1"})
    assert response.status_code == 200
    assert response.json()["errors"], "phai noi ro trang khong co bang event"


def test_index_co_o_dan_link_confluence(client):
    page = client.get("/").text
    assert 'id="spec-url"' in page and 'id="btn-spec-url"' in page


def test_link_go_sai_tra_400_chu_khong_502(client, monkeypatch):
    """400 = loi cua nguoi dung. Tra 502 thi tester di kiem tra VPN thay vi
    doc lai cai link."""
    response = client.post("/event/spec/confluence", json={"url": "khong-phai-link"})
    assert response.status_code == 400


@pytest.mark.parametrize("path", ["/", "/static/event.js"])
def test_trang_va_asset_bat_trinh_duyet_hoi_lai(client, path):
    """Khong co Cache-Control thi trinh duyet suy doan thoi han theo tuoi file
    va F5 khong hoi lai server. Da mat may luot debug vi tester chay ban JS cu
    trong khi ca hai cung soi code moi."""
    assert client.get(path).headers.get("cache-control") == "no-cache"


def test_nap_spec_moi_thi_bo_luon_phien_ghi_cu(client, fake_adb, monkeypatch):
    """Spec moi = lam lai tu dau. Giu lai phien ghi cu thi stage ket o
    'ready_to_check': nut Ghi khoa, nut Cham mo, va tester ket cung - Reset thi
    mat luon spec vua nap.

    Da gap that: chay xong mot luot roi nap spec khac -> khong bam Ghi duoc nua.
    """
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    client.post("/event/stop")
    assert client.get("/event/state").json()["stage"] == "ready_to_check"

    client.post("/event/spec", json={"text": SPEC_TSV})
    state = client.get("/event/state").json()
    assert state["stage"] == "ready_to_record", "nap spec moi phai cho ghi lai"
    assert state["recording"] is None


def test_nap_spec_tu_link_cung_bo_phien_ghi_cu(client, fake_adb, monkeypatch):
    """Hai duong nap spec phai hanh xu giong het nhau."""
    monkeypatch.setattr(routes_event, "fetch_page",
                        lambda url: ("T", CONFLUENCE_HTML))
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    client.post("/event/stop")

    client.post("/event/spec/confluence", json={"url": "https://x.vn/pages/1"})
    assert client.get("/event/state").json()["stage"] == "ready_to_record"


def test_dang_ghi_ma_nap_spec_moi_thi_dung_han_phien_cu(client, fake_adb):
    """Khong dung han thi process logcat cu con treo, doc song song voi phien
    sau va an mat log cua nhau."""
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    assert client.get("/event/state").json()["stage"] == "recording"

    client.post("/event/spec", json={"text": SPEC_TSV})
    assert client.get("/event/state").json()["stage"] == "ready_to_record"
    assert fake_adb.process.returncode is not None, "phai kill process logcat cu"










# --- tim thay package thi tu mo, khong thay thi de tester tu mo (KHONG chan) ---

def test_tim_thay_package_thi_tool_tu_mo_app(client, fake_adb):
    client.post("/event/spec", json={"text": SPEC_TSV})
    body = client.post("/event/record", json={"serial": "FAKE1",
                                              "package": "com.example.app"}).json()
    assert body["launched"] is True
    assert "launch" in fake_adb.calls, "phai goi launch"
    assert "force_stop" in fake_adb.calls, "phai tat app truoc de property co hieu luc"


def test_khong_thay_package_van_ghi_va_de_tester_tu_mo(client, fake_adb):
    """KHONG chan: van phai ghi, va ghi TU DAU de bat duoc event luc mo app.

    Chan thi tester khong test duoc app ma `pm list packages` khong tra ra.
    Nhung tool cung khong duoc tu mo bua: `monkey` voi app khong ton tai in
    "No activities found to run" ma tra exit 0, mo that bai trong im lang roi
    ghi log cua app dang mo san.
    """
    client.post("/event/spec", json={"text": SPEC_TSV})
    response = client.post("/event/record", json={"serial": "FAKE1",
                                                  "package": "com.khong.he.co"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["launched"] is False, "khong thay app thi KHONG duoc tu mo"
    assert "launch" not in fake_adb.calls, "mo bua se mo sai app"
    assert client.get("/event/state").json()["stage"] == "recording"
    assert "mở app" in body["hint"].lower(), body["hint"]


def test_goi_y_ten_gan_giong_khi_go_lech_mot_chu(client, fake_adb):
    client.post("/event/spec", json={"text": SPEC_TSV})
    body = client.post("/event/record", json={"serial": "FAKE1",
                                              "package": "com.example.ap"}).json()
    assert body["launched"] is False
    assert "com.example.app" in body["hint"]


def test_stream_mo_TRUOC_khi_mo_app(client, fake_adb):
    """Ghi tu dau: phai mo stream logcat roi moi mo app, khong thi mat cac
    event dau tien (first_open, session_start)."""
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    calls = fake_adb.calls
    assert calls.index("spawn") < calls.index("launch")
    assert calls.index("clear") < calls.index("spawn")


def test_goi_y_app_DANG_MO_khi_dan_sai_ten(client, fake_adb):
    """App dang mo la su that quan sat duoc, manh hon so khop chuoi.

    Da gap that: dan 'com.ai.aiimage.aivideo.generator' trong khi may co
    'com.ai.aiimage.aivideogenerator' - thua mot dau cham, va ca phien ghi
    khong ket luan duoc gi.
    """
    fake_adb.foreground = "com.other.app"
    client.post("/event/spec", json={"text": SPEC_TSV})
    body = client.post("/event/record", json={"serial": "FAKE1",
                                              "package": "com.khong.he.co"}).json()
    assert body["launched"] is False
    assert "com.other.app" in body["hint"], body["hint"]
    assert "KHÔNG kết luận được gì" in body["hint"]


def test_dan_sai_ten_tu_mo_app_thi_van_cham_duoc(client, fake_adb):
    """Dan sai ten + tu mo app bang tay -> tool phai NHAN RA app dang mo va
    cham cho app do, khong bo cuoc.

    Truoc day: `pidof <ten sai>` mai mai rong -> app_seen=False -> ca phien ra
    "khong verify duoc". Tester lam dung het moi thu ma khong nhan duoc ket
    luan nao, chi vi mot dau cham go lech.
    """
    fake_adb.foreground = "com.example.app"          # app tester tu mo
    client.post("/event/spec", json={"text": SPEC_TSV})
    body = client.post("/event/record", json={"serial": "FAKE1",
                                              "package": "com.example.ap"}).json()
    assert body["launched"] is False
    for name in ("rating_placement_viewed", "rating_star_clicked"):
        fake_adb.process.stdout.queue.append(
            (f"09-08 15:00:01.000 V/FA-SVC ( 9): Logging event: origin=app,"
             f"name={name},params=Bundle[{{{PARAMS[name]}}}]\n").encode())
    stop = client.post("/event/stop").json()
    rec = stop["recording"]
    assert rec["app_seen"] is True, "app dang mo -> phai coi la da thay app chay"
    assert rec["checked_package"] == "com.example.app", "phai cham cho app dang mo"
    check = client.post("/event/check").json()
    assert check["summary"]["pass"] == 5
    assert check["checked_package"] == "com.example.app"


def test_bao_cao_noi_ro_da_cham_cho_app_nao(client, fake_adb):
    """Doi app duoi test ma khong noi ra thi bao cao noi ve mot app khac han
    app tester nghi minh dang test."""
    fake_adb.foreground = "com.example.app"
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.ap"})
    client.post("/event/stop")
    client.post("/event/check")
    page = client.get("/event/report").text
    assert "com.example.ap'" in page or "com.example.ap<" in page, "phai neu ten da dan"
    assert "com.example.app" in page, "va ten app da cham"


def test_dan_dung_ten_ma_app_khong_chay_thi_KHONG_doi_sang_app_khac(client, fake_adb):
    """Ten dan CO tren may nhung app khong chay -> khong duoc am tham doi sang
    app dang mo. Luc do co gi sai that (app crash, mo khong len), va doi sang
    app khac la bao cao ve mot app tester khong he chon."""
    fake_adb.foreground = "com.other.app"
    fake_adb.running = set()          # khong app nao chay
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    stop = client.post("/event/stop").json()
    assert stop["recording"]["app_seen"] is False
    assert stop["recording"]["checked_package"] == "com.example.app"
    check = client.post("/event/check").json()
    assert check["summary"]["pass"] == 0


def test_doan_app_lay_cai_xuat_hien_nhieu_nhat_va_loai_launcher():
    """Doan theo SO LAN o foreground, khong theo mau cuoi cung.

    Lay mau luc Dung ghi thi cai gi dang tren man luc do thang - da do duoc
    tren may: bat ra com.google.android.apps.nexuslauncher va bao cao ghi "da
    cham cho launcher", vo nghia.
    """
    from usv.event_recording import Recording
    from usv.event_session import doan_app

    rec = Recording(serial="S1", package="com.go.sai")
    rec.home_package = "com.google.android.apps.nexuslauncher"
    rec.foreground_seen = {
        "com.google.android.apps.nexuslauncher": 9,   # launcher, phai loai
        "com.android.systemui": 4,                    # system UI, phai loai
        "com.that.su.app": 6,
        "com.thoang.qua": 1,
    }
    assert doan_app(rec) == "com.that.su.app"


def test_doan_app_tra_rong_khi_chi_thay_launcher():
    from usv.event_recording import Recording
    from usv.event_session import doan_app

    rec = Recording(serial="S1", package="com.go.sai")
    rec.home_package = "com.launcher"
    rec.foreground_seen = {"com.launcher": 5, "com.android.systemui": 2}
    assert doan_app(rec) == "", "khong duoc cham cho launcher"


# --- link artifact ---

ARTIFACT = "https://claude.ai/code/artifact/43b243a5-cb0f-4482-9601-042ba7cacc73"


def test_chua_publish_thi_khong_co_link(client, monkeypatch, tmp_path):
    from usv import artifact_link
    monkeypatch.setattr(artifact_link, "duong_dan", lambda goc=None: tmp_path / "x.json")
    assert client.get("/event/artifact").json().get("url") is None


def test_publish_roi_thi_tra_link_va_noi_ro_luot_nao(client, fake_adb, monkeypatch, tmp_path):
    """`khop` phai phan biet artifact CUA LUOT NAY voi artifact luot cu.

    Thieu no thi nut artifact luon trong nhu moi, va mot bao cao cu bi gui cho
    team nhu bao cao cua lan chay vua roi - im lang va sai.
    """
    from usv import artifact_link
    monkeypatch.setattr(artifact_link, "duong_dan", lambda goc=None: tmp_path / "x.json")
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    client.post("/event/stop")
    check = client.post("/event/check").json()
    luot = client.get("/event/state").json()

    # publish cho DUNG luot nay
    client.post("/event/artifact", json={"url": ARTIFACT,
                                         "generated_at": check.get("generated_at", "")})
    body = client.get("/event/artifact").json()
    assert body["url"] == ARTIFACT
    assert body["khop"] is (body["generated_at"] == body["run_generated_at"])
    assert luot["stage"] == "done"


def test_artifact_luot_cu_thi_bao_KHONG_khop(client, fake_adb, monkeypatch, tmp_path):
    from usv import artifact_link
    monkeypatch.setattr(artifact_link, "duong_dan", lambda goc=None: tmp_path / "x.json")
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1", "package": "com.example.app"})
    client.post("/event/stop")
    client.post("/event/check")
    client.post("/event/artifact", json={"url": ARTIFACT,
                                         "generated_at": "2020-01-01 00:00"})
    body = client.get("/event/artifact").json()
    assert body["khop"] is False, "artifact cua luot khac phai bao khong khop"


def test_url_khong_phai_https_bi_tu_choi(client, monkeypatch, tmp_path):
    """Nut nay se duoc bam va gui cho nguoi khac - khong nhan url la."""
    from usv import artifact_link
    monkeypatch.setattr(artifact_link, "duong_dan", lambda goc=None: tmp_path / "x.json")
    r = client.post("/event/artifact", json={"url": "javascript:alert(1)"})
    assert r.status_code == 400


# --- day noi: route phai truyen event CA PHIEN vao check ---

def test_route_cham_truyen_event_ca_phien_vao_check(client, fake_adb, monkeypatch):
    """Thieu tham so nay thi tool im lang tro ve hanh vi bao THIEU OAN.

    Check presence chi phan biet duoc "app khong ban" voi "app ban ngoai buoc
    da danh dau" khi nhan duoc event cua ca phien. Quen truyen o tang route thi
    unit test cua check van xanh ma nguoi dung van nhan fail oan - da la dung
    benh nay o cho khac. Xem tests/test_event_ngoai_cua_so.py.
    """
    from usv import event_check_runner, routes_event_check

    thay: dict = {}
    goc = event_check_runner.run

    def spy(*args, **kwargs):
        thay.update(kwargs)
        return goc(*args, **kwargs)

    monkeypatch.setattr(routes_event_check.event_check_runner, "run", spy)
    client.post("/event/spec", json={"text": SPEC_TSV})
    client.post("/event/record", json={"serial": "FAKE1",
                                       "package": "com.example.app"})
    client.post("/event/mark", json={"spec_event": "rating_placement_viewed",
                                     "note": ""})
    client.post("/event/stop")
    assert client.post("/event/check").status_code == 200
    names = [e.name for e in thay.get("session_events", ())]
    assert "rating_placement_viewed" in names, sorted(thay)
