"""Kieu du lieu cho phia THIET BI. Khong I/O -> test khong can device.

`DeviceNode` la mot node trong cay `uiautomator dump`, `Bounds` la hinh chu nhat
dung cho ca px va dp.

Tool nay khong con phia DESIGN: doi chieu UI voi Figma/pen.dev la mot tool khac
(repo ui-spec-verifier). O day chi dung cay UI de PHAN GIAI SELECTOR - tim node
theo resource-id/text roi bam vao tam bounds cua no.
"""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Bounds:
    """Hinh chu nhat. Dung cho ca px va dp - don vi do nguoi goi tu biet."""

    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def empty(self) -> bool:
        """Node an / chua layout xong thi ra bounds 0x0."""
        return self.width <= 0 or self.height <= 0

    def scaled(self, factor: float) -> Bounds:
        """Doi don vi (px -> dp la factor = 1/scale). KHONG lam tron.

        Tuyet doi khong lam tron o day. Neu lam tron tung canh roi moi tru ra
        width thi cung mot element se cho size khac nhau tuy no nam o dau tren
        man hinh (vd 447px/2.75: canh 20.7..183.3 -> width 162.6, nhung so dung
        la 162.5). Sai so 0.1dp nghe nho nhung lam tolerance +-2dp chay khong
        nhat quan. Lam tron CHI o tang hien thi: dung rounded()/as_tuple().
        """
        return Bounds(
            self.left * factor, self.top * factor,
            self.right * factor, self.bottom * factor,
        )

    def rounded(self, ndigits: int = 1) -> Bounds:
        """Ban da lam tron, dung khi hien thi cho nguoi doc."""
        return Bounds(
            round(self.left, ndigits), round(self.top, ndigits),
            round(self.right, ndigits), round(self.bottom, ndigits),
        )

    def as_tuple(self, ndigits: int = 1) -> tuple[float, float, float, float]:
        """Cho payload JSON - lam tron de so hien ra khong dai dong."""
        return (
            round(self.left, ndigits), round(self.top, ndigits),
            round(self.right, ndigits), round(self.bottom, ndigits),
        )

    def size_tuple(self, ndigits: int = 1) -> tuple[float, float]:
        """Width/height lam tron TU SO CHINH XAC (khong tu canh da lam tron)."""
        return (round(self.width, ndigits), round(self.height, ndigits))


@dataclass(frozen=True, slots=True)
class DeviceNode:
    """Mot node trong cay `uiautomator dump`.

    resource_id KHONG UNIQUE - da xac nhan tren may that: 1 GridView chua 4 card,
    ca 4 dung chung resource-id 'borderContainer'. Vi vay khoa doi chieu la
    (resource_id, index_in_parent), khong bao gio la resource_id mot minh.
    """

    node_id: str                  # duong dan trong cay, vd "0.1.3.2" - unique
    resource_id: str              # da bo prefix package, vd "tvQuestionTitle"
    resource_id_full: str         # nguyen ban, vd "com.x:id/tvQuestionTitle"
    cls: str                      # vd "android.widget.TextView"
    text: str
    content_desc: str
    bounds_px: Bounds
    bounds_dp: Bounds
    clickable: bool
    visible: bool
    parent_id: str | None
    index_in_parent: int
    depth: int

    @property
    def short_cls(self) -> str:
        return self.cls.rsplit(".", 1)[-1] if self.cls else ""

    @property
    def label(self) -> str:
        """Ten de tester nhan ra node tren report."""
        if self.resource_id:
            return self.resource_id
        if self.text:
            return f"{self.short_cls}({self.text[:20]!r})"
        return f"{self.short_cls}@{self.node_id}"

    @property
    def match_key(self) -> tuple[str, int]:
        """Khoa doi chieu. Xem docstring class ve chuyen resource_id trung."""
        return (self.resource_id, self.index_in_parent)
