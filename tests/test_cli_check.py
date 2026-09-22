"""CLI `check`: mot lenh tu nap spec -> lai may -> cham -> report.

Ba dieu khong duoc pha, moi dieu mot test:
  - Event co trong spec ma flow khong co case -> NOT_TESTED kem "chua co flow",
    KHONG phai FAIL. Chua lai toi thi chua do gi ca.
  - Case lai hut (step chet) -> van co mat trong report, kem ten step chet.
    Bien mat khoi report la im lang va sai.
  - 0 may / >1 may -> message doc duoc, khong phai traceback.
  - Case cua SDK khac (event khong co trong spec dang cham) KHONG duoc chay:
    no lai that tren may va doi trang thai cua app.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from conftest import PARAMS, FakeAdb
from usv import cli_check, cli_main, logcat_stream
from usv.adb_parsers import AdbError, Device
from usv.density import ScreenMetrics
from usv.device_actions import Selector
from usv.event_flow_models import Flow, FlowCase, Step
from usv.event_spec_parse import parse_paste

FIXTURES = Path(__file__).parent / "fixtures"
SPEC_TSV = (FIXTURES / "event-spec-rating.tsv").read_text(encoding="utf-8")
# Event thu ba: co trong spec, KHONG co case trong flow.
SPEC_3_EVENT = SPEC_TSV + (
    "Home\trating_dismissed\tKhi user dong man rating\t\t\t\t\t\n")

DUMP = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0"><node index="0" text="" resource-id="" class="a.b.FrameLayout"
 package="com.example.app" content-desc="" clickable="false" enabled="true"
 visible-to-user="true" bounds="[0,0][1080,2280]"><node index="0" text="Home"
 resource-id="com.example.app:id/btnHome" class="a.b.TextView" package="com.example.app"
 content-desc="" clickable="true" enabled="true" visible-to-user="true"
 bounds="[100,200][300,400]" /></node></hierarchy>"""

PACKAGE = "com.example.app"
PNG = b"\x89PNG\r\n\x1a\n" + b"gia-lap"


class CliFakeAdb(FakeAdb):
    """FakeAdb cua test route + nhung gi rieng duong CLI can (lai may that)."""

    def __init__(self) -> None:
        super().__init__()
        self.taps = 0
        self.awake = True
        self.devices_found = [Device(serial="FAKE1", state="device", model="Pixel")]

    async def devices(self):
        return list(self.devices_found)

    async def setprop(self, serial, key, value):
        # Thu tu setprop <-> force_stop la thu duoc khang dinh trong test, nen
        # phai ghi lai lan goi chu khong nuot im.
        self.calls.append("setprop")

    async def screen_metrics(self, serial):
        return (1080, 2280), 440

    async def dump_ui(self, serial):
        return DUMP

    async def input_tap(self, serial, x, y):
        self.taps += 1

    async def input_keyevent(self, serial, name):
        return None

    async def input_text(self, serial, text):
        return None

    async def is_debuggable(self, serial, package):
        return True

    async def package_version(self, serial, package):
        return ("2.4.1", "125")

    async def is_awake(self, serial):
        return self.awake

    async def wake(self, serial):
        self.awake = True
        self.calls.append("wake")

    async def screencap(self, serial):
        return PNG


@pytest.fixture(autouse=True)
def _nhanh(monkeypatch):
    """Bo moi khoang cho - test khong duoc ngoi doi app khoi dong."""
    async def instant(_seconds):
        return None
    monkeypatch.setattr("usv.event_flow_run.asyncio.sleep", instant)
    monkeypatch.setattr(logcat_stream, "LAUNCH_SETTLE", 0)


@pytest.fixture
def adb():
    return CliFakeAdb()


def _case(event: str, label: str = "", expect: dict | None = None) -> FlowCase:
    return FlowCase(event=event, name=label, expect_params=expect or {},
                    steps=(Step(kind="tap",
                                selector=Selector(resource_id="btnHome")),))


def _flow(*cases: FlowCase) -> Flow:
    return Flow(package=PACKAGE, cases=tuple(cases))


def _run(adb, spec_text: str, flow: Flow | None, out_dir: Path, **kw) -> dict:
    return asyncio.run(cli_check.check(
        spec=parse_paste(spec_text), package=PACKAGE, flow=flow,
        adb=adb, out_dir=out_dir, **kw))


def _verdict_of(payload: dict, event: str) -> str:
    for row in payload["results"]:
        if row["element"] == event and row["check"] == "event_presence":
            return row["verdict"]
    raise AssertionError(f"khong thay dong presence cua {event!r}")


def _message_of(payload: dict, event: str) -> str:
    for row in payload["results"]:
        if row["element"] == event and row["check"] == "event_presence":
            return row["message"]
    return ""


def test_event_khong_co_case_trong_flow_ra_NOT_TESTED_kem_chua_co_flow(adb, tmp_path):
    payload = _run(adb, SPEC_3_EVENT, _flow(
        _case("rating_placement_viewed", "tai home", {"placement_name": "home"}),
        _case("rating_star_clicked", "5 sao")), tmp_path)

    assert _verdict_of(payload, "rating_dismissed") == "NOT_TESTED"
    assert "chưa có" in _message_of(payload, "rating_dismissed").lower()
    assert payload["fail"] == 0, "khong lai toi thi khong duoc ket luan FAIL"


def test_chua_co_flow_thi_moi_event_NOT_TESTED_khong_phai_FAIL(adb, tmp_path):
    payload = _run(adb, SPEC_TSV, None, tmp_path)
    assert payload["fail"] == 0
    assert payload["not_tested"] >= 2
    assert "flow" in _message_of(payload, "rating_placement_viewed").lower()


def test_case_lai_hut_van_co_mat_trong_report_kem_step_chet(adb, tmp_path):
    hong = FlowCase(event="rating_placement_viewed", name="tai home",
                    steps=(Step(kind="tap",
                                selector=Selector(resource_id="khong_co_nut_nay")),))
    payload = _run(adb, SPEC_TSV, _flow(hong), tmp_path)

    assert _verdict_of(payload, "rating_placement_viewed") == "NOT_TESTED"
    message = _message_of(payload, "rating_placement_viewed")
    assert "khong_co_nut_nay" in message, message
    assert payload["fail"] == 0
    assert payload["cases"][0]["status"] == "not_tested"


def test_case_chay_duoc_va_app_ban_dung_thi_PASS(adb, tmp_path):
    payload = _run(adb, SPEC_TSV, _flow(
        _case("rating_placement_viewed", "tai home", {"placement_name": "home"}),
        _case("rating_star_clicked", "5 sao")), tmp_path)
    assert _verdict_of(payload, "rating_placement_viewed") == "PASS"
    assert payload["pass"] >= 1


def test_report_duoc_ghi_ra_file(adb, tmp_path):
    payload = _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")), tmp_path)
    report = Path(payload["report"])
    assert report.exists()
    html = report.read_text(encoding="utf-8")
    assert "rating_placement_viewed" in html
    assert PACKAGE in html


def test_khong_co_may_thi_bao_ro_khong_traceback(adb, tmp_path):
    adb.devices_found = []
    with pytest.raises(cli_check.CliError) as err:
        _run(adb, SPEC_TSV, None, tmp_path)
    assert "máy" in str(err.value)


def test_nhieu_may_ma_khong_chi_dinh_serial_thi_bao_ro(adb, tmp_path):
    adb.devices_found = [Device(serial="A1", state="device", model="Pixel"),
                         Device(serial="B2", state="device", model="Samsung")]
    with pytest.raises(cli_check.CliError) as err:
        _run(adb, SPEC_TSV, None, tmp_path)
    assert "A1" in str(err.value) and "B2" in str(err.value)
    assert "--serial" in str(err.value)


def test_nhieu_may_co_serial_thi_chay_dung_may_do(adb, tmp_path):
    adb.devices_found = [Device(serial="A1", state="device", model="Pixel"),
                         Device(serial="B2", state="device", model="Samsung")]
    payload = _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")),
                   tmp_path, serial="B2")
    assert payload["serial"] == "B2"


def test_may_chua_authorize_khong_duoc_tinh_la_may_dung_duoc(adb, tmp_path):
    adb.devices_found = [Device(serial="A1", state="unauthorized", model="")]
    with pytest.raises(cli_check.CliError) as err:
        _run(adb, SPEC_TSV, None, tmp_path)
    assert "A1" in str(err.value)


def test_enable_fa_chay_TRUOC_moi_lan_mo_lai_app(adb, tmp_path):
    """setprop chi an tu lan app khoi dong SAU no. Dat sau relaunch la logcat
    im, va moi event thanh 'thieu' oan."""
    _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")), tmp_path)
    assert "setprop" in adb.calls
    assert adb.calls.index("setprop") < adb.calls.index("force_stop"), adb.calls


def test_stdout_dung_MOT_dong_JSON(adb, tmp_path, monkeypatch, capsys):
    spec_file = tmp_path / "spec.tsv"
    spec_file.write_text(SPEC_TSV, encoding="utf-8")
    flow_file = tmp_path / "flow.yaml"
    flow_file.write_text(
        f"package: {PACKAGE}\n"
        "cases:\n"
        "  - event: rating_placement_viewed\n"
        "    label: tai home\n"
        "    expect_params: {placement_name: home}\n"
        "    steps:\n"
        "      - {kind: tap, resource_id: btnHome}\n", encoding="utf-8")
    monkeypatch.setattr(cli_main, "make_client", lambda: adb)

    code = cli_main.main(["--spec-tsv", str(spec_file), "--package", PACKAGE,
                           "--flows", str(flow_file), "--out", str(tmp_path)])
    out = capsys.readouterr()
    assert code == 0
    assert len(out.out.strip().splitlines()) == 1, out.out
    payload = json.loads(out.out)
    assert payload["package"] == PACKAGE
    assert Path(payload["report"]).exists()
    # Tien do phai o stderr - lan vao stdout la agent doc JSON hong.
    assert "case" in out.err.lower()


def test_loi_bao_ra_stderr_va_ma_thoat_khac_0(adb, tmp_path, monkeypatch, capsys):
    adb.devices_found = []
    spec_file = tmp_path / "spec.tsv"
    spec_file.write_text(SPEC_TSV, encoding="utf-8")
    monkeypatch.setattr(cli_main, "make_client", lambda: adb)

    code = cli_main.main(["--spec-tsv", str(spec_file), "--package", PACKAGE,
                           "--out", str(tmp_path)])
    out = capsys.readouterr()
    assert code != 0
    assert out.out.strip() == "", "loi thi stdout phai rong, khong nua JSON nua chu"
    assert "máy" in out.err


def test_spec_hong_thi_dung_ngay_khong_dong_vao_may(adb, tmp_path):
    hong = "Screen Name\tEvent_Name\n" + "khong co cot nao dung\n"
    with pytest.raises(cli_check.CliError):
        asyncio.run(cli_check.check(spec=parse_paste(hong), package=PACKAGE,
                                    flow=None, adb=adb, out_dir=tmp_path))
    assert adb.calls == [], "spec hong ma da dong vao may la sai thu tu"


def test_adb_chet_giua_chung_khong_lam_no_traceback(adb, tmp_path, monkeypatch):
    async def no(*a, **kw):
        raise AdbError("adb rot cap")
    monkeypatch.setattr(adb, "screen_metrics", no)
    with pytest.raises(cli_check.CliError) as err:
        _run(adb, SPEC_TSV, None, tmp_path)
    assert "adb rot cap" in str(err.value)


def test_metrics_doc_tu_may_that(adb, tmp_path):
    """Moi phep doi px<->dp dua vao day; doan bua la selector bam truot."""
    payload = _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")), tmp_path)
    assert payload["metrics"] == "1080x2280@440"


def test_params_cua_case_duoc_dua_vao_cham(adb, tmp_path):
    """`expect_params` cua case la gia tri LAN NAY phai ra - sai thi FAIL_VALUE."""
    payload = _run(adb, SPEC_TSV, _flow(
        _case("rating_placement_viewed", "tai home",
              {"placement_name": "exit_click"})), tmp_path)
    verdicts = [row["verdict"] for row in payload["results"]
                if row["element"].startswith("rating_placement_viewed")]
    assert any(v.startswith("FAIL") for v in verdicts), verdicts
    assert PARAMS  # log fixture that su co event nay


def test_co_du_4_co_dan_sang_cham_giong_duong_web(adb, tmp_path, monkeypatch):
    """Bon co nay quyet dinh nghia cua verdict: thieu mot cai la "FA khong in
    log" bi doc thanh "app khong ban event". Duong web dan du bon; duong CLI
    khong duoc dan thieu."""
    goi = {}
    that = cli_check.event_check_runner.run

    def ghi_lai(spec, windows, config, **kwargs):
        goi.update(kwargs)
        return that(spec, windows, config, **kwargs)

    monkeypatch.setattr(cli_check.event_check_runner, "run", ghi_lai)
    _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")), tmp_path)

    assert set(goi) == {"fa_silent", "stream_died", "app_seen_running",
                        "session_events"}
    assert goi["session_events"], "phai dan event CA PHIEN, khong chi trong cua so"


def test_logcat_im_thi_bao_fa_silent_chu_khong_ket_luan_app_thieu(adb, tmp_path,
                                                                  monkeypatch):
    async def khong_log(serial, tag, message):
        adb.marks.append(message)      # co moc, nhung khong dong FA nao

    monkeypatch.setattr(adb, "shell_log", khong_log)
    payload = _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")), tmp_path)
    assert payload["fa_silent"] is True
    assert payload["fail"] == 0, "FA im ma ket luan app thieu event la bao oan"


def test_chay_duoc_tren_console_cp1252(tmp_path):
    """Console Windows la cp1252. Message tieng Viet ma khong ep UTF-8 thi
    ngay `--help` cung no UnicodeEncodeError - tool chet truoc khi lam gi."""
    import os
    import subprocess
    import sys as _sys

    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    done = subprocess.run(
        [_sys.executable, "-m", "usv.cli_main", "--help"],
        # Con ep UTF-8 ra stream (xem cli_main.ep_utf8), nen cha phai doc
        # UTF-8 - de text=True thi cha doc theo PYTHONIOENCODING=cp1252 va no.
        capture_output=True, encoding="utf-8", timeout=60, env=env,
        cwd=str(Path(__file__).resolve().parent.parent))
    assert done.returncode == 0, done.stdout + done.stderr
    assert "--serial" in done.stdout

def test_report_co_anh_va_ban_app_dang_cai(adb, tmp_path):
    """Doi chat voi dev ma khong noi duoc da check ban nao thi moi ket luan
    deu tra lai duoc bang 'ban do cu roi'."""
    payload = _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")), tmp_path)
    assert payload["app_version"] == "2.4.1 (125)"
    html = Path(payload["report"]).read_text(encoding="utf-8")
    assert "2.4.1 (125)" in html
    assert "data:image/png;base64," in html

def test_case_lai_hut_van_co_anh_ngay_cho_bi_ket(adb, tmp_path):
    """Anh o dung cho lai hut la thu duy nhat noi duoc vi sao khong bam trung."""
    hong = FlowCase(event="rating_placement_viewed", name="tai home",
                    steps=(Step(kind="tap",
                                selector=Selector(resource_id="khong_co_nut_nay")),))
    payload = _run(adb, SPEC_TSV, _flow(hong), tmp_path)
    html = Path(payload["report"]).read_text(encoding="utf-8")
    assert "lúc lái hụt" in html

def test_khong_chup_duoc_thi_report_van_ra(adb, tmp_path, monkeypatch):
    async def hong(serial):
        raise AdbError("screencap chet")
    monkeypatch.setattr(adb, "screencap", hong)
    payload = _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")), tmp_path)
    assert Path(payload["report"]).exists()


def test_man_tat_thi_danh_thuc_truoc_khi_chay(adb, tmp_path):
    """Man tat thi moi cu bam roi vao khong khi, va ca luot ra 'khong thay
    element' - mot ly do sai hoan toan."""
    adb.awake = False
    _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")), tmp_path)
    assert "wake" in adb.calls


def test_case_hut_vi_man_khoa_thi_noi_thang_ly_do(adb, tmp_path, monkeypatch):
    """Khong noi thi nguoi doc di soi selector, trong khi loi nam o cho may tu
    khoa man giua chung - moi case sau deu hut theo cung mot kieu."""
    async def khong_danh_thuc(serial):
        return None      # may khoa that: wake khong lam man sang lai duoc

    monkeypatch.setattr(adb, "wake", khong_danh_thuc)
    adb.awake = False
    hong = FlowCase(event="rating_placement_viewed", name="tai home",
                    steps=(Step(kind="tap",
                                selector=Selector(resource_id="khong_co_nut_nay")),))
    payload = _run(adb, SPEC_TSV, _flow(hong), tmp_path)
    assert "khoá" in payload["cases"][0]["reason"], payload["cases"][0]
    assert payload["fail"] == 0


def test_flow_tu_mo_app_thi_KHONG_mo_them_mot_lan_truoc_moc(adb, tmp_path):
    """Moc chen sau reset, truoc step. Mo app truoc moc thi event kieu
    "1 lan/session" ban o luot mo do - ngoai cua so - va case bao "khong ban"
    trong khi log co: FAIL oan. Flow co step `launch` thi chi duoc mo MOT lan,
    va lan do phai nam sau moc."""
    case = FlowCase(event="rating_placement_viewed", name="tai home",
                    steps=(Step(kind="launch"),
                           Step(kind="tap",
                                selector=Selector(resource_id="btnHome"))))
    _run(adb, SPEC_TSV, _flow(case), tmp_path)
    assert adb.calls.count("force_stop") == 1, adb.calls
    # setprop van phai dung truoc lan mo duy nhat do.
    assert adb.calls.index("setprop") < adb.calls.index("force_stop"), adb.calls


def test_case_khong_co_step_launch_thi_van_duoc_mo_lai(adb, tmp_path):
    """Case lai tiep tren man cua case truoc (`relaunch: false`) la truong hop
    khac; con case thuong khong tu mo thi reset phai mo ho, khong thi app dang
    o man nao thi chay tu man do."""
    _run(adb, SPEC_TSV, _flow(_case("rating_placement_viewed")), tmp_path)
    assert adb.calls.count("force_stop") >= 1, adb.calls


def test_case_co_event_ngoai_spec_thi_khong_chay(adb, tmp_path):
    """File flow gom case cua nhieu SDK; mot luot chi cham mot spec.

    Chay case ngoai spec khong chi ton thoi gian: no bam nut that tren may -
    dong popup, them widget, bam check-in - nen doi luon trang thai ma spec
    dang cham can toi, va nhieu man chi hien mot lan moi ngay.
    """
    payload = _run(adb, SPEC_TSV, _flow(
        _case("rating_placement_viewed", "tai home", {"placement_name": "home"}),
        _case("widget_view", "popup Add Widget"),
        _case("daily_checkin_screen_view", "popup checkin")), tmp_path)

    da_chay = {row["case"] for row in payload["cases"]}
    assert da_chay == {"tai home"}, "chi case cua spec nay duoc chay"
    assert not any(row["element"].startswith(("widget", "daily"))
                   for row in payload["results"]), \
        "event ngoai spec khong duoc lot vao bang cham"


def test_case_chon_bang_tu_khoa_keo_theo_case_tien_de():
    """`--case` chay le mot phan flow, nhung khong duoc chay tren man sai.

    Case dat `relaunch: false` chay tiep tren man cua case ngay truoc no, nen
    chon mot minh no la lai tren man khong co that. Chon thi phai keo ca chuoi
    ve toi case tu mo app.
    """
    from dataclasses import replace as _replace

    from usv.event_flow_models import Reset

    noi_tiep = Reset(relaunch=False)
    cases = (
        _case("rating_placement_viewed", "popup o home"),
        _replace(_case("rating_star_clicked", "cham 3 sao o home"), reset=noi_tiep),
        _replace(_case("rating_placement_viewed", "popup o man result"), reset=noi_tiep),
    )

    chon = cli_check.chon_case(cases, ("result",))
    assert [c.name for c in chon] == ["popup o home", "cham 3 sao o home",
                                      "popup o man result"]

    # Case tu mo app thi khong keo theo gi ca.
    assert [c.name for c in cli_check.chon_case(cases, ("popup o home",))] == ["popup o home"]
    # Tu khoa khop nhieu case thi lay het, moi case van keo tien de cua no.
    assert len(cli_check.chon_case(cases, ("o home",))) == 2
    # Khong truyen gi thi giu nguyen ca flow.
    assert cli_check.chon_case(cases, ()) == cases
