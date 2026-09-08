---
phase: 5
title: "Report theo mẫu tool ads"
status: completed
priority: P2
effort: "4h"
dependencies: [4]
---

# Phase 5: Report theo mẫu tool check ID ads

## Overview
Render kết quả thành HTML theo đúng hệ thiết kế của `ad-checklist-diff`, cộng xlsx
qua `exporter.py` sẵn có. User đã chốt mẫu này, **không** dùng tầng report của tool UI.

## Key insight
Mock đã dựng sẵn, **mọi số tính từ log thật**, không gõ tay:
`plans/reports/260908-1521-event-report-mock.html`
→ https://claude.ai/code/artifact/d33633ec-6594-457f-a024-ac4b153f27e5
Phase này là port mock đó thành module + test, không phải thiết kế lại.

## Requirements
- Functional: 5 trạng thái hiển thị phân biệt được; scorecard **mẫu số = số dòng đã
  kiểm**; `NOT_TESTED` + `EXTRA` ra chip riêng; callout cho `EXTRA` và cho R3.
- Non-functional: self-contained HTML; 3 trạng thái theme; `overflow-x` cho bảng rộng.

## Architecture
Bê nguyên token của `ad-checklist-diff/report_renderer.py`, **không thêm màu**:
`--accent:#146b6e` · `--paper:#eef2f1` · `--pass:#1f7a4d` · `--fail:#b23b2e` · `--pending:#97650f`
+ đủ bộ dark. Chữ: Manrope 800 / Public Sans / JetBrains Mono, `tabular-nums`.
Bố cục: eyebrow → h1 → scorecard có bar → section chips → callout → `<details>` mỗi screen.

Mở rộng, chỉ những chỗ event cần 5 trạng thái thay vì 2:

| Việc | Cách |
|---|---|
| `NOT_VERIFIABLE` | thêm rule `.status.pending` — **token `--pending` đã có**, chỉ thiếu rule |
| `NOT_TESTED` / `EXTRA` | thêm `.status.not_tested` trung tính (`--surface-alt` + viền `--line`) |
| Bảng 3→5 cột | Event · Param · Spec cần · App gửi · Kết quả. `min-width` 480→720 px |
| Section | theo `Screen Name` — khớp pattern section-per-mục của report ads |
| Scorecard | mẫu số = số dòng đã kiểm; `NOT_TESTED`/`EXTRA` **không bao giờ** vào số fail |

Theme phải viết đúng 3 tầng: `:root` sáng · `@media (prefers-color-scheme: dark)` bọc
`:root:not([data-theme="light"])` · `:root[data-theme="dark"]`. Không màu nào chỉ được
định nghĩa bên trong media/`[data-theme]`.

## Related Code Files
- Create: `src/usv/report_event_css.py` (~130 LOC)
- Create: `src/usv/report_event_html.py` (~170 LOC)
- Modify: `src/usv/routes_export.py` (thêm endpoint xlsx cho event)
- Create: `tests/test_report_event.py`
- Reference: `plans/reports/260908-1521-event-report-mock.html`

## Implementation Steps
1. `report_event_css.py` — token + CSS thành hằng chuỗi. Tách riêng khỏi HTML để
   cả 2 file dưới 200 LOC.
2. `report_event_html.py` — scorecard, chips, callout, `<details>` mỗi screen.
3. xlsx: dùng `exporter.py` sẵn có (`_tone` đã sửa ở phase 1).
4. Test:
   - đủ 5 class trạng thái xuất hiện khi input có đủ 5 verdict
   - **scorecard mẫu số không gồm `NOT_TESTED` và `EXTRA`**
   - `fa_silent=True` → callout R3 xuất hiện
   - `near_edge` → in ra, không im lặng
   - có cả 3 block theme; **không** màu nào chỉ nằm trong media query
   - escape HTML: event/param/giá trị chứa `<script>` phải bị escape
5. `pytest`.

## Success Criteria
- [x] Trông giống report tool ads (cùng token, cùng font, cùng bố cục)
- [x] 5 trạng thái phân biệt được bằng mắt
- [x] Mẫu số scorecard loại `NOT_TESTED`/`EXTRA`
- [x] Giá trị từ log được escape
- [x] Cả 2 file <200 LOC

## Risk Assessment
- Giá trị log là dữ liệu **không kiểm soát** (`error_msg` chứa backtick, dấu ngoặc).
  Chặn: `html.escape` mọi chỗ + test có `<script>`.
- Bảng 5 cột trên màn hẹp. Chặn: `.table-scroll` `overflow-x:auto`, body không tràn ngang.

## Lệch khỏi plan khi làm

**Bỏ endpoint xlsx ở phase này.** Plan ghi sửa `routes_export.py`, nhưng chưa có route
event nào (phase 6) nên chưa có gì để export. Dồn sang phase 6 cùng các route khác.

**Sửa một lỗi UX tự phát hiện khi render thật:** section mà mọi dòng đều `NOT_TESTED`
hiện ra `0/0 khớp` — vô nghĩa với người đọc, vì `NOT_TESTED` bị loại khỏi mẫu số.
Đổi thành `chưa test (N)`. Có test khoá: `test_section_toan_chua_test_...`.
