---
phase: 6
title: "Route + tab web"
status: pending
priority: P2
effort: "5h"
dependencies: [5]
---

# Phase 6: Route + tab web

## Overview
Nối các tầng lại thành luồng tester dùng được: dán spec → preview → Ghi → bấm marker
từng bước → Dừng → xem report. Tab mới trong web UI hiện có.

## Key insight — test PHẢI gọi qua HTTP

Bài học đã trả giá ở tool UI: thiếu `import frame_mismatch_note` gây `NameError`
trong thân hàm mà **410 test vẫn xanh**, vì mọi test e2e đều gọi hàm trực tiếp,
bỏ qua route HTTP. Đã phải thêm `tests/test_api_check_route.py` và chứng minh nó
bắt được bug bằng cách xoá import đi.

**Phase này bắt buộc có test gọi qua `TestClient`**, không chỉ gọi hàm.

## Requirements
- Functional: dán spec → preview kèm lỗi từng dòng; **không preview thì không cho Ghi**;
  Ghi (tuỳ chọn từ lúc mở app); một nút một bước; Dừng → check → report.
- Non-functional: middleware loopback sẵn có vẫn áp; state trong `session_state`;
  không thêm dependency mới.

## Architecture
```
routes_event.py   POST /event/spec      dán text -> preview {events, errors}
                  POST /event/record    bat dau ghi (from_launch: bool)
                  POST /event/mark      {label, spec_event} -> chen marker
                  POST /event/stop      dung -> cat cua so
                  POST /event/check     cham -> results + summary
                  GET  /event/state     trang thai hien tai
session_state.py  += EventRun(spec, windows, results, fa_silent)
web/event.js      tab moi
```
Nút marker mang **nhãn cột `Triggered`** ("Khi màn rating hiển thị") để tester biết
phải làm gì — cột văn xuôi này dùng làm nhãn, **không** chạm verdict.

## Related Code Files
- Create: `src/usv/routes_event.py` (~150 LOC)
- Create: `src/usv/web/event.js` (~170 LOC)
- Modify: `src/usv/session_state.py` (`EventRun`)
- Modify: `src/usv/main.py` (1 dòng `include_router`)
- Modify: `src/usv/web/index.html` (tab + panel)
- Create: `tests/test_api_event_route.py`

## Implementation Steps
1. `session_state.py` — `EventRun`, đặt cạnh `CheckRun` sẵn có.
2. `routes_event.py` — 6 endpoint. `/event/mark` từ chối khi chưa Ghi;
   `/event/record` từ chối khi chưa có spec hợp lệ.
3. `main.py` — `include_router`.
4. `index.html` + `event.js` — tab, ô textarea, bảng preview, danh sách nút marker,
   nút Dừng. Nút đã bấm thì đánh dấu để tester biết còn bước nào chưa làm.
5. **`tests/test_api_event_route.py` gọi qua `TestClient`**:
   - `/event/spec` với spec thật → 2 event, `errors` rỗng
   - `/event/spec` với bản gãy → `errors` không rỗng, **HTTP 200** (lỗi dữ liệu, không phải lỗi server)
   - `/event/record` khi chưa có spec → **409**
   - `/event/mark` khi chưa Ghi → **409**
   - `/event/check` khi chưa Dừng → **409**
   - luồng đủ với logcat giả (monkeypatch adb) → results khớp phase 4
   - **chứng minh test có tác dụng**: xoá tạm 1 import trong `routes_event.py`,
     test phải đỏ. Ghi lại kết quả rồi phục hồi.
6. `pytest` toàn bộ.

## Success Criteria
- [ ] Luồng đủ chạy được không cắm máy (adb monkeypatch)
- [ ] Test gọi qua `TestClient`, **đã chứng minh bắt được lỗi import**
- [ ] Không preview hợp lệ thì không Ghi được
- [ ] Tab UI cũ không bị ảnh hưởng — 459 test cũ xanh
- [ ] Không thêm dependency
- [ ] Cả 2 file mới <200 LOC

## Risk Assessment
- **Open question 2 chặn UX ở đây.** Spec 5 event thì danh sách nút phẳng là đủ;
  60 event thì cần tìm kiếm + nhóm theo screen + thấy tiến độ. Làm bản phẳng trước,
  **hỏi user** trước khi làm phần nhóm — đừng tự đoán.
- Stream logcat sống qua nhiều request. Chặn: giữ process trong `session_state`,
  `/event/stop` phải kill được cả khi client đóng tab; thêm dọn dẹp lúc shutdown.
- `EventRun` + `CheckRun` cùng trong một state → hai tab đè nhau. Chặn: khoá riêng
  từng field, test 2 tab chạy nối tiếp không xoá dữ liệu của nhau.
