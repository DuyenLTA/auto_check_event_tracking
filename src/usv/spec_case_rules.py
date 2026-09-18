"""Luat doi chieu khung case voi bang spec.

Tach khoi `spec_case_skeleton` (tu vung) vi hai viec khac han nhau: ben kia
noi mot case GOM NHUNG GI, ben nay noi mot bo case co DUNG khong. Doc rieng
thi thay ngay cai gi la dinh nghia, cai gi la rang buoc.
"""

from __future__ import annotations

from .event_spec_models import SpecSheet
from .spec_case_skeleton import CaseSkeleton


def validate(cases: tuple[CaseSkeleton, ...], sheet: SpecSheet,
             remote_keys: tuple[str, ...] = (),
             remote_defaults: dict[str, str] | None = None) -> tuple[str, ...]:
    """Doi chieu case voi bang spec. Rong = khong co gi sai.

    `remote_keys` la ten cac key trang khai. De rong thi bo qua khau kiem ten
    key - trang khong co bang Remote Key thi khong co gi de so, bat bua se bao
    loi tren moi case.
    """
    errors: list[str] = []
    by_name = {e.name: e for e in sheet.events}
    for case in cases:
        event = by_name.get(case.event)
        if event is None:
            errors.append(
                f"{case.id}: event {case.event!r} không có trong bảng spec "
                f"(bảng có: {', '.join(sorted(by_name)) or 'không có event nào'}).")
            continue
        for name, value in case.expect_params.items():
            param = event.param(name)
            if param is None:
                errors.append(
                    f"{case.id}: {case.event} không khai param {name!r}.")
            elif not param.free_form and value not in param.allowed:
                errors.append(
                    f"{case.id}: {name}={value!r} ngoài danh sách spec cho phép "
                    f"({', '.join(param.allowed)}).")
        for key in case.remote_config:
            if remote_keys and key not in remote_keys:
                errors.append(
                    f"{case.id}: remote key {key!r} không có trong trang spec "
                    f"({', '.join(remote_keys)}).")
        for key, value in case.remote_config.items():
            mac_dinh = (remote_defaults or {}).get(key, "")
            if mac_dinh and value.strip().casefold() == mac_dinh.casefold():
                errors.append(
                    f"{case.id}: remote_config {key}={value!r} đúng bằng giá trị "
                    f"mặc định của trang — khai lại không đổi gì, chỉ biến một "
                    f"case chạy được thành case phải sửa Remote Config.")
        if case.remote_config and case.reset == "none":
            # App doc remote config luc process start, nen sua xong ma khong mo
            # lai thi case chay tren gia tri cu - sai im lang, khong bao gi.
            errors.append(
                f"{case.id}: có đổi remote config nhưng `reset` là 'none' — "
                f"app chỉ đọc giá trị mới lúc khởi động, phải `relaunch` "
                f"hoặc `pm_clear`.")
        if case.burns_popup and case.reset != "pm_clear":
            errors.append(
                f"{case.id}: case làm popup tắt vĩnh viễn nhưng `reset` mới là "
                f"{case.reset!r} — phải `pm_clear`, không thì các case sau "
                f"không đo được gì.")
    return tuple(errors)


def missed(cases: tuple[CaseSkeleton, ...],
           sheet: SpecSheet) -> tuple[str, ...]:
    """Thu spec khai ma khong case nao khang dinh. LUON in ra.

    Hai muc, dung bo muc dau: co bang spec ma MOI event deu khong co param
    (daily checkin, widget - moi event chi la "man do co hien khong"). Luc do
    khong co bo ba (event, param, gia tri) nao de thieu, nen neu chi dem bo ba
    thi mot danh sach case RONG cung bao "khong bo sot" - pass gia, dung cai
    kieu im lang ma tool nay sinh ra de tranh.
    """
    have_case = {c.event for c in cases}
    covered = {(c.event, name, value)
               for c in cases for name, value in c.expect_params.items()}
    gaps = []
    for event in sheet.events:
        if event.name not in have_case:
            gaps.append(f"{event.name} (chưa có case nào)")
            continue
        for param in event.params:
            for value in param.allowed:
                if (event.name, param.name, value) not in covered:
                    gaps.append(f"{event.name}.{param.name}={value}")
    return tuple(gaps)


def chain(cases: tuple[CaseSkeleton, ...]) -> tuple[str, ...]:
    """Kiem day case noi tiep nhau: `reset: none` phai khai chay SAU case nao.

    Khong co khau nay thi thu tu chay nam o thu tu dong trong file. Doi cho hai
    dong la case `none` chay trước case dung ra phai dung truoc no, va no khong
    hong ra mat - no chay tren mot man hinh khac roi bao `Chua test`.
    """
    known = {c.id for c in cases}
    errors: list[str] = []
    for case in cases:
        if case.reset == "none" and not case.sau:
            errors.append(
                f"{case.id}: `reset` là 'none' nhưng chưa khai `sau` — "
                f"không biết nó chạy tiếp trạng thái của case nào.")
        if case.sau and case.sau == case.id:
            errors.append(f"{case.id}: `sau` trỏ vào chính nó.")
        elif case.sau and case.sau not in known:
            errors.append(
                f"{case.id}: `sau` trỏ tới {case.sau!r} — không có case nào id đó.")

    # Vong tron: di nguoc chuoi `sau` tu tung case, gap lai chinh minh la vong.
    parent = {c.id: c.sau for c in cases if c.sau in known and c.sau != c.id}
    for start in parent:
        seen, node = {start}, parent[start]
        while node in parent:
            if node in seen:
                errors.append(f"{start}: chuỗi `sau` tạo thành vòng tròn.")
                break
            seen.add(node)
            node = parent[node]
    return tuple(dict.fromkeys(errors))


def order(cases: tuple[CaseSkeleton, ...]) -> tuple[CaseSkeleton, ...]:
    """Thu tu chay suy ra tu chuoi `sau`, khong phu thuoc thu tu dong trong file.

    Sap XEN KE, khong theo tang: moi vong lay case SAN SANG DAU TIEN theo thu
    tu file. Lay het ca tang mot luc thi moi case goc bi don len dau, chen vao
    giua mot day dang do - day case van chay duoc nhung doc thi khong con ra
    trinh tu nao, va diff giua hai lan sinh nhay lung tung.

    He qua: file da xep dung thi thu tu tra ve y nguyen file. Chi case nao co
    cha chua chay moi bi day xuong.

    Goi `chain` truoc: ham nay coi nhu day case da khong con vong tron.
    """
    remaining = list(cases)
    done: set[str] = set()
    out: list[CaseSkeleton] = []
    while remaining:
        found = next((c for c in remaining if not c.sau or c.sau in done), None)
        if found is None:        # con vong tron - tra phan con lai nguyen ven
            out.extend(remaining)
            break
        out.append(found)
        done.add(found.id)
        remaining.remove(found)
    return tuple(out)
