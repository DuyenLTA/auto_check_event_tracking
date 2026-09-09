---
phase: 6
title: "Route + tab web"
status: completed
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
- [x] Luồng đủ chạy được không cắm máy (adb monkeypatch)
- [x] Test gọi qua `TestClient`, **đã chứng minh bắt được lỗi import**
- [x] Không preview hợp lệ thì không Ghi được
- [x] Tab UI cũ không bị ảnh hưởng — 459 test cũ xanh
- [x] Không thêm dependency
- [x] Cả 2 file mới <200 LOC

## Risk Assessment
- **Open question 2 chặn UX ở đây.** Spec 5 event thì danh sách nút phẳng là đủ;
  60 event thì cần tìm kiếm + nhóm theo screen + thấy tiến độ. Làm bản phẳng trước,
  **hỏi user** trước khi làm phần nhóm — đừng tự đoán.
- Stream logcat sống qua nhiều request. Chặn: giữ process trong `session_state`,
  `/event/stop` phải kill được cả khi client đóng tab; thêm dọn dẹp lúc shutdown.
- `EventRun` + `CheckRun` cùng trong một state → hai tab đè nhau. Chặn: khoá riêng
  từng field, test 2 tab chạy nối tiếp không xoá dữ liệu của nhau.

## Lệch khỏi plan khi làm

**Thêm 2 module ngoài dự kiến.** Plan ghi `routes_event.py` + `web/event.js`. Thực tế:
- `event_state.py` (82 LOC) — `session_state.py` đã bị bỏ khi tách repo nên phải có
  chỗ giữ spec/phiên ghi/kết quả. Có `stage` để UI biết bật tắt nút nào; suy từ các
  field khác cũng được nhưng logic sẽ rải ra cả hai phía rồi lệch nhau.
- `routes_device.py` (53 LOC) — cũng bị bỏ khi tách repo, mà UI cần chọn máy/app.
- `routes_event_report.py` (74 LOC) — tách khỏi `routes_event.py` để dưới 200 LOC.
- Web tách 3 file: `event.js` (196) · `event-marks.js` (81) · `event-render.js` (77).
  Một file là 255 LOC, vượt ngưỡng.

**Bỏ câu chưa chốt số 2 (spec bao nhiêu event).** User hỏi lại nó ảnh hưởng gì đến
tool. Kiểm bằng grep: không có `limit` / `MAX_` / `paginat` / cắt bớt nào phụ thuộc
số event ở bất kỳ tầng nào. Nên đã làm bản **nhóm theo màn + ô lọc + dấu đã-bấm**,
chạy tốt cho cả 5 và 60 event. Câu đó không phải câu hỏi.

**Sửa 2 bug tìm được khi làm phase này** — cả hai đều thuộc loại "test xanh mà vẫn hỏng":

1. `exporter.py` còn tham chiếu `summary.unmatched`, field đã bỏ khi tách repo →
   `AttributeError` khi tải xlsx. Không ai thấy vì `test_report_export.py` đã bị xoá
   nên không còn test nào gọi `exporter.build()`. Đã sửa header + hàng tổng cho domain
   event, và `test_xlsx_tai_duoc_sau_khi_cham` khoá lại (đã chứng minh: đưa
   `summary.unmatched` trở lại thì test đỏ đúng `AttributeError` đó).

2. `start.sh` kiểm `import PIL, multipart` — hai thư viện đã bỏ khỏi dependency →
   **cài lại mỗi lần chạy**. Và không có chỗ nào phát hiện `usv` trỏ sai repo: đổi tên
   thư mục dự án làm file `.pth` của editable install trỏ vào đường dẫn cũ, uvicorn nạp
   **nguyên một package khác** trong khi pytest vẫn xanh (pytest lấy `src` qua
   `pythonpath` trong pyproject). Đã gặp thật: server serve tool UI, mọi route 404.
   Thêm guard so `usv.__file__` với `src/` của chính repo, cài lại vẫn sai thì báo kèm
   lệnh `pip uninstall`.

**Smoke test thật, không chỉ TestClient.** Chạy `./start.sh` rồi curl từng endpoint:
`/` 200 · `/static/*` 200 · `/event/state` · `/event/config` · `/devices` (thấy máy
thật Pixel_4) · `POST /event/spec` (parse spec thật) · `/event/report` 409 khi chưa
chấm. Đây là bước bắt được bug số 2 — 180 test không bắt được.

## Bổ sung: chế độ nhanh (2026-09-09)

User chốt cách dùng thực tế: *"tôi đưa nội dung bảng, tôi tự bấm vào màn đấy rồi bạn
check log nó đúng đủ là được cho nhanh"*. Nên thêm chế độ **không đánh dấu từng bước**,
và để làm **mặc định** — đó là cách sẽ dùng hằng ngày.

`event_window.whole_session()` gom cả phiên thành **một cửa sổ cho mỗi event trong spec**.
Không có nó thì cắt theo mốc ra 0 cửa sổ và mọi dòng thành *chưa test*.

**Bắt buộc tắt `duplicate` ở chế độ này** — một phiên dài vào ra cùng một màn thì event
đó bắn lại là **đúng**, bật lên là báo oan hàng loạt. Làm bằng
`CheckConfig.with_option()` (bản sao, không sửa file config). Có test chứng minh cả hai
chiều: tắt thì `track_ad_request` bắn 17 lần không thành fail, bật thì thành fail — nếu
test chỉ kiểm chiều tắt thì nó xanh cả khi `whole_session` hỏng.

**Report và xlsx đều phải nói ra.** Không nói thì người đọc tưởng đã kiểm cả thời điểm
bắn — mà đó chính là thứ chế độ này đánh đổi đi. Callout trên HTML, dòng cảnh báo trong
sheet tổng của xlsx.

### Đánh đổi, ghi rõ để sau này không nhầm

| | chế độ nhanh | đánh dấu từng bước |
|---|---|---|
| event có bắn / param đúng | ✅ | ✅ |
| bắn đúng lúc | ❌ | ✅ |
| bắn trùng | tắt | ✅ theo bước |

### Web tách thêm 2 file
`event.js` lên 217 LOC nên tách `event-api.js` (22) và `event-device.js` (52).
Còn `event.js` 162 · `event-marks.js` 81 · `event-render.js` 82.

### Test
+21 (12 chế độ nhanh, 9 qua route). Tổng **282**.
