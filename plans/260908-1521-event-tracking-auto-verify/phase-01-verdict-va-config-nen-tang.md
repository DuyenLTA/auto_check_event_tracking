---
phase: 1
title: "Verdict + config nền tảng"
status: completed
priority: P1
effort: "3h"
dependencies: []
---

# Phase 1: Verdict + config nền tảng — viết test TRƯỚC

## Overview
Thêm 5 verdict cho domain event và đăng ký 2 check mới vào config. Đây là phase
duy nhất **sửa file dùng chung**, nên viết test trước.

## Vì sao test trước — có regression THẬT đang chờ

Không phải phòng xa. Đã đọc code và xác định:

| Chỗ | Code hiện tại | Thêm `NOT_TESTED` mà không sửa |
|---|---|---|
| `check_models.py` `Summary.add()` | `else: self.failed += 1` | **`NOT_TESTED` bị đếm thành FAIL** — vi phạm nguyên tắc 1 |
| `exporter.py:43` `_tone()` | rơi xuống nhánh fail | ô xlsx tô **đỏ** như lỗi thật |
| `web/render.js:103` | `VERDICT_CLASS[r.verdict] ?? 'v-fail'` | hiện **đỏ** trên UI |
| `report_matrix.py:45` | `if verdict in FAIL_VERDICTS` | 4 verdict `FAIL_*` mới **không được tô** nếu quên thêm vào set |

`verdict_label()` thì lành: `.get(v, str(v))` nên chỉ in thô tên enum, không sai nghĩa.

## Requirements
- Functional: 5 verdict mới; `NOT_TESTED` không vào `failed` ở **cả 4 chỗ** trên;
  4 `FAIL_*` mới vào `FAIL_VERDICTS` và vào `failed`.
- Non-functional: **không đổi tên/giá trị 5 verdict cũ**; file vẫn <200 LOC
  (`check_models.py` đang 173 → tách nếu vượt).

## Architecture
```
Verdict (StrEnum)  += FAIL_VALUE · FAIL_TYPE · FAIL_DUPLICATE · FAIL_PARAM_EXTRA · NOT_TESTED
VERDICT_LABEL      += 5 nhãn tiếng Việt
VERDICT_ICON       += 5
FAIL_VERDICTS      += 4 (KHÔNG có NOT_TESTED)
Summary            += not_tested: int, chặn TRƯỚC nhánh else, + vào headline()
```
`Summary.not_tested` đặt cạnh `unmatched`/`extra` và **return sớm** như hai cái đó —
cùng một lý do: không phải lỗi app.

## Related Code Files
- Modify: `src/usv/check_models.py` (enum, 2 map, `FAIL_VERDICTS`, `Summary`)
- Modify: `src/usv/exporter.py` (`_tone`)
- Modify: `src/usv/web/render.js` (`VERDICT_CLASS`)
- Modify: `src/usv/check_config.py` (`KNOWN_CHECKS` += `event_presence`, `event_params`)
- Modify: `config/ui-check-rules.yaml` (2 check mới, mặc định `enabled: true`)
- Create: `tests/test_verdict_event.py`

## Implementation Steps
1. **Test trước** — `tests/test_verdict_event.py`:
   - `Summary` nhận `NOT_TESTED` → `failed == 0`, `not_tested == 1`
   - `Summary` nhận từng `FAIL_*` mới → `failed == 1`
   - `exporter._tone(NOT_TESTED)` **khác** tone của `FAIL_TEXT`
   - `NOT_TESTED not in FAIL_VERDICTS`; 4 `FAIL_*` mới **in** `FAIL_VERDICTS`
   - `verdict_label()` trả nhãn tiếng Việt cho cả 5, không trả tên enum thô
   - **Chạy, phải ĐỎ.** Đỏ ở đâu thì ghi lại — đó là bằng chứng test có tác dụng.
2. Sửa `check_models.py`, `exporter.py`, `render.js`, `check_config.py`, YAML.
3. Grep lại `?? 'v-fail'` và mọi nhánh `else` mặc định-fail còn sót.
4. `pytest` — 459 test cũ + test mới, tất cả xanh.

## Success Criteria
- [x] Test viết trước và **đã chứng minh đỏ** trước khi sửa code
- [x] `NOT_TESTED` không xuất hiện trong `failed` ở Summary, xlsx, UI, matrix
- [x] 5 verdict cũ giữ nguyên **giá trị** chuỗi
- [x] 459 test cũ vẫn xanh
- [x] Mọi file sửa vẫn <200 LOC

## Risk Assessment
- **Đổi giá trị enum cũ** → report/xlsx cũ đọc không khớp. Chặn: test assert
  `str(Verdict.FAIL_TEXT) == "FAIL_TEXT"` cho cả 5 cái cũ.
- `check_models.py` 173 LOC + ~20 dòng → sát 200. Nếu vượt: tách map nhãn/icon
  sang `check_models_labels.py`, **không** tách enum.
