"""Tim nut dong quang cao tren man dang hien.

Vi sao khong ghi cung mot `resource_id` trong flow: mot app co it nhat bon kieu
quang cao chan duong, moi kieu mot nut khac nhau - da gap tren cung mot app:

    splash ad        text="Skip Ad"                (resource_id=txtSkipAd)
    interstitial web resource_id="dismiss-button"  (do AdMob dung, khong phai app)
    paywall          content-desc="Close Billing Screen"
    native ad        khong co nut dong - khong chan duong, bo qua

Ghi cung mot cai thi flow vo ngay khi gap kieu khac, va tester phai ngoi dump UI
de doi mot dong YAML. Nen `close_ad` doi chieu theo DANH SACH mau, uu tien cai
chac chan nhat truoc.

KHONG nhan mau "x" mot chu: no khop ca `boxTitle`, `checkbox`, `pixel`... va bam
nham vao mot cai gi do trong app la hong ca case ma khong ai biet.
"""

from __future__ import annotations

from .models import DeviceNode

# Uu tien tu tren xuong: resource_id ben nhat, roi desc, cuoi cung moi den chu
# hien tren man (vo khi doi ngon ngu).
MAU_ID = ("dismiss-button", "interstitial_close", "ad_close", "btnclose",
          "ivclose", "img_close", "close_button", "btnskip", "txtskipad")
MAU_DESC = ("close", "dismiss", "skip ad", "đóng")
MAU_TEXT = ("skip ad", "close", "đóng", "bỏ qua")


def _khop(gia_tri: str, mau: tuple[str, ...]) -> bool:
    thap = gia_tri.strip().casefold()
    return bool(thap) and any(m in thap for m in mau)


def tim_nut_dong(nodes: list[DeviceNode]) -> DeviceNode | None:
    """Node dong quang cao dau tien tim duoc, hoac None neu man khong co.

    None KHONG phai loi: khong co quang cao chan duong la truong hop binh
    thuong nhat, va `close_ad` phai im lang di tiep luc do.
    """
    dung_duoc = [n for n in nodes if n.visible and not n.bounds_px.empty]
    for mau, lay in ((MAU_ID, lambda n: n.resource_id),
                     (MAU_DESC, lambda n: n.content_desc),
                     (MAU_TEXT, lambda n: n.text)):
        for node in dung_duoc:
            if _khop(lay(node), mau):
                return node
    return None
