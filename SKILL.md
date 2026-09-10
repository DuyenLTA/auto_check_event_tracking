---
name: auto-check-event-tracking
description: >
  Đối chiếu event Firebase Analytics mà app Android thật bắn ra với bảng spec event
  tracking, ra report pass/fail kèm note sai ở đâu (thiếu event, bắn trùng, thiếu param,
  sai giá trị, sai kiểu, thừa param). Chạy qua web UI local hoặc gọi trực tiếp từ Python.
  Kích hoạt khi user nói về: check event tracking, verify event Firebase, đối chiếu event
  với spec, nạp spec từ link Confluence, log FA-SVC, logcat event, report event tracking,
  auto check event.
  Cần adb + máy Android thật cắm cáp, bật USB debugging. Không cần token.
  Không dùng cho đối chiếu UI với design Figma — đó là tool ui-spec-verifier.
---

# Auto Check Event Tracking

Repo gốc: https://github.com/DuyenLTA/auto_check_event_tracking

## Đọc trước khi làm gì

`README.md` trong thư mục skill này là tài liệu đầy đủ: bảng verdict, format bảng spec
(TSV dán từ Excel), cách tool đọc logcat, ràng buộc `setprop` không sống qua reboot,
và nguyên tắc "không verify được thì nói không verify được".

## Chạy web UI

Linux/macOS:

```bash
cd ~/.claude/skills/auto-check-event-tracking
./start.sh                    # http://127.0.0.1:8000
PORT=9000 ./start.sh          # đổi cổng
USV_NO_BROWSER=1 ./start.sh   # không tự mở browser
```

Lần đầu ~30s (tự tạo venv + cài lib), sau đó ~1s.

**Windows**: `./start.sh` KHÔNG chạy được — nó tìm `.venv/bin/python`, còn venv trên
Windows đặt ở `.venv/Scripts/`. Dùng `scripts/run-windows.py`:

```bash
cd ~/.claude/skills/auto-check-event-tracking
.venv/Scripts/python.exe scripts/run-windows.py 8000
```

Rồi tự mở http://127.0.0.1:8000. Script này làm hai việc mà `start.sh` không làm
được trên Windows: đặt `ProactorEventLoop` (uvicorn mặc định dùng
`SelectorEventLoop`, loop đó không tạo được subprocess nên **mọi lệnh adb đổ
`NotImplementedError`**), và đọc file `.env` ở gốc repo (`start.sh` không đọc
`.env`, mà Windows thì không có `~/.bashrc` để `export`).

Lần đầu cần tự cài: `.venv/Scripts/python.exe -m pip install -e .`

Ba bước trên UI:

1. **Nạp spec** — dán link Confluence rồi bấm *Đọc từ link*, hoặc mở phần dán TSV tay.
   Còn lỗi thì không cho Ghi.
2. **Máy và app** — dán package name → *Bắt đầu ghi*, thao tác trên máy, rồi *Dừng ghi*.
   Máy tool tự nhận. Luôn ghi từ lúc app mở: `setprop log.tag.FA-SVC` chỉ ăn từ lần
   khởi động sau đó, nên nếu tự mở app thì mở **sau** khi bấm Ghi.
3. **Chấm** → report HTML.

Đánh mốc từng bước là **tuỳ chọn**: có bấm mốc thì chấm theo cửa sổ từng bước, không
bấm mốc nào thì tool tự chấm cả phiên. Không còn ô tick chế độ, cũng không xuất xlsx.

## Gọi từ Python

Xem mục "Gọi từ Python" trong `README.md` — dùng `event_check_runner.run()` với
`parse_paste()` cho spec và `cut_log()` cho log đã capture.

## Cấu hình

`config/event-check-rules.yaml` — bật/tắt từng check, có hiệu lực ngay.

Nạp spec từ link Confluence cần hai biến môi trường; thiếu thì dùng đường dán TSV tay:

```bash
export CONFLUENCE_BASE_URL=https://confluence.cong-ty.vn
export CONFLUENCE_TOKEN=<personal access token>
```

Nên dùng đường Confluence hơn dán tay: bảng thật gộp ô (`rowspan`) Event_Name cho nhiều
dòng param, đếm ô theo dấu tab sẽ báo lỗi oan trên bảng hoàn toàn hợp lệ.

## Test

```bash
# Windows
.venv/Scripts/python.exe -m pytest -m "not device"   # không cần cắm máy
.venv/Scripts/python.exe -m pytest -m device         # cần máy thật

# Linux/macOS
.venv/bin/python -m pytest -m "not device"
```

## Cập nhật skill

Skill này là git clone có hai remote, nội dung hai bên giữ giống nhau 100%:
`origin` = DuyenLTA/auto_check_event_tracking (gốc), `mine` = LuuThiAnDuyen/check_event_track.

```bash
cd ~/.claude/skills/auto-check-event-tracking
git pull origin main      # hoặc: git pull mine main
```

## Tự publish artifact sau mỗi lượt chấm

Tool không publish artifact được (chạy ở `127.0.0.1`, không có đường tới claude.ai —
xem `artifact_link.py`), nên việc publish phải do Claude làm. `scripts/watch-cham-moi.py`
lo phần máy làm được: dò tool, thấy lượt chấm mới chưa publish thì tải report về
`out/artifact-page.html` rồi in một dòng ra stdout để Claude biết mà publish.

```bash
.venv/Scripts/python.exe -u scripts/watch-cham-moi.py
```

Publish xong, Claude `POST /event/artifact` kèm `generated_at` của lượt đó; nút trên
trang tự đổi thành **Link artifact**. Republish cùng file giữ nguyên URL, nên link
gửi cho team chỉ cần nhớ một lần.
