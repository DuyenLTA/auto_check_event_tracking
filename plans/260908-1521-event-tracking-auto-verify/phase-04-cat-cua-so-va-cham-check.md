---
phase: 4
title: "Cắt cửa sổ theo marker + chấm check"
status: completed
priority: P1
effort: "6h"
dependencies: [2, 3]
---

# Phase 4: Cắt cửa sổ theo marker + chấm check

## Overview
Cắt timeline log thành các cửa sổ theo marker, rồi chấm từng dòng spec × cửa sổ ra
verdict. Đây là tầng ra kết luận.

## Key insight — 5 case đã chạy thật, dùng làm test hồi quy

Spike đã chạy spec thật × log thật. Bê nguyên thành test:

| Case | Kết quả phải ra |
|---|---|
| Spec đúng | **3 PASS, 0 fail oan** — 3 param `ga_*` không được sinh `FAIL_PARAM_EXTRA` |
| Bỏ `home` khỏi `Value` | `FAIL_VALUE` × 2 |
| Spec khai `placement_name` là `Number` | `FAIL_TYPE` × 2 |
| Spec khai thêm `rating_source` | `FAIL_MISSING` |
| Spec ghi sai tên `rating_star_click` | `FAIL_MISSING` (event không bắn) |
| `error_code=3` mà spec khai `String` | `NOT_VERIFIABLE` |

Case đầu là quan trọng nhất: **0 fail oan**. Nếu nó đỏ thì tool vô dụng bất kể các case sau.

## Requirements
- Functional: một nút một bước (marker sau = điểm kết trước); bắn trùng chấm **theo
  từng cửa sổ**, không theo cả phiên; event spec chưa có marker nào → `NOT_TESTED`;
  event `origin=auto`/`am` → `EXTRA`; kiểm kiểu **một chiều**.
- Non-functional: check thuần hàm, không chạm adb → test không cần máy.

## Architecture
```
event_window.py         cut(lines, markers) -> tuple[Window,...]
                        Window(label, spec_event, events: tuple[ObservedEvent,...], edge: tuple)
checks/event_presence.py  có bắn · bắn trùng · chưa test
checks/event_params.py    thiếu · thừa · giá trị · kiểu
```
Cửa sổ cuối kết ở lúc Dừng ghi. Event nằm trong **vùng đệm** ở biên (mặc định 250 ms)
thì vẫn tính vào cửa sổ nhưng gắn cờ `near_edge` để phase 5 in ra — R4.

### Kiểm kiểu một chiều
| Spec | App gửi | Kết luận |
|---|---|---|
| `Number` | `home` | **FAIL_TYPE** — sai rõ |
| `Number` | `3` | PASS |
| `String` | `home` | PASS |
| `String` | `3` | **NOT_VERIFIABLE** — logcat in Long `3` và String `"3"` y hệt |

## Related Code Files
- Create: `src/usv/event_window.py` (~90 LOC)
- Create: `src/usv/checks/event_presence.py` (~120 LOC)
- Create: `src/usv/checks/event_params.py` (~170 LOC)
- Create: `src/usv/event_check_runner.py` (~45 LOC) — **KHÔNG** dùng `check_runner._REGISTRY`
- Create: `tests/test_event_window.py`, `tests/test_check_event.py`

## Implementation Steps
1. `event_window.py` — cắt theo timestamp marker; marker cuối → hết log; vùng đệm biên.
2. `checks/event_presence.py`:
   - spec event không có cửa sổ nào → `NOT_TESTED`
   - có cửa sổ, 0 lần bắn → `FAIL_MISSING`
   - >1 lần **trong cùng cửa sổ** → `FAIL_DUPLICATE` (nói rõ số lần)
   - event `origin != app` và event `origin=app` không có trong spec → `EXTRA`
3. `checks/event_params.py` — thứ tự chấm: thiếu → giá trị → kiểu → thừa.
   Lọc param hệ thống **trước** khi chấm "thừa", dùng `event_system_params`.
   `allowed == ()` → bỏ qua bước giá trị, chỉ kiểm có mặt + kiểu.
4. Đăng ký `_REGISTRY`: `"event_presence"`, `"event_params"`.
5. Test — 6 case bảng trên, chạy trên fixture thật, **không mock**.
6. `pytest`.

## Success Criteria
- [x] Case "spec đúng" ra **3 PASS, 0 fail** — không fail oan từ `ga_*`
- [x] 5 case gài lỗi ra đúng verdict đúng chỗ
- [x] `NOT_TESTED` không vào `Summary.failed` (phase 1 đã khoá)
- [x] Bắn trùng chấm theo cửa sổ: `track_ad_request` 17x/phiên **không** thành fail
- [x] Cả 3 file mới <200 LOC

## Risk Assessment
- **R4: event sát biên marker.** Vùng đệm 250 ms là số **đoán**, chưa đo. Chặn: gắn
  cờ `near_edge` và in ra, để tester thấy chứ không im lặng. Đo lại khi có phiên thật.
- Bắn trùng dễ báo oan nếu app có retry. Chặn: message nói rõ số lần + mốc thời gian
  để tester tự phán, và `event_presence.duplicate` bật/tắt riêng trong YAML.

## Lệch khỏi plan khi làm

**Không thêm được vào `check_runner._REGISTRY`.** Plan ghi "2 dòng vào `_REGISTRY`" —
sai. `check_runner.run` nhận `MatchResult` (các cặp design node ↔ device node đã ghép),
còn check event nhận `SpecSheet` + cửa sổ log: hình dạng đầu vào khác hẳn, nhồi vào một
registry chung là phải bóp méo một trong hai bên.

Làm `event_check_runner.py` riêng (43 LOC), dùng lại `CheckResult` · `Summary` ·
`CheckConfig` · `sort_for_report`. Từ vựng verdict vẫn ở một chỗ duy nhất
(`check_models`); chỉ tầng **điều phối** là riêng. `KNOWN_CHECKS` trong `check_config`
vẫn dùng chung — config là chung, runner là riêng.
