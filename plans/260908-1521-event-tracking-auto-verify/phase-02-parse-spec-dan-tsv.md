---
phase: 2
title: "Parse spec dán TSV"
status: completed
priority: P1
effort: "5h"
dependencies: [1]
---

# Phase 2: Parse spec dán TSV — rủi ro cao nhất

## Overview
Tester dán bảng spec 8 cột vào ô text → parse thành `SpecEvent` → trả payload cho
bảng preview. Không có preview thì không cho Ghi.

## Key insight — spike đã bắt lỗi thật, đừng lặp lại

Gộp dòng theo số cột **KHÔNG chạy được**. Đo trên chính bảng user gửi:

```
"rating_placement_viewed\tKhi man rating hien thi\tplacement_name\t"  -> 4 cot
+ "String\tresult, exit_click, app_shortcut, home\tVi tri"            -> 3 cot
= 6 cot, PHAI la 7   <- o `Param Description` rong bi "String" chiem cho
```

Hệ quả nếu gộp thô: parser thấy 6 < 7 nên **ăn luôn hàng sau**, spec sai mà không
báo gì. Đúng thứ `check_config.py:4` gọi là "kiểu im lặng nguy hiểm hơn crash".

**Chốt: parse nghiêm, một hàng một dòng, KHÔNG tự gộp.** Hàng sai số cột → đưa vào
danh sách lỗi kèm số dòng + số cột đếm được, hiện ở preview cho tester tự sửa.
(Dán từ Excel vào `<textarea>` thật thì giữ một hàng một dòng và giữ ô rỗng bằng
tab liên tiếp — bảng trong tin nhắn chat bị gãy là do chat reflow, không phải clipboard.)

## Requirements
- Functional: nhận header bất kể thứ tự cột; hàng có `Event_Name` rỗng = param tiếp
  của event phía trên; `Value` là danh sách phân tách dấu phẩy, rỗng = free-form
  (chỉ kiểm có mặt + kiểu); trả cả `errors` lẫn `events`.
- Non-functional: 0 event hoặc thiếu cột bắt buộc → **lỗi rõ**, không parse bừa.

## Architecture
```
event_spec_models.py   SpecParam(name, value_type, allowed: tuple[str,...], description)
                       SpecEvent(screen, name, triggered, params: dict[str, SpecParam])
                       SpecSheet(events: tuple[SpecEvent,...], errors: tuple[str,...])
event_spec_parse.py    parse_paste(text) -> SpecSheet
```
Cột bắt buộc: `Event_Name`, `Params`, `Value Type`. Cột tuỳ chọn: `Screen Name`,
`Triggered`, `Value`, `Param Description`, `Value Description`.
Nhận diện cột bằng header đã `strip().lower()` — cho phép cột lạ, bỏ qua.

## Related Code Files
- Create: `src/usv/event_spec_models.py` (~70 LOC)
- Create: `src/usv/event_spec_parse.py` (~150 LOC)
- Create: `tests/test_event_spec_parse.py`
- Create: `tests/fixtures/event-spec-rating.tsv` (spec thật của user, TSV đúng)
- Create: `tests/fixtures/event-spec-broken.tsv` (bản bị gãy dòng như trong chat)

## Implementation Steps
1. `event_spec_models.py` — dataclass `frozen=True, slots=True` theo đúng kiểu `models.py`.
2. `event_spec_parse.py`:
   - `split("\n")`, bỏ dòng trắng, dòng đầu = header
   - map tên cột → index; thiếu cột bắt buộc → `errors` + `events` rỗng
   - mỗi dòng: số cột **phải bằng** header; khác → `errors.append(f"dòng {i}: {n} cột, cần {ncol}")`
   - `Event_Name` rỗng → gắn vào event hiện tại; chưa có event nào → `errors`
   - `Value` split `,` + strip; rỗng → `allowed = ()` (free-form)
3. Test:
   - spec thật → 2 event, `rating_star_clicked` có **đúng 2 param**
   - **bản gãy dòng → `errors` không rỗng, KHÔNG tự gộp, KHÔNG ra spec sai**
   - thiếu cột `Value Type` → lỗi rõ, không crash
   - hàng param mồ côi (không event nào trước) → lỗi rõ
   - `Value` rỗng → `allowed == ()`
   - cột lạ thêm vào → vẫn parse được
4. `python -m py_compile` sau mỗi file, rồi `pytest`.

## Success Criteria
- [x] Spec thật của user parse ra đúng 2 event / 3 param
- [x] Bản gãy dòng bị **từ chối kèm số dòng**, không đoán
- [x] Không có nhánh nào parse bừa khi thiếu cột
- [x] Cả 2 file <200 LOC

## Risk Assessment
- **Excel thật có thể xuất khác dự đoán** (dấu ngoặc kép quanh ô chứa dấu phẩy).
  Chặn: thử `csv.reader(delimiter="\t")` trước, fallback `split("\t")`; test cả 2 dạng.
- **Open question 2 chưa có lời** — spec thật bao nhiêu event. Không chặn phase này,
  nhưng chặn UX phase 6.
