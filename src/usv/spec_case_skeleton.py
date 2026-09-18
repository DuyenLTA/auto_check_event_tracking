"""Khung case sinh tu spec, va cai chot chan agent khong bia ra khoi spec.

Agent doc van xuoi Requirements roi de xuat mot danh sach case. Van xuoi thi
phai suy luan, nhung DOI CHIEU voi bang spec thi do duoc - nen phan do duoc
lam o day bang Python, khong hoi lai agent.

Ba thu chan duoc:
  1. Event/param/gia tri khong co trong bang spec -> tu choi. Agent doc nham
     muc khac cua trang la sinh ra event khong ton tai, im lang rat de lot.
  2. Case bam nut Rate ma reset chi la `relaunch` -> tu choi. Spec noi "khong
     hien pop-up rating khi user da bam rate", tuc mot lan bam la tat vinh
     vien; relaunch khong go duoc, case sau se `not_tested` hang loat.
  3. Gia tri trong spec ma khong case nao phu -> in ra BO SOT. Cung nguyen tac
     voi triage: soi 3/15 ma im thi bao cao trong nhu da soi het.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

# `none`      khong lam gi - case chay tiep tren trang thai case truoc de lai
# `relaunch`  force-stop + mo lai. Du de popup 1-lan-moi-session len lai
# `pm_clear`  xoa sach data. Duong duy nhat go duoc trang thai "da bam rate"
#             tren app KHONG debuggable, doi lai mat login va phai di lai
#             onboarding
RESETS = ("none", "relaunch", "pm_clear")


@dataclass(frozen=True, slots=True)
class CaseSkeleton:
    """Mot case luc chua co `steps`. Tang B moi dien steps vao.

    `expect_params` la cho case CHAT HON spec: spec noi placement_name duoc
    phep la 1 trong 4 gia tri, case noi lan nay PHAI ra dung gia tri nao.
    """

    id: str
    event: str
    expect_params: dict[str, str] = field(default_factory=dict)
    precondition: str = ""          # dieu kien de event ban - lay tu van xuoi
    reset: str = "relaunch"
    # Gia tri remote config case nay CAN co truoc khi chay. Khong phai thu de
    # kiem tra - la tien de. Vi du man rating o luong exit chi hien khi vi tri
    # `home` da bi go khoi `show_rating_placement`: con `home` thi popup da
    # tieu het luot cua session o man home roi, bam back khong ra gi.
    remote_config: dict[str, str] = field(default_factory=dict)
    burns_popup: bool = False       # case nay lam popup tat vinh vien?
    # Case nay chay tiep trang thai do case nao de lai. BAT BUOC khi reset la
    # `none`: khong khai thi thu tu chay nam o thu tu dong trong file, ma thu
    # tu dong thi doi luc nao khong ai biet - hong im lang.
    sau: str = ""
    blocked_by: tuple[str, ...] = ()  # remote key co the chan case nay
    source: str = ""                # cho nao trong trang noi dieu do

    def payload(self) -> dict:
        return {"id": self.id, "event": self.event,
                "expect_params": self.expect_params,
                "precondition": self.precondition, "reset": self.reset,
                "remote_config": self.remote_config,
                "burns_popup": self.burns_popup,
                "sau": self.sau,
                "blocked_by": list(self.blocked_by), "source": self.source}


def parse(raw: object) -> tuple[tuple[CaseSkeleton, ...], tuple[str, ...]]:
    """JSON agent tra ve -> case. Sai kieu thi bao ro, khong doan ho."""
    if not isinstance(raw, list):
        return (), ("Phải là một mảng JSON các case.",)
    cases, errors = [], []
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        where = f"case #{index}"
        if not isinstance(item, dict):
            errors.append(f"{where}: không phải object.")
            continue
        case_id = str(item.get("id") or "").strip()
        event = str(item.get("event") or "").strip()
        if not case_id:
            errors.append(f"{where}: thiếu `id`.")
            continue
        if case_id in seen:
            errors.append(f"{where}: `id` {case_id!r} bị trùng.")
            continue
        seen.add(case_id)
        if not event:
            errors.append(f"{case_id}: thiếu `event`.")
            continue
        params = item.get("expect_params") or {}
        if not isinstance(params, dict):
            errors.append(f"{case_id}: `expect_params` phải là object.")
            continue
        reset = str(item.get("reset") or "relaunch").strip()
        if reset not in RESETS:
            errors.append(
                f"{case_id}: `reset` {reset!r} không hợp lệ, "
                f"chọn một trong {', '.join(RESETS)}.")
            continue
        remote = item.get("remote_config") or {}
        if not isinstance(remote, dict):
            errors.append(f"{case_id}: `remote_config` phải là object.")
            continue
        blocked = item.get("blocked_by") or []
        cases.append(CaseSkeleton(
            id=case_id, event=event,
            expect_params={str(k): str(v) for k, v in params.items()},
            precondition=str(item.get("precondition") or ""),
            reset=reset,
            remote_config={str(k): str(v) for k, v in remote.items()},
            burns_popup=bool(item.get("burns_popup")),
            sau=str(item.get("sau") or "").strip(),
            blocked_by=tuple(str(b) for b in blocked),
            source=str(item.get("source") or "")))
    return tuple(cases), tuple(errors)
