"""Parse XML cua `uiautomator dump` thanh cay DeviceNode. Pure -> test bang fixture.

Giu NGUYEN CAU TRUC CAY (parent_id, index_in_parent, depth) chu khong lam phang:
matcher can index_in_parent lam khoa vi resource-id KHONG unique (1 GridView co
4 card dung chung resource-id 'borderContainer' - da xac nhan tren may that).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .density import ScreenMetrics
from .models import Bounds, DeviceNode

_BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")

# Node cua he thong, khong phai UI cua app dang test. Loc khoi bucket EXTRA de
# report khong day ra hang chuc dong vo nghia.
_SYSTEM_ID_PREFIXES = (
    "android:id/",
    "com.android.systemui:id/",
    "com.google.android.apps.nexuslauncher:id/",
    "com.android.launcher",
)
# resource-id cua chinh Android Framework, luon co trong moi Activity.
_FRAMEWORK_IDS = frozenset({
    "content", "action_bar_root", "decor_content_parent", "navigationBarBackground",
    "statusBarBackground", "action_mode_bar_stub", "title_container",
})


def parse_bounds(raw: str) -> Bounds:
    """'[0,72][1080,283]' -> Bounds(0, 72, 1080, 283)."""
    match = _BOUNDS_RE.fullmatch(raw.strip())
    if not match:
        raise ValueError(f"bounds khong doc duoc: {raw!r}")
    left, top, right, bottom = (int(g) for g in match.groups())
    return Bounds(left, top, right, bottom)


def strip_package(resource_id: str) -> str:
    """'com.x:id/tvTitle' -> 'tvTitle'. Giu nguyen neu khong co dang do.

    Bo prefix package de mapping trong design khong phai viet ten package
    (design cua designer khong biet package name cua app).
    """
    return resource_id.rsplit("/", 1)[-1] if "/" in resource_id else resource_id


def is_system_node(node: DeviceNode) -> bool:
    """True voi node cua Framework/SystemUI/Launcher - khong phai UI app."""
    full = node.resource_id_full
    if any(full.startswith(prefix) for prefix in _SYSTEM_ID_PREFIXES):
        return True
    return node.resource_id in _FRAMEWORK_IDS


def parse_dump(xml_text: str, metrics: ScreenMetrics) -> list[DeviceNode]:
    """XML -> danh sach DeviceNode theo thu tu duyet truoc (pre-order).

    Thu tu pre-order = thu tu xuat hien trong cay, dung lam `order` cho check
    order o phase sau.
    """
    root = ET.fromstring(xml_text)
    nodes: list[DeviceNode] = []

    def walk(element: ET.Element, parent_id: str | None, path: str, depth: int) -> None:
        children = [c for c in element if c.tag == "node"]
        for index, child in enumerate(children):
            node_id = f"{path}.{index}" if path else str(index)
            nodes.append(_build(child, parent_id, node_id, index, depth, metrics))
            walk(child, node_id, node_id, depth + 1)

    # <hierarchy> la the goc, khong phai node -> bat dau tu con cua no.
    walk(root, None, "", 0)
    return nodes


def _build(
    element: ET.Element,
    parent_id: str | None,
    node_id: str,
    index: int,
    depth: int,
    metrics: ScreenMetrics,
) -> DeviceNode:
    attr = element.attrib
    raw_bounds = attr.get("bounds", "")
    try:
        bounds_px = parse_bounds(raw_bounds)
    except ValueError:
        # Node khong co bounds hop le van phai giu lai (de cay khong lech index),
        # nhung danh dau invisible de moi check hinh hoc bo qua.
        bounds_px = Bounds(0, 0, 0, 0)

    resource_full = attr.get("resource-id", "").strip()
    # visible: uiautomator khong luon co thuoc tinh nay -> suy tu bounds rong.
    declared_visible = attr.get("visible-to-user", "true") != "false"

    return DeviceNode(
        node_id=node_id,
        resource_id=strip_package(resource_full),
        resource_id_full=resource_full,
        cls=attr.get("class", ""),
        text=attr.get("text", ""),
        content_desc=attr.get("content-desc", ""),
        bounds_px=bounds_px,
        bounds_dp=metrics.bounds_to_dp(bounds_px),
        clickable=attr.get("clickable") == "true",
        visible=declared_visible and not bounds_px.empty,
        parent_id=parent_id,
        index_in_parent=index,
        depth=depth,
    )


def app_nodes(nodes: list[DeviceNode]) -> list[DeviceNode]:
    """Bo node he thong. Dung cho bucket EXTRA va cho thong ke."""
    return [n for n in nodes if not is_system_node(n)]


def dump_stats(nodes: list[DeviceNode]) -> dict:
    """So lieu de tester biet ngay chat luong dump - dump nghe kem thi matcher
    se yeu, biet som tot hon biet muon (vd app Compose khong gan testTag)."""
    # Gom set parent 1 lan roi tra cuu - tranh O(n^2) tren dump lon.
    parents = {n.parent_id for n in nodes if n.parent_id is not None}
    leaves = [n for n in nodes if n.node_id not in parents]
    return {
        "total": len(nodes),
        "with_resource_id": sum(1 for n in nodes if n.resource_id),
        "leaves": len(leaves),
        "leaves_with_resource_id": sum(1 for n in leaves if n.resource_id),
        "leaves_matchable": sum(
            1 for n in leaves if n.resource_id or n.text or n.content_desc
        ),
        "compose_nodes": sum(1 for n in nodes if "compose" in n.cls.lower()),
    }
