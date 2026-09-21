# flows/ — đường đi để lái app

Một file cho một app: `flows/<package>.yaml`. `check` đọc đúng file này, không tự mò UI.
Chưa có file → case ra `NOT_TESTED` kèm "chưa có flow", **không phải FAIL**.

Format chuẩn: [`example.yaml`](example.yaml). Parser: `src/usv/flow_yaml.py`.

## Quy tắc

- **Một case = một event.** Một case lái tới đúng một trạng thái rồi chờ một event. Cham 2 event → viết 2 case.
- `expect_params` là giá trị **lần này phải ra**, khác với spec (spec nói "được phép những giá trị nào").
- Selector dùng **đúng một** trong `resource_id` | `text` | `desc`. Hai trường → lỗi.
  `index` = node thứ mấy trong số các node khớp, tính từ 0 (nhiều card dùng chung một `resource_id`).
- Selector theo `text`/`desc` chạy được nhưng **vỡ khi app đổi ngôn ngữ** → report đánh dấu `fragile`.
- **Chỉ viết case cho vị trí app thật sự có.** Vị trí không tồn tại mà vẫn viết case thì ra `FAIL`,
  đọc như app thiếu event. Ví dụ `result` của SDK Rating là màn trả kết quả gen ảnh/video —
  app học/tiện ích không có màn đó, bỏ case và ghi comment nói vì sao bỏ. Nhận biết lúc record:
  màn home có nút Generate/Create hay ô nhập prompt không.
- `reset` không có `pm clear` (xoá sạch login). Reset đi qua Remote Config + xoá vài file prefs.

## Step

| kind | Trường bắt buộc | Việc |
|---|---|---|
| `launch` | — | force-stop rồi mở lại app |
| `tap` | selector | bấm vào giữa node |
| `swipe` | selector | quét trên node; `direction` = up/down/left/right (mặc định up) |
| `type` | `text` | gõ chữ vào ô đang focus (tap vào ô trước) |
| `key` | `text` | keyevent, vd `KEYCODE_BACK` |
| `wait` | `seconds` | chờ cứng |
| `wait_text` | `text` | chờ tới khi chữ xuất hiện, `timeout` mặc định 10s |

## Lỗi

Sai cú pháp YAML / không có file → dừng ngay, nói tên file.
Sai một dòng (thiếu `event`, selector hai trường, `kind` lạ) → gom hết vào `Flow.errors`,
mỗi dòng chỉ rõ `case N (event), step M` — sửa một lượt, không phải chạy lại từng lỗi.
Case nào sai thì **bỏ hẳn** case đó, không chạy dở.
