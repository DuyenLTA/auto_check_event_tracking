"""Check event_params: thieu param, gia tri ngoai danh sach, sai kieu, thua param.

Thu tu cham co y: thieu -> gia tri -> kieu -> thua. Mot param sai o buoc som thi
khong cham tiep - noi "sai gia tri VA sai kieu" cho cung mot o la nhieu.

HAI GUARD BAT BUOC, thieu mot cai la tool bao oan hang loat:

1. Param HE THONG bi loc TRUOC khi cham "thua param". Firebase tu gan
   `ga_event_origin` vao 42/42 event; khong loc thi moi event deu FAIL_PARAM_EXTRA.
   Xem event_system_params.

2. Dong log BI CAT (`truncated`) -> NOT_VERIFIABLE, khong bao thieu param. Tran
   payload logcat la 4068 B; dong bi cat mat duoi thi param con lai khong phai
   la app khong gui.

KIEM KIEU MOT CHIEU - gioi han that cua logcat, khong phai luoi:
    spec Number, app gui 'home'  -> FAIL_TYPE      (sai ro)
    spec Number, app gui '3'     -> PASS
    spec String, app gui 'home'  -> PASS
    spec String, app gui '3'     -> NOT_VERIFIABLE (logcat in Long 3 va String
                                                    "3" y het nhau)
"""

from __future__ import annotations

import re

from ..check_models import CheckResult, Verdict
from ..event_spec_models import SpecEvent, SpecParam, SpecSheet
from ..event_system_params import global_params
from ..event_window import Window

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?$")


def _looks_numeric(value: str) -> bool:
    return bool(_NUMBER.match((value or "").strip()))


def run(spec: SpecSheet, windows: tuple[Window, ...], config,
        *, fa_silent: bool = False, stream_died: bool = False,
        app_seen_running: bool = True) -> list[CheckResult]:
    # stream_died khong doi gi o day: event NAO BAT DUOC thi param cua no van
    # doc duoc day du. Chi check presence moi phai than trong.
    #
    # Nhung app KHONG HE CHAY thi khac: event bat duoc la cua app khac, nen
    # param cua chung cung khong noi gi ve app duoi test. Im lang o day, de
    # check presence noi mot lan cho ro - xem event_presence.
    if not app_seen_running:
        return []
    setting = config.checks.get("event_params")
    options = setting.options if setting else {}
    catch_extra = bool(options.get("param_extra", True))
    use_heuristic = bool(options.get("global_param_heuristic", False))

    globals_seen = _globals(windows) if use_heuristic else frozenset()
    known = {e.name: e for e in spec.events}
    out: list[CheckResult] = []

    for window in windows:
        event = known.get(window.spec_event)
        if event is None:
            continue
        for observed in window.named(event.name)[:1]:   # lan ban dau tien
            if observed.truncated:
                out.append(CheckResult(
                    element=event.name, check="event_params",
                    verdict=Verdict.NOT_VERIFIABLE,
                    message=("Dòng log bị logcat cắt mất phần cuối (trần payload "
                             "4068 B) nên danh sách param không đầy đủ — không "
                             "kết luận được là app thiếu param."),
                ))
                continue
            out.extend(_check_params(event, observed.params, catch_extra,
                                     globals_seen, window.expect_params))
    return out


def _check_params(event: SpecEvent, got: dict[str, str], catch_extra: bool,
                  globals_seen: frozenset[str],
                  expect: dict[str, str] | None = None) -> list[CheckResult]:
    out: list[CheckResult] = []
    wanted = expect or {}
    for param in event.params:
        label = f"{event.name}.{param.name}"
        if param.name not in got:
            out.append(CheckResult(
                element=label, check="event_params", verdict=Verdict.FAIL_MISSING,
                expected=_want(param), actual="không gửi",
                message=(f"Spec khai param {param.name!r} mà app không gửi. "
                         f"App gửi: {', '.join(got) or '(không param nào)'}."),
            ))
            continue

        value = got[param.name]
        # Case tu dong lai app toi DUNG MOT cho nen no biet gia tri nao phai ra
        # - cham theo do thi chat hon danh sach cho phep cua spec. Do la cach
        # duy nhat bat duoc loi "man Result bao placement_name=home".
        exact = wanted.get(param.name)
        if exact is not None and value != exact:
            out.append(CheckResult(
                element=label, check="event_params", verdict=Verdict.FAIL_VALUE,
                expected=f"{exact} (case này lái tới đúng chỗ đó)", actual=value,
                delta=f"{value!r} thay vì {exact!r}",
                message=(f"Case lái app tới nơi phải ra {exact!r} nhưng app gửi "
                         f"{value!r}."),
            ))
            continue
        if not param.free_form and value not in param.allowed:
            out.append(CheckResult(
                element=label, check="event_params", verdict=Verdict.FAIL_VALUE,
                expected=_want(param), actual=value,
                delta=f"{value!r} ngoài danh sách",
                message=(f"Giá trị {value!r} không nằm trong danh sách spec cho "
                         f"phép ({', '.join(param.allowed)})."),
            ))
            continue

        if param.wants_number and not _looks_numeric(value):
            out.append(CheckResult(
                element=label, check="event_params", verdict=Verdict.FAIL_TYPE,
                expected=f"kiểu {param.value_type}", actual=value,
                message=f"Spec khai {param.value_type} mà app gửi {value!r}.",
            ))
            continue

        if param.wants_string and _looks_numeric(value):
            out.append(CheckResult(
                element=label, check="event_params",
                verdict=Verdict.NOT_VERIFIABLE,
                expected=f"kiểu {param.value_type}", actual=value,
                message=("logcat in số Long và chuỗi số y hệt nhau nên không "
                         f"phân biệt được {value!r} là String hay Number. Giá trị "
                         "thì đúng — chỉ riêng KIỂU là chưa kết luận được."),
            ))
            continue

        out.append(CheckResult(
            element=label, check="event_params", verdict=Verdict.PASS,
            expected=_want(param), actual=value,
            message=f"Param khớp spec (= {value!r}).",
        ))

    if catch_extra:
        out.extend(_extra_params(event, got, globals_seen))
    return out


def _extra_params(event: SpecEvent, got: dict[str, str],
                  globals_seen: frozenset[str]) -> list[CheckResult]:
    out = []
    for name, value in got.items():
        if name in event.param_names:
            continue
        if name in globals_seen:
            # Param co mat o MOI event -> gan nhu chac la global param tu khai
            # (setDefaultEventParameters), khong phai app gui sai o event nay.
            out.append(CheckResult(
                element=f"{event.name}.{name}", check="event_params",
                verdict=Verdict.EXTRA, actual=value,
                message=("Param này có ở mọi event quan sát được nên rất có thể "
                         "là global param app tự khai, không phải lỗi ở event "
                         "này. Không tính vào fail."),
            ))
            continue
        out.append(CheckResult(
            element=f"{event.name}.{name}", check="event_params",
            verdict=Verdict.FAIL_PARAM_EXTRA, actual=value,
            message=(f"App gửi param {name!r} mà spec không khai. Nếu đúng là "
                     "app cần gửi thì cập nhật spec."),
        ))
    return out


def _want(param: SpecParam) -> str:
    if param.free_form:
        return f"{param.value_type} (không giới hạn giá trị)"
    return f"{param.value_type}: {', '.join(param.allowed)}"


def _globals(windows: tuple[Window, ...]) -> frozenset[str]:
    sets = [frozenset(e.params) for w in windows for e in w.app_events]
    return global_params(sets)
