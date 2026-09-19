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

HAI BAC MAU, va vi sao phai tach:

1. Mau CHAC - chi quang cao moi dat ten the nay: `dismiss-button`, `txtSkipAd`,
   "Close Billing Screen". Thay la dong, khong hoi gi them.

2. Mau MO HO - dung mot chu "Close" / "Đóng" / "Dismiss". Popup cua CHINH APP
   cung dat y het the: da do tren may that, popup Add Widget co
   `content-desc="Close"`. Dong nham no thi event vua ban ra xong bi tat man,
   buoc `wait_text` sau do nhin vao man trong va bao "Chua test" - hong ma
   trong nhu app thieu event. Nen mau mo ho CHI duoc dong khi node nam TRONG
   khung quang cao (xet to tien, khong xet ca man): mot native ad nam chung
   man voi popup la chuyen binh thuong, co mat no khong bien nut X cua app
   thanh nut X cua quang cao.
"""

from __future__ import annotations

from .models import DeviceNode

# Uu tien tu tren xuong: resource_id ben nhat, roi desc, cuoi cung moi den chu
# hien tren man (vo khi doi ngon ngu).
MAU_ID = ("dismiss-button", "interstitial_close", "ad_close", "btnskip",
          "txtskipad")
MAU_DESC = ("close billing", "close ad", "skip ad", "dismiss ad")
MAU_TEXT = ("skip ad", "bỏ qua", "close ad")

# Mau mo ho: app dung y het the cho popup cua no. Xem docstring.
MAU_MO_HO = ("close", "đóng", "dismiss", "btnclose", "ivclose", "img_close",
             "close_button")
# Khung quang cao: to tien phai la mot trong so nay thi mau mo ho moi tinh.
MAU_KHUNG_ADS = ("nativead", "adview", "ad_media", "ad_container",
                 "adcontainer", "ad_frame", "interstitial", "ad_overlay")


def _khop(gia_tri: str, mau: tuple[str, ...]) -> bool:
    thap = gia_tri.strip().casefold()
    return bool(thap) and any(m in thap for m in mau)


def _trong_khung_ads(node: DeviceNode, theo_id: dict[str, DeviceNode]) -> bool:
    """Node co to tien nao la khung quang cao khong.

    Xet to tien chu khong xet ca man: home cua app nao cung co the co mot
    native ad o duoi, ma no khong lien quan gi toi cai popup dang che giua man.
    """
    cha = theo_id.get(node.parent_id or "")
    while cha is not None:
        if _khop(cha.resource_id, MAU_KHUNG_ADS):
            return True
        cha = theo_id.get(cha.parent_id or "")
    return False


def tim_nut_dong(nodes: list[DeviceNode], *, chi_chac: bool = False,
                 man_ads: bool = False) -> DeviceNode | None:
    """Node dong quang cao dau tien tim duoc, hoac None neu man khong co.

    None KHONG phai loi: khong co quang cao chan duong la truong hop binh
    thuong nhat, va `close_ad` phai im lang di tiep luc do.

    `chi_chac=True` bo han bac mau mo ho. Dung khi dang CHO mot man cu the
    hien ra (`wait_text`): chinh man dang cho co the co nut "Close" cua no -
    popup Add Widget la vi du - va tu bam vao do la tu tay dong cai man minh
    vua doi.
    """
    dung_duoc = [n for n in nodes if n.visible and not n.bounds_px.empty]
    for mau, lay in ((MAU_ID, lambda n: n.resource_id),
                     (MAU_DESC, lambda n: n.content_desc),
                     (MAU_TEXT, lambda n: n.text)):
        for node in dung_duoc:
            if _khop(lay(node), mau):
                return node

    if chi_chac and not man_ads:
        return None

    # Dang o TRONG man quang cao thi "Close" mot chu chac chan la nut dong
    # quang cao - khong con popup nao cua app o day de bam nham. Nut dong cua
    # quang cao thuong nam trong WebView khong co resource_id nao, nen luat
    # "phai co to tien la khung ads" khong bat duoc no.
    if man_ads:
        for node in dung_duoc:
            for lay in (lambda n: n.resource_id, lambda n: n.content_desc,
                        lambda n: n.text):
                if _khop(lay(node), MAU_MO_HO):
                    return node
        return None

    # Het mau chac moi den mau mo ho, va chi trong khung quang cao.
    theo_id = {n.node_id: n for n in nodes}
    for node in dung_duoc:
        if not _trong_khung_ads(node, theo_id):
            continue
        for lay in (lambda n: n.resource_id, lambda n: n.content_desc,
                    lambda n: n.text):
            if _khop(lay(node), MAU_MO_HO):
                return node
    return None


# Nut X cua popup CUA APP - khac han nut dong quang cao o tren. O day mau mo ho
# lai la mau DUNG: popup cua app dat ten nut dong y nhu the that.
MAU_NUT_POPUP = ("close", "đóng", "dismiss", "btnclose", "ivclose", "img_close",
                 "close_button")


def tim_nut_dong_popup(nodes: list[DeviceNode],
                       neo: str = "") -> DeviceNode | None:
    """Nut dong cua popup mang chu `neo`, hoac None.

    Tach khoi `tim_nut_dong`: ben kia dong quang cao va phai DE PHONG bam nham
    popup cua app; ben nay nguoc lai - goi no la da biet ro dang dong popup nao.

    PHAI di theo cay tu chu neo len, khong duoc quet ca man: do duoc tren may
    that - paywall dat nut X la content-desc "Close Billing Screen", ma chu do
    cung chua "close". Paywall con dang chong len popup thi quet ca man se bam
    X cua paywall, popup van nguyen, roi buoc cho sau do bao "khong thay chu".
    Nut dong dung la nut nam TRONG cung khoi voi chu neo.
    """
    dung_duoc = [n for n in nodes if n.visible and not n.bounds_px.empty]

    def la_nut_dong(node: DeviceNode) -> bool:
        return any(_khop(gia_tri, MAU_NUT_POPUP) for gia_tri in
                   (node.resource_id, node.content_desc, node.text))

    if not neo:
        for node in dung_duoc:
            if la_nut_dong(node):
                return node
        return None

    thap = neo.strip().casefold()
    theo_id = {n.node_id: n for n in nodes}
    moc = [n for n in dung_duoc
           if thap in n.text.casefold() or thap in n.content_desc.casefold()]

    def to_tien(node: DeviceNode) -> list[str]:
        duong = []
        cha = theo_id.get(node.parent_id or "")
        while cha is not None:
            duong.append(cha.node_id)
            cha = theo_id.get(cha.parent_id or "")
        return duong

    # Tu khoi NHO NHAT chua chu neo noi ra: nut dong gan chu neo nhat moi la
    # nut cua chinh popup do, khong phai nut cua lop dang chong len no.
    for anchor in moc:
        for khoi in to_tien(anchor):
            trong_khoi = [n for n in dung_duoc
                          if khoi in to_tien(n) and la_nut_dong(n)]
            if trong_khoi:
                return trong_khoi[0]
    return None
