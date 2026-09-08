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
from .models import DeviceNode

# So node gan giong in ra khi khong tim thay - du de nhan ra, khong lam nghen log.
SUGGEST = 5
MIN_RATIO = 0.5


@dataclass(frozen=True, slots=True)
class Selector:
    """Mot cach chi ra node. Dung dung MOT trong ba truong."""

    resource_id: str = ""
    text: str = ""
    desc: str = ""
    index: int = 0        # node thu may trong so cac node khop, tinh tu 0

    @property
    def kind(self) -> str:
        if self.resource_id:
            return "resource_id"
        return "text" if self.text else "desc"

    @property
    def needle(self) -> str:
        return self.resource_id or self.text or self.desc

    @property
    def fragile(self) -> bool:
        """Khop theo CHU thi vo khi doi ngon ngu. resource_id thi song."""
        return self.kind in {"text", "desc"}

    def label(self) -> str:
        suffix = f"[{self.index}]" if self.index else ""
        return f"{self.kind}={self.needle!r}{suffix}"


def _candidates(nodes: list[DeviceNode], selector: Selector) -> list[DeviceNode]:
    needle = selector.needle
    if selector.kind == "resource_id":
        hits = [n for n in nodes if n.resource_id == needle]
    elif selector.kind == "text":
        folded = needle.casefold()
        hits = [n for n in nodes if n.text.strip().casefold() == folded]
    else:
        folded = needle.casefold()
        hits = [n for n in nodes if n.content_desc.strip().casefold() == folded]
    # Node an / chua layout xong ra bounds 0x0 - bam vao do la bam vao khong khi.
    return [n for n in hits if not n.bounds_px.empty]


def _near_misses(nodes: list[DeviceNode], selector: Selector) -> list[str]:
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
            f"Khong thay element {selector.label()} tren man dang hien." + hint)
    if selector.index >= len(hits):
        raise AdbError(
            f"{selector.label()} chi ra node thu {selector.index} nhung chi co "
            f"{len(hits)} node khop. Dem tu 0.")
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
            f"Huong quet {direction!r} khong hieu. Chi nhan: "
            + ", ".join(sorted(moves)))
    await client.input_swipe(serial, *moves[direction])
    return node
