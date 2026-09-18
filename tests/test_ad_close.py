"""Tim nut dong quang cao: mot app co nhieu kieu quang cao, moi kieu mot nut."""

from __future__ import annotations

from usv.ad_close import tim_nut_dong
from usv.density import ScreenMetrics
from usv.ui_dump import parse_dump

METRICS = ScreenMetrics(width_px=1080, height_px=2400, density=440)


def _man(*nodes: str) -> list:
    than = "".join(nodes)
    xml = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
           "<hierarchy rotation=\"0\"><node index=\"0\" text=\"\" resource-id=\"\""
           " class=\"a.b.FrameLayout\" package=\"com.x\" content-desc=\"\""
           " clickable=\"false\" enabled=\"true\" visible-to-user=\"true\""
           f" bounds=\"[0,0][1080,2400]\">{than}</node></hierarchy>")
    return parse_dump(xml, METRICS)


def _node(rid="", text="", desc="", bounds="[10,20][110,120]") -> str:
    return (f"<node index=\"0\" text=\"{text}\" resource-id=\"{rid}\""
            f" class=\"a.b.View\" package=\"com.x\" content-desc=\"{desc}\""
            f" clickable=\"true\" enabled=\"true\" visible-to-user=\"true\""
            f" bounds=\"{bounds}\" />")


def test_interstitial_web_cua_admob():
    node = tim_nut_dong(_man(_node(rid="com.x:id/noise"),
                             _node(rid="dismiss-button")))
    assert node is not None and node.resource_id == "dismiss-button"


def test_splash_ad_co_nut_skip():
    node = tim_nut_dong(_man(_node(rid="com.x:id/txtSkipAd", text="Skip Ad")))
    assert node is not None and node.resource_id == "txtSkipAd"


def test_paywall_khoa_bang_content_desc():
    node = tim_nut_dong(_man(_node(desc="Close Billing Screen")))
    assert node is not None and node.content_desc == "Close Billing Screen"


def test_man_sach_thi_tra_None_chu_khong_bao_loi():
    """Khong co quang cao chan duong la truong hop binh thuong nhat."""
    assert tim_nut_dong(_man(_node(rid="com.x:id/btnHome", text="Home"))) is None


def test_khong_bam_nham_vao_node_chua_chu_x():
    """Mau 'x' mot chu khop ca checkbox/boxTitle/pixel - bam nham la hong case
    ma khong ai biet."""
    assert tim_nut_dong(_man(_node(rid="com.x:id/checkbox"),
                             _node(rid="com.x:id/boxTitle", text="Pixel"))) is None


def test_bo_qua_node_an_hoac_khong_co_kich_thuoc():
    assert tim_nut_dong(_man(_node(rid="dismiss-button",
                                   bounds="[0,0][0,0]"))) is None


def test_uu_tien_resource_id_hon_chu_tren_man():
    node = tim_nut_dong(_man(_node(text="Close"), _node(rid="ad_close")))
    assert node is not None and node.resource_id == "ad_close"


def test_close_ad_cho_quang_cao_kip_hien():
    """Splash ad mat 5-8s moi ra nut Skip. Kiem mot lan roi bo qua la luon truot."""
    import asyncio

    from usv import flow_screen
    from usv.ad_close import tim_nut_dong
    from usv.ui_cache import CayUI

    lan = {"dem": 0}

    class Adb:
        async def dump_ui(self, serial):
            lan["dem"] += 1
            co_nut = lan["dem"] >= 3
            return ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
                    "<hierarchy rotation=\"0\"><node index=\"0\" text=\"\""
                    " resource-id=\"\" class=\"a.b.F\" package=\"com.x\""
                    " content-desc=\"\" clickable=\"false\" enabled=\"true\""
                    " visible-to-user=\"true\" bounds=\"[0,0][1080,2400]\">"
                    + (_node(rid="dismiss-button") if co_nut else "")
                    + "</node></hierarchy>")

    node = asyncio.run(flow_screen.cho_nut(
        Adb(), "S1", METRICS, CayUI(), 30, tim_nut_dong))
    assert node is not None
    assert lan["dem"] == 3


# --- dialog quyen he thong ---

def test_tim_nut_cho_phep_theo_id_cua_permissioncontroller():
    from usv.quyen_he_thong import tim_nut_cho_phep

    node = tim_nut_cho_phep(_man(_node(rid="permission_message"),
                                 _node(rid="permission_allow_button",
                                       text="Cho phép")))
    assert node is not None and node.resource_id == "permission_allow_button"


def test_khong_bao_gio_bam_nut_TU_CHOI():
    """'Không cho phép' chứa cả 'cho phép' — khớp kiểu `in` là bấm nhầm nút từ
    chối, và cả flow chạy ở một trạng thái khác hẳn mà không ai biết."""
    from usv.quyen_he_thong import tim_nut_cho_phep

    node = tim_nut_cho_phep(_man(_node(rid="permission_deny_button",
                                       text="Không cho phép")))
    assert node is None


def test_khong_co_dialog_quyen_thi_tra_None():
    from usv.quyen_he_thong import tim_nut_cho_phep

    assert tim_nut_cho_phep(_man(_node(rid="com.x:id/btnHome", text="Home"))) is None


# --- mau mo ho: "Close" mot chu ---

def _man_long(khung_rid: str, con: str) -> list:
    """Man co mot khung `khung_rid` boc `con`, canh mot native ad ROI RA."""
    xml = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
           "<hierarchy rotation=\"0\"><node index=\"0\" text=\"\" resource-id=\"\""
           " class=\"a.b.FrameLayout\" package=\"com.x\" content-desc=\"\""
           " clickable=\"false\" enabled=\"true\" visible-to-user=\"true\""
           " bounds=\"[0,0][1080,2400]\">"
           f"<node index=\"0\" text=\"\" resource-id=\"{khung_rid}\""
           " class=\"a.b.FrameLayout\" package=\"com.x\" content-desc=\"\""
           " clickable=\"false\" enabled=\"true\" visible-to-user=\"true\""
           f" bounds=\"[0,600][1080,1400]\">{con}</node>"
           "<node index=\"1\" text=\"\" resource-id=\"com.x:id/nativeAdView\""
           " class=\"a.b.FrameLayout\" package=\"com.x\" content-desc=\"\""
           " clickable=\"false\" enabled=\"true\" visible-to-user=\"true\""
           " bounds=\"[0,1440][1080,2400]\">"
           "<node index=\"0\" text=\"Ad\" resource-id=\"com.x:id/txtAds\""
           " class=\"a.b.TextView\" package=\"com.x\" content-desc=\"\""
           " clickable=\"false\" enabled=\"true\" visible-to-user=\"true\""
           " bounds=\"[39,1487][102,1539]\" /></node>"
           "</node></hierarchy>")
    return parse_dump(xml, METRICS)


def test_khong_dong_popup_CUA_APP_du_no_ghi_Close():
    """Popup Add Widget co content-desc='Close' y het nut dong quang cao. Dong
    nham no thi event vua ban xong bi tat man, buoc cho sau do bao 'Chua test'
    - hong ma trong nhu app thieu event. Native ad o duoi man khong lien quan."""
    nodes = _man_long("com.x:id/widgetPopupContainer",
                      _node(desc="Close") + _node(text="Add Widget"))
    assert tim_nut_dong(nodes) is None


def test_nut_Close_NAM_TRONG_khung_quang_cao_thi_dong():
    nodes = _man_long("com.x:id/nativeAdView2", _node(desc="Close"))
    node = tim_nut_dong(nodes)
    assert node is not None and node.content_desc == "Close"


def test_paywall_van_dong_duoc_du_khong_co_khung_ads():
    """'Close Billing Screen' la mau CHAC - paywall khong boc trong khung ads
    nao, chan no lai thi flow khong bao gio vao duoc man home."""
    node = tim_nut_dong(_man(_node(desc="Close Billing Screen")))
    assert node is not None


def test_chi_chac_bo_han_bac_mau_mo_ho():
    """`wait_text` dang cho popup Add Widget hien ra, ma chinh popup do co nut
    'Close'. Neu vong cho tu bam nut mo ho thi no dong mat cai man vua doi."""
    nodes = _man_long("com.x:id/nativeAdView2", _node(desc="Close"))
    assert tim_nut_dong(nodes) is not None            # binh thuong: dong duoc
    assert tim_nut_dong(nodes, chi_chac=True) is None  # dang cho: khong dong


def test_chi_chac_van_dong_paywall_va_splash_ad():
    """Hai thu nay chan duong that, va ten cua chung khong nhap nhang."""
    paywall = tim_nut_dong(_man(_node(desc="Close Billing Screen")), chi_chac=True)
    splash = tim_nut_dong(_man(_node(rid="com.x:id/txtSkipAd", text="Skip Ad")),
                          chi_chac=True)
    assert paywall is not None and splash is not None


# --- close_popup: nut dong phai thuoc CHINH popup do ---

def _man_hai_lop() -> list:
    """Paywall dang chong len popup Add Widget - dung canh do duoc luc 14:35."""
    xml = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
           "<hierarchy rotation=\"0\"><node index=\"0\" text=\"\" resource-id=\"\""
           " class=\"a.b.F\" package=\"com.x\" content-desc=\"\" clickable=\"false\""
           " enabled=\"true\" visible-to-user=\"true\" bounds=\"[0,0][1080,2400]\">"
           # popup cua app, nam duoi
           "<node index=\"0\" text=\"\" resource-id=\"com.x:id/widgetPopup\""
           " class=\"a.b.F\" package=\"com.x\" content-desc=\"\" clickable=\"false\""
           " enabled=\"true\" visible-to-user=\"true\" bounds=\"[60,600][1020,1500]\">"
           "<node index=\"0\" text=\"Add Widget\" resource-id=\"\" class=\"a.b.T\""
           " package=\"com.x\" content-desc=\"\" clickable=\"false\" enabled=\"true\""
           " visible-to-user=\"true\" bounds=\"[100,650][900,720]\" />"
           "<node index=\"1\" text=\"\" resource-id=\"\" class=\"a.b.V\""
           " package=\"com.x\" content-desc=\"Close\" clickable=\"true\""
           " enabled=\"true\" visible-to-user=\"true\" bounds=\"[930,640][990,700]\" />"
           "</node>"
           # paywall chong len tren, nut X cua no cung chua chu "close"
           "<node index=\"1\" text=\"\" resource-id=\"com.x:id/billing\""
           " class=\"a.b.F\" package=\"com.x\" content-desc=\"\" clickable=\"false\""
           " enabled=\"true\" visible-to-user=\"true\" bounds=\"[0,0][1080,2400]\">"
           "<node index=\"0\" text=\"\" resource-id=\"\" class=\"a.b.Image\""
           " package=\"com.x\" content-desc=\"Close Billing Screen\""
           " clickable=\"true\" enabled=\"true\" visible-to-user=\"true\""
           " bounds=\"[34,64][166,196]\" /></node>"
           "</node></hierarchy>")
    return parse_dump(xml, METRICS)


def test_dong_popup_khong_bam_nham_X_cua_lop_dang_chong_len():
    """Do duoc tren may that: paywall dat nut X la 'Close Billing Screen' - chu
    do cung chua 'close'. Quet ca man thi bam X cua paywall, popup van nguyen,
    roi buoc cho sau do bao 'khong thay chu' - mat mot luot cham."""
    from usv.ad_close import tim_nut_dong_popup

    nut = tim_nut_dong_popup(_man_hai_lop(), "Add Widget")
    assert nut is not None
    assert nut.content_desc == "Close"       # X cua popup, khong phai cua paywall


def test_dong_popup_khong_thay_chu_neo_thi_tra_None():
    from usv.ad_close import tim_nut_dong_popup

    assert tim_nut_dong_popup(_man_hai_lop(), "Check-In") is None
