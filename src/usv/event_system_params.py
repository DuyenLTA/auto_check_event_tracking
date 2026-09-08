"""Loc param HE THONG cua Firebase ra khoi phep so voi spec.

Vi sao bat buoc: user da bat "app gui them param spec khong khai = FAIL". Neu
khong loc thi MOI event deu FAIL, vi Firebase tu gan param vao moi event.

Do that tren AIP922 (42 event origin=app):
    ga_event_origin(_o)   42/42
    ga_screen_class(_sc)  40/42
    ga_screen_id(_si)     40/42

Nen luat la TIEN TO, khong phai danh sach ten: `ga_` va `_`. Ben dan tai lieu
Firebase in ra dang `tenDai(tenNgan)` nen ca hai dang deu bi bat sau khi
fa_event_parse da bo hau to ngoac.

CHU Y tien to dung: la `ga_`, KHONG phai `firebase_`. Gia dinh ban dau sai, spike
sua lai.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

# Tien to param do Firebase/GA tu gan.
_SYSTEM_PREFIXES = ("ga_", "_")

# Param Firebase tu gan nhung KHONG mang tien to tren. Giu danh sach ngan va chi
# them khi do duoc that tren may, dung doan.
_SYSTEM_NAMES = frozenset({
    "firebase_event_origin", "firebase_screen", "firebase_screen_class",
    "firebase_screen_id", "firebase_previous_class", "firebase_previous_id",
    "firebase_previous_screen", "engagement_time_msec", "session_id",
})


def is_system(name: str) -> bool:
    key = (name or "").strip()
    if not key:
        return True   # param khong ten thi khong the doi chieu voi spec
    if key.casefold() in _SYSTEM_NAMES:
        return True
    return key.startswith(_SYSTEM_PREFIXES)


def strip_system(params: dict[str, str]) -> dict[str, str]:
    """Bo param he thong, giu nguyen thu tu con lai."""
    return {k: v for k, v in params.items() if not is_system(k)}


def global_params(param_sets: Iterable[frozenset[str]]) -> frozenset[str]:
    """Param co mat o MOI event -> rat co the la global param tu khai.

    `setDefaultEventParameters` gan mot param vao moi event ma spec khong khai -
    bao FAIL la oan hang loat.

    MAC DINH TAT trong YAML (`global_param_heuristic: false`): AIP922 khong co
    global param nao, tien to `ga_` da loc sach, nen bat len la them mot lop
    doan khong can thiet. Chi bat khi gap app that co khai.

    Doi it nhat 2 event: mot event thi param nao cung "co mat o 100% event".
    """
    sets = [s for s in param_sets]
    if len(sets) < 2:
        return frozenset()
    counter: Counter[str] = Counter()
    for names in sets:
        counter.update(names)
    return frozenset(name for name, count in counter.items() if count == len(sets))
