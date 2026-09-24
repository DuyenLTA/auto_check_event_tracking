"""Chay flow. Khong can may - client va logcat duoc thay ban gia.

Hai bat buoc:
  - STEP THAT BAI -> not_tested, KHONG phai fail. Khong lai toi duoc man can
    test thi tool chua do gi ca.
  - RESET khong an -> blocked, cung khong phai fail.
"""

from __future__ import annotations

import asyncio

import pytest

from usv import event_flow_run, remote_config
from usv.adb_parsers import AdbError
from usv.density import ScreenMetrics
from usv.device_actions import Selector
from usv.event_flow_models import Flow, FlowCase, Reset, Step
from usv.event_flow_run import expectations, run_case, run_flow
from usv.event_window import cut_log, mark_label, with_expectations
from usv.logcat_stream import Recording

METRICS = ScreenMetrics(width_px=1080, height_px=2280, density=440)

DUMP = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0"><node index="0" text="" resource-id="" class="a.b.FrameLayout"
 package="com.x" content-desc="" clickable="false" enabled="true" visible-to-user="true"
 bounds="[0,0][1080,2280]"><node index="0" text="Home" resource-id="com.x:id/btnHome"
 class="a.b.TextView" package="com.x" content-desc="" clickable="true" enabled="true"
 visible-to-user="true" bounds="[100,200][300,400]" /></node></hierarchy>"""


class FakeClient:
    def __init__(self) -> None:
        self.log: list[str] = []
        self.marks: list[str] = []
        self.taps = 0
        self.debuggable = True

    async def dump_ui(self, serial):
        return DUMP

    async def force_stop(self, serial, package):
        self.log.append("force_stop")

    async def launch(self, serial, package):
        self.log.append("launch")

    async def input_tap(self, serial, x, y):
        self.taps += 1

    async def input_keyevent(self, serial, name):
        self.log.append(f"key:{name}")

    async def input_text(self, serial, text):
        self.log.append(f"type:{text}")

    async def shell_log(self, serial, tag, message):
        self.marks.append(message)

    async def is_debuggable(self, serial, package):
        return self.debuggable


@pytest.fixture(autouse=True)
def _no_wait(monkeypatch):
    async def instant(_s):
        return None
    monkeypatch.setattr(event_flow_run.asyncio, "sleep", instant)


@pytest.fixture
def recording():
    return Recording(serial="S1", package="com.x", stopped=False)


def _case(**kw):
    base = dict(event="rating_placement_viewed", name="rating tai home",
                expect_params={"placement_name": "home"},
                steps=(Step(kind="tap", selector=Selector(resource_id="btnHome")),))
    base.update(kw)
    return FlowCase(**base)


def run(coro):
    return asyncio.run(coro)


def test_case_chay_duoc_thi_chen_moc_va_chay_het_step(recording):
    client = FakeClient()
    result = run(run_case(client, "S1", METRICS, "com.x", recording, _case()))
    assert result.status == "ok"
    assert result.steps_done == 1
    assert client.taps == 1
    assert client.marks == [mark_label("rating_placement_viewed", "rating tai home")]


def test_moc_mang_NHAN_CASE_de_phan_biet_nhieu_case_cung_event(recording):
    """placement_name co 4 gia tri -> 4 case cung mot event."""
    client = FakeClient()
    for place in ("home", "result"):
        run(run_case(client, "S1", METRICS, "com.x", recording,
                     _case(name=f"rating tai {place}",
                           expect_params={"placement_name": place})))
    assert client.marks == [
        mark_label("rating_placement_viewed", "rating tai home"),
        mark_label("rating_placement_viewed", "rating tai result"),
    ]


def test_step_that_bai_ra_NOT_TESTED_khong_phai_fail(recording):
    client = FakeClient()
    case = _case(steps=(Step(kind="tap", selector=Selector(resource_id="khong_co")),))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "not_tested"
    assert "that bai" in result.reason or "thất bại" in result.reason
    assert client.taps == 0


def test_step_that_bai_giua_duong_ghi_lai_da_chay_bao_nhieu(recording):
    client = FakeClient()
    case = _case(steps=(
        Step(kind="tap", selector=Selector(resource_id="btnHome")),
        Step(kind="tap", selector=Selector(resource_id="khong_co")),
    ))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.steps_done == 1
    assert result.status == "not_tested"


def test_step_la_bao_loi(recording):
    client = FakeClient()
    result = run(run_case(client, "S1", METRICS, "com.x", recording,
                          _case(steps=(Step(kind="nhay_lung_tung"),))))
    assert result.status == "not_tested"


def test_reset_bi_chan_ra_BLOCKED_khong_phai_fail(recording, monkeypatch):
    client = FakeClient()
    client.debuggable = False
    case = _case(reset=Reset(remote_config={"enable_rate": "true"}))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "blocked"
    assert "debuggable" in result.reason


def test_reset_khong_giu_duoc_gia_tri_ra_BLOCKED(recording, monkeypatch):
    """Build dev dat minimumFetchInterval = 0 -> throttle vo hieu."""
    client = FakeClient()

    async def fake_override(*_a, **_k):
        return remote_config.OverrideResult(applied={"enable_rate": "true"})

    async def fake_verify(*_a, **_k):
        return {"enable_rate": "false"}      # app fetch that, de mat patch

    monkeypatch.setattr(remote_config, "override", fake_override)
    monkeypatch.setattr(remote_config, "verify", fake_verify)
    case = _case(reset=Reset(remote_config={"enable_rate": "true"}))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "blocked"
    assert "minimumFetchInterval" in result.reason


def test_reset_mo_lai_app_truoc_khi_chen_moc(recording, monkeypatch):
    """App doc gia tri moi luc process start, nen phai mo lai TRUOC khi do."""
    client = FakeClient()

    async def fake_override(*_a, **_k):
        return remote_config.OverrideResult(applied={"k": "v"})

    async def fake_verify(*_a, **_k):
        return {"k": "v"}

    monkeypatch.setattr(remote_config, "override", fake_override)
    monkeypatch.setattr(remote_config, "verify", fake_verify)
    run(run_case(client, "S1", METRICS, "com.x", recording,
                 _case(reset=Reset(remote_config={"k": "v"}))))
    assert client.log[:2] == ["force_stop", "launch"]


def test_mot_case_blocked_khong_dung_ca_luot(recording, monkeypatch):
    client = FakeClient()
    ok_case = _case(name="case chay duoc")
    bad_case = _case(name="case bi chan", steps=(
        Step(kind="tap", selector=Selector(resource_id="khong_co")),))
    results = run(run_flow(client, "S1", METRICS, "com.x", recording,
                           Flow(package="com.x", cases=(bad_case, ok_case))))
    assert [r.status for r in results] == ["not_tested", "ok"]


def test_expectations_chi_lay_case_da_chay(recording):
    client = FakeClient()
    ok_case = _case(name="chay duoc", expect_params={"placement_name": "home"})
    bad_case = _case(name="khong chay", expect_params={"placement_name": "result"},
                     steps=(Step(kind="tap", selector=Selector(resource_id="x")),))
    results = run(run_flow(client, "S1", METRICS, "com.x", recording,
                           Flow(cases=(ok_case, bad_case))))
    assert expectations(results) == {"chay duoc": {"placement_name": "home"}}


def test_gan_gia_tri_doi_hoi_vao_cua_so_theo_NHAN_khong_theo_thu_tu():
    """Case that bai khong chen moc -> zip theo thu tu se gan lech."""
    log = "\n".join([
        "09-08 15:00:01.000 I/USV_MARK( 9): "
        + mark_label("rating_placement_viewed", "case B"),
        "09-08 15:00:02.000 V/FA-SVC ( 9): Logging event: origin=app,"
        "name=rating_placement_viewed,params=Bundle[{placement_name=result}]",
    ])
    windows = with_expectations(cut_log(log), {
        "case A": {"placement_name": "home"},
        "case B": {"placement_name": "result"},
    })
    assert windows[0].expect_params == {"placement_name": "result"}


def test_cua_so_khong_co_nhan_khop_thi_de_rong():
    log = ("09-08 15:00:01.000 I/USV_MARK( 9): "
           + mark_label("ev_a", "nhan khong khop"))
    windows = with_expectations(cut_log(log), {"nhan khac": {"a": "1"}})
    assert windows[0].expect_params == {}


def test_step_tuy_chon_hut_thi_case_van_chay_tiep(recording):
    """Quang cao xen ke khong hien -> bo qua buoc dong no, KHONG phai lai hut."""
    client = FakeClient()
    case = _case(steps=(
        Step(kind="tap", selector=Selector(resource_id="khong_co"), optional=True),
        Step(kind="tap", selector=Selector(resource_id="btnHome")),
    ))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "ok"
    assert result.steps_done == 1
    assert any("bỏ qua bước tuỳ chọn" in n for n in result.notes), result.notes


def test_cay_ui_dung_lai_giua_hai_buoc_chi_doc(recording, monkeypatch):
    """`uiautomator dump` mat 2.2s tren may that. Hai buoc lien tiep cung nhin
    mot man khong doi thi doc lai la tra tien hai lan cho cung mot thu."""
    client = FakeClient()
    dem = {"dump": 0}
    that = client.dump_ui

    async def dem_dump(serial):
        dem["dump"] += 1
        return await that(serial)

    client.dump_ui = dem_dump
    case = _case(steps=(
        Step(kind="tap", selector=Selector(resource_id="khong_co"), optional=True),
        Step(kind="tap", selector=Selector(resource_id="cung_khong_co"),
             optional=True),
        Step(kind="tap", selector=Selector(resource_id="btnHome")),
    ))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "ok"
    # Ba buoc nhung chi MOT lan dump: hai buoc dau khong bam duoc gi nen man
    # khong doi, buoc ba dung lai chinh cay do.
    assert dem["dump"] == 1, dem


def test_bam_xong_thi_cay_cu_bi_bo(recording):
    """Da bam thi man doi. Dung lai cay cu la bam vao toa do cua qua khu."""
    from usv.ui_cache import CayUI

    cay = CayUI()
    cay.giu(["node gia"])
    assert cay.con_dung_duoc()
    cay.bo()
    assert not cay.con_dung_duoc()


def test_wait_text_dem_bang_dong_ho_that_khong_tru_dan_theo_POLL(recording, monkeypatch):
    """Mot vong cho ton (dump 2.2s + POLL) nhung code cu chi tru POLL, nen
    `timeout: 25` chay ~390 giay that. Da lam mot luot cham ton 611s."""
    from usv import flow_screen

    dong_ho = {"t": 0.0}
    monkeypatch.setattr(flow_screen.time, "monotonic", lambda: dong_ho["t"])

    client = FakeClient()

    async def dump_cham(serial):
        dong_ho["t"] += 2.2          # dump that mat 2.2s tren may
        return DUMP

    client.dump_ui = dump_cham
    thay = run(flow_screen.wait_text(client, "S1", METRICS,
                                         "chu-khong-bao-gio-co", 10))
    assert thay is False
    # Cho 10s thi duoc phep tieu toi da 10s + mot lan dump dang do.
    assert dong_ho["t"] <= 10 + 2.2 * 2, dong_ho


def test_close_ad_bam_dung_nut_dong_va_cho_man_lang(recording, monkeypatch):
    client = FakeClient()
    case = _case(steps=(Step(kind="close_ad"),))
    monkeypatch.setattr("usv.flow_screen.tim_nut_dong",
                        lambda nodes, **_: nodes[-1])
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "ok"
    assert client.taps == 1


def test_close_ad_man_sach_thi_di_tiep_khong_bao_loi(recording):
    """Khong co quang cao chan duong la truong hop binh thuong nhat - bao loi
    o day la moi flow deu vo khi quang cao khong hien."""
    client = FakeClient()
    case = _case(steps=(Step(kind="close_ad"),
                        Step(kind="tap", selector=Selector(resource_id="btnHome"))))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "ok"
    assert result.steps_done == 2


def test_cho_man_dung_lai_TRUOC_khi_chup_tam_sau_buoc_cuoi(recording, monkeypatch):
    """Bam xong thi bottom sheet / dialog cua he thong con dang bay ra: chup
    ngay la duoc mot tam nua trong nua man - do duoc tren may that voi nut
    "Add Widget Now". Tam nay la bang chung ngu canh nen cham mot nhip khong
    lam sai ket qua nao."""
    client = FakeClient()
    thu_tu: list[str] = []

    async def sleep_ghi(giay):
        thu_tu.append(f"sleep {giay}")

    monkeypatch.setattr(event_flow_run.asyncio, "sleep", sleep_ghi)

    async def chup(moment: str) -> None:
        thu_tu.append(f"chụp {moment}")

    run(run_case(client, "S1", METRICS, "com.x", recording, _case(), on_shot=chup))
    assert thu_tu[-2:] == [f"sleep {event_flow_run.SHOT_SETTLE}",
                           "chụp sau bước cuối"], thu_tu


def test_wait_text_tu_don_man_chan_roi_cho_tiep(recording, monkeypatch):
    """Paywall len SAU khi cac buoc close_ad het han cho. Vong cho ngoi nhin no
    het gio thi case bao Chua test trong khi app chang sai gi - do duoc tren
    may that voi paywall cua app texttoimage."""
    from usv import flow_screen

    PAYWALL = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
               "<hierarchy rotation=\"0\"><node index=\"0\" text=\"\""
               " resource-id=\"\" class=\"a.b.F\" package=\"com.x\""
               " content-desc=\"\" clickable=\"false\" enabled=\"true\""
               " visible-to-user=\"true\" bounds=\"[0,0][1080,2280]\">"
               "<node index=\"0\" text=\"\" resource-id=\"\" class=\"a.b.Image\""
               " package=\"com.x\" content-desc=\"Close Billing Screen\""
               " clickable=\"true\" enabled=\"true\" visible-to-user=\"true\""
               " bounds=\"[34,64][166,196]\" /></node></hierarchy>")

    class Adb:
        def __init__(self) -> None:
            self.taps: list[tuple[float, float]] = []
            self.lan = 0

        async def dump_ui(self, serial):
            self.lan += 1
            # Hai vong dau la paywall; bam dong roi moi ra man co chu.
            return PAYWALL if not self.taps else DUMP

        async def input_tap(self, serial, x, y):
            self.taps.append((x, y))

    async def instant(_s):
        return None

    monkeypatch.setattr(flow_screen.asyncio, "sleep", instant)
    adb = Adb()
    thay = run(flow_screen.wait_text(adb, "S1", METRICS, "Home", 5))
    assert thay is True
    # Bam vao TAM nut dong, khong phai goc tren-trai.
    assert adb.taps == [(100.0, 130.0)], adb.taps


def test_wait_text_KHONG_dong_nut_mo_ho_cua_man_dang_cho(recording, monkeypatch):
    """Popup Add Widget co desc='Close' cua chinh no. Tu bam vao do la tu tay
    dong mat cai man vua doi duoc, roi bao khong thay."""
    from usv import flow_screen

    POPUP = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
             "<hierarchy rotation=\"0\"><node index=\"0\" text=\"\""
             " resource-id=\"com.x:id/nativeAdView\" class=\"a.b.F\""
             " package=\"com.x\" content-desc=\"\" clickable=\"false\""
             " enabled=\"true\" visible-to-user=\"true\""
             " bounds=\"[0,0][1080,2280]\">"
             "<node index=\"0\" text=\"\" resource-id=\"\" class=\"a.b.V\""
             " package=\"com.x\" content-desc=\"Close\" clickable=\"true\""
             " enabled=\"true\" visible-to-user=\"true\""
             " bounds=\"[900,200][960,260]\" />"
             "<node index=\"1\" text=\"Add Widget\" resource-id=\"\""
             " class=\"a.b.T\" package=\"com.x\" content-desc=\"\""
             " clickable=\"false\" enabled=\"true\" visible-to-user=\"true\""
             " bounds=\"[100,300][900,400]\" /></node></hierarchy>")

    class Adb:
        def __init__(self) -> None:
            self.taps = []

        async def dump_ui(self, serial):
            return POPUP

        async def input_tap(self, serial, x, y):
            self.taps.append((x, y))

    async def instant(_s):
        return None

    monkeypatch.setattr(flow_screen.asyncio, "sleep", instant)
    adb = Adb()
    assert run(flow_screen.wait_text(adb, "S1", METRICS, "Add Widget", 5)) is True
    assert adb.taps == []


def test_wait_text_khong_don_man_chan_qua_nhieu_lan(recording, monkeypatch):
    """Chuoi quang cao vo tan thi vong cho phai chiu het gio, khong song mai."""
    from usv import flow_screen

    PAYWALL = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
               "<hierarchy rotation=\"0\"><node index=\"0\" text=\"\""
               " resource-id=\"\" class=\"a.b.F\" package=\"com.x\""
               " content-desc=\"\" clickable=\"false\" enabled=\"true\""
               " visible-to-user=\"true\" bounds=\"[0,0][1080,2280]\">"
               "<node index=\"0\" text=\"\" resource-id=\"\" class=\"a.b.Image\""
               " package=\"com.x\" content-desc=\"Close Billing Screen\""
               " clickable=\"true\" enabled=\"true\" visible-to-user=\"true\""
               " bounds=\"[34,64][166,196]\" /></node></hierarchy>")

    class Adb:
        def __init__(self) -> None:
            self.taps = []

        async def dump_ui(self, serial):
            return PAYWALL      # dong bao nhieu lan cung ra cai khac y het

        async def input_tap(self, serial, x, y):
            self.taps.append((x, y))

    async def instant(_s):
        return None

    monkeypatch.setattr(flow_screen.asyncio, "sleep", instant)
    adb = Adb()
    assert run(flow_screen.wait_text(adb, "S1", METRICS, "Home", 0)) is False
    assert len(adb.taps) == flow_screen.MAN_CHAN_TOI_DA, adb.taps


def test_buoc_intent_goi_am_start(recording):
    """Buoc `intent` phai goi start_intent voi dung action va component."""
    from usv.event_flow_models import Step

    class Adb(FakeClient):
        def __init__(self):
            super().__init__()
            self.intents = []

        async def start_intent(self, serial, action, component=""):
            self.intents.append((action, component))

    client = Adb()
    case = _case(steps=(Step(kind="intent",
                             text="com.apero.rating.action.RATING",
                             component="com.x/com.apero.RatingActivity"),))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "ok"
    assert client.intents == [("com.apero.rating.action.RATING",
                               "com.x/com.apero.RatingActivity")]


def test_close_popup_don_lop_che_roi_bam_lai(recording):
    """Nut X cua popup co that va tim dung, nhung paywall dang phu len tren nen
    cu tap dau roi vao lop tren - do duoc tren may that, anh luc lai hut cho
    thay popup van nguyen sau khi 'da bam'."""
    from usv.event_flow_models import Step

    POPUP_VA_PAYWALL = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
        "<hierarchy rotation=\"0\"><node index=\"0\" text=\"\" resource-id=\"\""
        " class=\"a.b.F\" package=\"com.x\" content-desc=\"\" clickable=\"false\""
        " enabled=\"true\" visible-to-user=\"true\" bounds=\"[0,0][1080,2400]\">"
        "<node index=\"0\" text=\"\" resource-id=\"com.x:id/popup\" class=\"a.b.F\""
        " package=\"com.x\" content-desc=\"\" clickable=\"false\" enabled=\"true\""
        " visible-to-user=\"true\" bounds=\"[60,600][1020,1500]\">"
        "<node index=\"0\" text=\"Add Widget\" resource-id=\"\" class=\"a.b.T\""
        " package=\"com.x\" content-desc=\"\" clickable=\"false\" enabled=\"true\""
        " visible-to-user=\"true\" bounds=\"[100,650][900,720]\" />"
        "<node index=\"1\" text=\"\" resource-id=\"\" class=\"a.b.V\" package=\"com.x\""
        " content-desc=\"Close\" clickable=\"true\" enabled=\"true\""
        " visible-to-user=\"true\" bounds=\"[930,640][990,700]\" /></node>"
        "<node index=\"1\" text=\"\" resource-id=\"com.x:id/billing\" class=\"a.b.F\""
        " package=\"com.x\" content-desc=\"\" clickable=\"false\" enabled=\"true\""
        " visible-to-user=\"true\" bounds=\"[0,0][1080,2400]\">"
        "<node index=\"0\" text=\"\" resource-id=\"\" class=\"a.b.Image\""
        " package=\"com.x\" content-desc=\"Close Billing Screen\" clickable=\"true\""
        " enabled=\"true\" visible-to-user=\"true\" bounds=\"[34,64][166,196]\" />"
        "</node></node></hierarchy>")
    CHI_POPUP = POPUP_VA_PAYWALL.replace(
        "<node index=\"1\" text=\"\" resource-id=\"com.x:id/billing\" class=\"a.b.F\""
        " package=\"com.x\" content-desc=\"\" clickable=\"false\" enabled=\"true\""
        " visible-to-user=\"true\" bounds=\"[0,0][1080,2400]\">"
        "<node index=\"0\" text=\"\" resource-id=\"\" class=\"a.b.Image\""
        " package=\"com.x\" content-desc=\"Close Billing Screen\" clickable=\"true\""
        " enabled=\"true\" visible-to-user=\"true\" bounds=\"[34,64][166,196]\" />"
        "</node>", "")
    SACH = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
            "<hierarchy rotation=\"0\"><node index=\"0\" text=\"Home\""
            " resource-id=\"com.x:id/btnHome\" class=\"a.b.T\" package=\"com.x\""
            " content-desc=\"\" clickable=\"true\" enabled=\"true\""
            " visible-to-user=\"true\" bounds=\"[100,200][300,400]\" /></hierarchy>")

    class Adb(FakeClient):
        def __init__(self):
            super().__init__()
            self.taps_at = []
            self.man = [POPUP_VA_PAYWALL, POPUP_VA_PAYWALL, CHI_POPUP, SACH, SACH]

        async def dump_ui(self, serial):
            return self.man[min(len(self.taps_at), len(self.man) - 1)]

        async def input_tap(self, serial, x, y):
            self.taps_at.append((x, y))

    client = Adb()
    case = _case(steps=(Step(kind="close_popup", text="Add Widget", timeout=5),))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "ok", result.reason
    # Bam X popup (khong an vi paywall che) -> don paywall -> bam lai X popup.
    assert client.taps_at == [(960.0, 670.0), (100.0, 130.0), (960.0, 670.0)], \
        client.taps_at


def test_tap_don_quang_cao_chan_duong_roi_bam_lai(recording):
    """Quang cao chen len giua hai buoc bat ky. Bao hut ngay la mat ca case,
    trong khi man dang can van nam ngay duoi lop quang cao do."""
    from usv.event_flow_models import Step

    ADS = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
           "<hierarchy rotation=\"0\"><node index=\"0\" text=\"\""
           " resource-id=\"dismiss-button\" class=\"a.b.V\" package=\"com.x\""
           " content-desc=\"\" clickable=\"true\" enabled=\"true\""
           " visible-to-user=\"true\" bounds=\"[900,100][980,180]\" /></hierarchy>")

    class Adb(FakeClient):
        def __init__(self):
            super().__init__()
            self.taps_at = []

        async def dump_ui(self, serial):
            return ADS if not self.taps_at else DUMP

        async def top_activity(self, serial):
            return "com.x/com.google.android.gms.ads.AdActivity"

        async def input_tap(self, serial, x, y):
            self.taps_at.append((x, y))

    client = Adb()
    case = _case(steps=(Step(kind="tap", selector=Selector(resource_id="btnHome")),))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "ok", result.reason
    # Bam nut dong quang cao truoc, roi moi bam dung nut can bam.
    assert client.taps_at == [(940.0, 140.0), (200.0, 300.0)], client.taps_at


def test_tap_van_bao_hut_khi_khong_co_quang_cao_nao(recording):
    """Don quang cao khong duoc bien mot buoc hut thanh im lang: khong co gi de
    don thi van phai bao `not_tested` kem ten step chet."""
    from usv.event_flow_models import Step

    client = FakeClient()
    case = _case(steps=(Step(kind="tap", selector=Selector(resource_id="khong_co")),))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "not_tested"
    assert "khong_co" in result.reason


class _PaywallAdb(FakeClient):
    """Paywall voi nut X bam SOM thi khong an: `bam_an_tu` = cu bam thu may
    moi thoat duoc. None = bam bao nhieu cung khong thoat."""

    def __init__(self, bam_an_tu):
        super().__init__()
        self.bam_an_tu = bam_an_tu
        from pathlib import Path
        self.paywall = (Path(__file__).parent / "fixtures" /
                        "paywall-dump.xml").read_text().replace(
            "Close Billing Screen", "請求画面を閉じる")

    def _con_paywall(self):
        return self.bam_an_tu is None or self.taps < self.bam_an_tu

    async def top_activity(self, serial):
        if self._con_paywall():
            return "com.x/com.visionlab.billing.ui.VslBillingActivity"
        return "com.x/.ui.MainActivity"

    async def dump_ui(self, serial):
        return self.paywall if self._con_paywall() else DUMP


def _nhanh(monkeypatch, cho_x=0.3):
    from usv import flow_screen
    monkeypatch.setattr(flow_screen, "POLL", 0.0)
    monkeypatch.setattr(flow_screen, "DONG_SETTLE", 0.0)
    monkeypatch.setattr(flow_screen, "PAYWALL_CHO_X", cho_x)


def test_close_ad_paywall_x_hien_tre_thi_bam_lai_toi_khi_thoat(recording,
                                                              monkeypatch):
    """X hien tre vai giay: cu bam dau khong an, phai kiem da thoat paywall
    chua roi bam lai - du `close_ad` khai timeout 0."""
    _nhanh(monkeypatch, cho_x=5)
    client = _PaywallAdb(bam_an_tu=3)
    case = _case(steps=(Step(kind="close_ad", timeout=0),))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "ok", result.reason
    assert client.taps == 3


def test_close_ad_ket_paywall_thi_bao_ro_tai_cho(recording, monkeypatch):
    _nhanh(monkeypatch)
    client = _PaywallAdb(bam_an_tu=None)
    case = _case(steps=(Step(kind="close_ad", timeout=0),))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "not_tested"
    assert "Kẹt ở paywall" in result.reason


def test_wait_text_don_paywall_tieng_la_roi_thay_chu(monkeypatch):
    from usv import flow_screen
    _nhanh(monkeypatch, cho_x=5)
    client = _PaywallAdb(bam_an_tu=2)
    thay = run(flow_screen.wait_text(client, "S1", METRICS, "Home", 0.2))
    assert thay is True
    assert client.taps == 2
