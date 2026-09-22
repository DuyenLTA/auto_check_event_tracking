"""Phan giai selector tren cay UI roi bam / quet / go chu.

Khong dung Maestro hay uiautomator2: `ui_dump.parse_dump` da tra ve DeviceNode
co resource_id, text, content_desc va bounds_px, con `adb shell input tap` bam
duoc theo toa do pixel - hai thu do dung chung mot he toa do. Them mot thu vien
nua chi de lam viec da lam duoc.

Selector khoa bang `(resource_id, index_in_parent)`, KHONG bao gio bang
resource_id mot minh: da xac nhan tren may that mot GridView chua 4 card dung
chung resource_id `borderContainer`. Xem docstring DeviceNode.

Khong thay node thi bao KEM THEO nhung node gan giong. Bao "not found" mot minh
thi tester phai tu dump ra doc bang mat, ma dump co hang tram node.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from .adb_parsers import AdbError
from .tu_dien_man_he_thong import no_bien_the
from .models import DeviceNode

# So node gan giong in ra khi khong tim thay - du de nhan ra, khong lam nghen log.
SUGGEST = 5
MIN_RATIO = 0.5


@dataclass(frozen=True, slots=True)
class Selector:
    """Mot cach chi ra node. Dung dung MOT trong bon truong."""

    resource_id: str = ""
    text: str = ""
    desc: str = ""
    # Ten lop (vd "EditText"). Loi thoat cuoi cung cho node KHONG co id, khong
    # chu, khong content-desc - o nhap cua man Create Song la vi du: ca hai o
    # deu la EditText tron, chu goi y hien ra o node khac. Khong co `cls` thi
    # flow khong cach nao cham toi chung.
    # Vo khi app doi cay view, nen chi dung khi ba truong kia dung het cach.
    cls: str = ""
    index: int = 0        # node thu may trong so cac node khop, tinh tu 0
    # Bien the NGON NGU KHAC cua cung mot nut. Chuoi tren man he thong (picker
    # anh, sheet thanh toan, dialog quyen) doi theo ngon ngu cua MAY, khong
    # theo ngon ngu chon trong app - khoa cung mot thu tieng thi cam may khac
    # locale la ca case chet. Do duoc: may de vi-VN, o anh mang desc "Ảnh được
    # chụp lúc..." trong khi flow cho "Photo taken on".
    #
    # Khop BAT KY bien the nao. Chi khai khi chuoi that su do he thong dich;
    # chu cua chinh app thi dung `resource_id` van hon.
    alt: tuple[str, ...] = ()

    @property
    def kind(self) -> str:
        if self.resource_id:
            return "resource_id"
        if self.text:
            return "text"
        return "desc" if self.desc else "cls"

    @property
    def needle(self) -> str:
        return self.resource_id or self.text or self.desc or self.cls

    @property
    def needles(self) -> tuple[str, ...]:
        """Chuoi chinh + bien the khai tay + bien the tu tu dien he thong.

        Khop mot cai la du. Tu dien lo phan dich (`Xong` tim luon `Done`) nen
        flow khong phai khai tay tung thu tieng - xem tu_dien_man_he_thong.
        """
        if self.kind == "resource_id":
            return (self.needle, *self.alt)
        # Chu NGUOI VIET khai truoc, tu dien chi bo sung cai con thieu: bao
        # loi in ra dung chuoi trong flow thi tester do lai file nhanh hon.
        ra = list(dict.fromkeys((self.needle, *self.alt)))
        da_co = {x.casefold() for x in ra}
        for chu in tuple(ra):
            for bien_the in no_bien_the(chu):
                if bien_the.casefold() not in da_co:
                    ra.append(bien_the)
                    da_co.add(bien_the.casefold())
        return tuple(ra)

    @property
    def fragile(self) -> bool:
        """Khop theo CHU thi vo khi doi ngon ngu. resource_id thi song."""
        return self.kind in {"text", "desc"}

    def label(self) -> str:
        suffix = f"[{self.index}]" if self.index else ""
        # In ca bien the: bao loi chi ra mot chuoi trong khi flow tim ba chuoi
        # thi nguoi doc di sua dung cai khong hong.
        ten = " | ".join(repr(x) for x in self.needles)
        return f"{self.kind}={ten}{suffix}"


def _khop(gia_tri: str, needle: str) -> bool:
    """So khop chu/desc. Needle tan cung bang `*` thi khop theo DAU CHUOI.

    Can cho nhung node mang du lieu trong chinh cai ten: o anh trong Google
    photo picker co desc "Photo taken on Sep 21, 2026 11:15 AM" - doi theo ngay
    chup nen khong the go cung. Khong co dau `*` thi van khop chinh xac nhu cu:
    mot selector go thieu chu phai hong ra mat chu khong duoc am tham bat nham
    node khac.
    """
    gia_tri = gia_tri.strip().casefold()
    needle = needle.strip().casefold()
    if needle.endswith("*"):
        return gia_tri.startswith(needle[:-1])
    return gia_tri == needle


def _khop_bat_ky(gia_tri: str, needles: tuple[str, ...]) -> bool:
    return any(_khop(gia_tri, n) for n in needles)


def _candidates(nodes: list[DeviceNode], selector: Selector) -> list[DeviceNode]:
    needles = selector.needles
    if selector.kind == "resource_id":
        hits = [n for n in nodes if n.resource_id in needles]
    elif selector.kind == "text":
        hits = [n for n in nodes if _khop_bat_ky(n.text, needles)]
    elif selector.kind == "cls":
        folded = {n.casefold() for n in needles}
        hits = [n for n in nodes if n.short_cls.casefold() in folded]
    else:
        hits = [n for n in nodes if _khop_bat_ky(n.content_desc, needles)]
    # Node an / chua layout xong ra bounds 0x0 - bam vao do la bam vao khong khi.
    return [n for n in hits if not n.bounds_px.empty]


def _near_misses(nodes: list[DeviceNode], selector: Selector) -> list[str]:
    if selector.kind == "cls":
        pool = {n.short_cls for n in nodes if n.short_cls}
        return difflib.get_close_matches(selector.needle, sorted(pool),
                                         n=SUGGEST, cutoff=MIN_RATIO)
    pool = {n.resource_id for n in nodes if n.resource_id} if \
        selector.kind == "resource_id" else \
        {n.text.strip() for n in nodes if n.text.strip()} | \
        {n.content_desc.strip() for n in nodes if n.content_desc.strip()}
    return difflib.get_close_matches(selector.needle, sorted(pool),
                                     n=SUGGEST, cutoff=MIN_RATIO)


def find(nodes: list[DeviceNode], selector: Selector) -> DeviceNode:
    """Node duy nhat khop selector. Khong khop -> AdbError kem goi y."""
    hits = _candidates(nodes, selector)
    if not hits:
        near = _near_misses(nodes, selector)
        hint = ("\n  Gan giong tren man: " + ", ".join(repr(x) for x in near)) \
            if near else "\n  Khong co gi gan giong tren man hinh."
        raise AdbError(
            f"Không thấy element {selector.label()} trên màn đang hiện." + hint)
    if selector.index >= len(hits):
        raise AdbError(
            f"{selector.label()} chỉ ra node thứ {selector.index} nhưng chỉ có "
            f"{len(hits)} node khớp. Đếm từ 0.")
    return hits[selector.index]


async def tap(client, serial: str, nodes: list[DeviceNode],
              selector: Selector) -> DeviceNode:
    """Bam vao TAM cua node - goc tren-trai co the nam ngoai vung bam duoc."""
    node = find(nodes, selector)
    box = node.bounds_px
    await client.input_tap(serial, (box.left + box.right) / 2,
                           (box.top + box.bottom) / 2)
    return node


async def swipe(client, serial: str, nodes: list[DeviceNode], selector: Selector,
                direction: str, fraction: float = 0.6) -> DeviceNode:
    """Quet TRONG node - dung cho list/pager. Huong: up/down/left/right.

    Quet trong node thay vi ca man hinh: quet ca man de trung vao thanh dieu
    huong hoac notification shade.
    """
    node = find(nodes, selector)
    box = node.bounds_px
    cx, cy = (box.left + box.right) / 2, (box.top + box.bottom) / 2
    dx = box.width * fraction / 2
    dy = box.height * fraction / 2
    moves = {
        "up": (cx, cy + dy, cx, cy - dy),
        "down": (cx, cy - dy, cx, cy + dy),
        "left": (cx + dx, cy, cx - dx, cy),
        "right": (cx - dx, cy, cx + dx, cy),
    }
    if direction not in moves:
        raise AdbError(
            f"Hướng quét {direction!r} không hiểu. Chỉ nhận: "
            + ", ".join(sorted(moves)))
    await client.input_swipe(serial, *moves[direction])
    return node
