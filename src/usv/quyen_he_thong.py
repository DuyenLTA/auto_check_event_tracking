"""Tim nut CHO PHEP cua dialog quyen he thong.

Android 13+ hoi quyen thong bao ngay lan mo app dau tien, va dialog do do
`com.google.android.permissioncontroller` ve - no nam DE tren app, nen moi
selector cua app deu khong thay gi va ca flow hut ngay buoc dau. Da gap that:
lan chay sau khi cai lai app hut o `wait_text 'What do you want to create'`
trong khi man that su dang hien la dialog quyen.

Chi bam nut CHO PHEP, khong bao gio bam TU CHOI: flow dung de do event cua app
o trang thai binh thuong, ma tu choi quyen la mot trang thai khac han.
"""

from __future__ import annotations

from .models import DeviceNode

# resource_id cua permissioncontroller, on dinh qua nhieu ban Android.
# `parse_dump` da bo tien to package nen o day chi con phan sau dau `/`.
MAU_ID = (
    "permission_allow_button",
    "permission_allow_foreground_only_button",
    "permission_allow_one_time_button",
    "permission_allow_all_button",
)
# Du phong khi ban Android doi id: bam theo chu tren nut. Chi nhan chu KHANG
# DINH, khong nhan "Khong cho phep" (chua ca "cho phep" trong no - nen phai so
# khop TUYET DOI, khong dung `in`).
MAU_TEXT = ("cho phép", "allow", "chỉ lần này", "while using the app",
            "khi dùng ứng dụng")


def tim_nut_cho_phep(nodes: list[DeviceNode]) -> DeviceNode | None:
    """Nut Cho phep cua dialog quyen, hoac None neu khong co dialog nao."""
    dung_duoc = [n for n in nodes if n.visible and not n.bounds_px.empty]
    for node in dung_duoc:
        if node.resource_id in MAU_ID:
            return node
    for node in dung_duoc:
        chu = node.text.strip().casefold()
        if chu in MAU_TEXT:            # khop TUYET DOI, xem docstring
            return node
    return None
