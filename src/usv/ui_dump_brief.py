"""Cay UI rut gon du de NGUOI (va Claude) doc bang mat.

`uiautomator dump` tra hang tram node, phan lon la layout rong. Do ca ra thi
nguoi doc chim trong du lieu va van khong biet bam vao dau. O day chi giu node
bam duoc hoac co chu - dung nhung thu co the viet thanh selector.

Moi dong deu kem `index=`: mot resource_id co the ung voi nhieu node (da xac
nhan tren may that: 4 card cung id `borderContainer`), khong co so thu tu thi
selector viet ra khong biet tro vao card nao.
"""

from __future__ import annotations

from .models import DeviceNode

MAX_TEXT = 40


def _needle(node: DeviceNode) -> tuple[str, str]:
    """(kieu, gia tri) se dung lam selector. Uu tien resource_id: no song qua
    lan doi ngon ngu, con text/desc thi khong."""
    if node.resource_id:
        return "resource_id", node.resource_id
    if node.content_desc.strip():
        return "desc", node.content_desc.strip()
    return "text", node.text.strip()


def _dung_duoc(node: DeviceNode) -> bool:
    if not node.visible or node.bounds_px.empty:
        return False
    return bool(node.clickable or node.text.strip()
                or node.content_desc.strip() or node.resource_id)


def brief(nodes: list[DeviceNode]) -> list[str]:
    """Mot dong mot node, da danh so theo nhom cung selector."""
    dong: list[str] = []
    dem: dict[tuple[str, str], int] = {}
    for node in nodes:
        if not _dung_duoc(node):
            continue
        kieu, gia_tri = _needle(node)
        if not gia_tri:
            continue
        khoa = (kieu, gia_tri)
        index = dem.get(khoa, 0)
        dem[khoa] = index + 1

        phan = [f"{kieu}={gia_tri!r}", f"index={index}"]
        if kieu != "text" and node.text.strip():
            phan.append(f"text={node.text.strip()[:MAX_TEXT]!r}")
        if kieu != "desc" and node.content_desc.strip():
            phan.append(f"desc={node.content_desc.strip()[:MAX_TEXT]!r}")
        phan.append(f"[{node.short_cls}]")
        if not node.clickable:
            phan.append("(không bấm được)")
        dong.append(" ".join(phan))
    return dong
