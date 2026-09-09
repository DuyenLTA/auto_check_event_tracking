# Auto Check Event Tracking

Đối chiếu **event Firebase Analytics app Android thật bắn ra** với **bảng spec event tracking**, ra report pass/fail và note rõ sai ở đâu.

> Đối chiếu **UI** với design Figma/pen.dev là tool khác: [ui-spec-verifier](https://github.com/DuyenLTA/ui-spec-verifier).

## Kiểm được gì

Với mỗi dòng trong bảng spec:

| Tiêu chí | Kết luận |
|---|---|
| Event có bắn ở bước đó không | `Khớp` / `Thiếu` |
| Bắn trùng nhiều lần trong một bước | `Bắn trùng` |
| Param spec khai mà app không gửi | `Thiếu` |
| Giá trị ngoài danh sách spec cho phép | `Sai giá trị` |
| Kiểu: spec `Number` mà app gửi chữ | `Sai kiểu` |
| App gửi param spec không khai | `Thừa param` |
| Kiểu: spec `String` mà app gửi số | `Chưa kết luận` — logcat in Long `3` và chuỗi `"3"` y hệt nhau |
| Chưa đánh dấu bước nào cho event | `Chưa test` — **không** tính là fail |
| Event app bắn mà spec không khai | `Spec không khai` — **không** tính là fail |

## Cần gì trước khi chạy

1. **Python 3.12+** (`python3 --version`)
2. **adb** — cài Android platform-tools. Không nằm trong PATH thì:
   ```bash
   export ADB_PATH=$HOME/Android/Sdk/platform-tools/adb
   ```
3. **Điện thoại Android** bật *USB debugging*, cắm cáp, bấm **Allow** trên máy.
   Kiểm tra: `adb devices` phải hiện `device` (không phải `unauthorized`).

Không cần token nào.

## Cách nó đọc được event

Bật log Firebase rồi đọc logcat:

```bash
adb shell setprop log.tag.FA-SVC VERBOSE
adb logcat -s FA-SVC:V USV_MARK:I
```

Event in ra dạng:

```
V/FA-SVC: Logging event: origin=app,name=rating_placement_viewed,
          params=Bundle[{placement_name=home, ga_event_origin(_o)=app}]
```

Ba điều đã đo trên máy thật, không phải suy luận:

- Event nằm ở tag **`FA-SVC`**, không phải `FA`. Tag `FA` in `Logging telemetry` nhưng **không kèm params**.
- `origin` phân loại nguồn: `app` (app tự gọi — phạm vi spec), `auto` (`screen_view`, `session_start`), `am` (nội bộ App Measurement).
- Param hệ thống mang tiền tố **`ga_`**, in dạng `ga_screen_class(_sc)=...`. Chúng có ở 42/42 event nên **luôn bị lọc** trước khi chấm "thừa param".

⚠️ `setprop` **không sống qua reboot**, và app phải **khởi động lại** sau khi set (property đọc lúc process start). Tool tự làm cả hai việc này mỗi lần Ghi.

## Ràng buộc lúc bắn

Tool không đoán event nào thuộc bước nào. Tester đánh dấu bước, tool chèn một dòng mốc vào chính logcat:

```bash
adb shell log -t USV_MARK "rating_placement_viewed | Khi màn rating hiển thị"
```

Dòng mốc nằm **chung timeline** với event nên không phải đồng bộ giờ giữa máy tính và điện thoại. **Một nút một bước**: mốc của bước sau chính là điểm kết của bước trước.

## Bảng spec

Dán trực tiếp từ Excel/Google Sheet (TSV). Cột bắt buộc: `Event_Name`, `Params`, `Value Type`.

```
Screen Name  Event_Name               Triggered              Params          Param Description  Value Type  Value                                   Value Description
Home         rating_placement_viewed  Khi màn rating hiện    placement_name                     String      result, exit_click, app_shortcut, home  Vị trí màn rating
Home         rating_star_clicked      Khi user click rate    star_value                         Number      1,2,3,4,5                               Số sao
                                                             placement_name                     String      result, exit_click, app_shortcut, home  Vị trí
```

- Cột `Event_Name` để trống = param tiếp của event phía trên.
- Cột `Value` để trống = free-form, chỉ kiểm có mặt + kiểu.
- Cột `Triggered` là văn xuôi cho người đọc, làm nhãn nút cho tester — **không** chạm verdict.

**Một hàng một dòng.** Hàng sai số cột bị báo lỗi kèm số dòng chứ không tự ghép lại: ghép theo số cột làm **mất ô rỗng** ở điểm gãy và sinh ra spec sai mà không báo gì.

## Chạy

```bash
./start.sh                    # http://127.0.0.1:8000
PORT=9000 ./start.sh          # đổi cổng
USV_NO_BROWSER=1 ./start.sh   # không tự mở browser
```

Lần đầu mất ~30 giây (tự tạo môi trường ảo + cài thư viện). Các lần sau ~1 giây.

Bốn bước trên giao diện:

1. **Dán bảng spec** → bấm *Đọc bảng*. Hàng nào sai số cột thì báo kèm số dòng. Còn lỗi thì không cho Ghi.
2. **Chọn máy và app** → *Bắt đầu ghi*. Tool tự bật log Firebase, tắt rồi mở lại app.
3. **Thao tác trên máy** rồi bấm *Dừng ghi*.
4. **Chấm** → xem report HTML hoặc tải xlsx.

### Hai chế độ

| | Chế độ nhanh (mặc định) | Đánh dấu từng bước |
|---|---|---|
| Cách làm | bấm Ghi rồi thao tác tự do | bấm nút của bước sắp làm **rồi mới** thao tác |
| Event có bắn / param đúng | ✅ | ✅ |
| Bắn **đúng lúc** | ❌ không có biên bước để so | ✅ |
| Bắn trùng | tắt — phiên dài vào ra một màn thì bắn lại là đúng | ✅ theo từng bước |

Chế độ đánh dấu: nút nhóm theo màn, có ô lọc và dấu đã-bấm. Mốc của bước sau là điểm kết của bước trước — không có nút Xong.

Report và xlsx **luôn ghi rõ** đã chạy chế độ nào, để người đọc không tưởng đã kiểm cả thời điểm.

## Gọi từ Python

Không cần giao diện thì dùng trực tiếp:

```python
from usv import event_check_runner, report_event_html
from usv.check_config import load
from usv.event_spec_parse import parse_paste
from usv.event_window import cut_log

spec = parse_paste(open("spec.tsv").read())
assert not spec.errors, spec.errors
windows = cut_log(open("capture.log").read())
results, summary = event_check_runner.run(spec, windows, load())
open("report.html", "w").write(
    report_event_html.build(spec, results, summary, package="com.x"))
```

## Test

```bash
.venv/bin/python -m pytest -m "not device"   # không cần cắm máy
.venv/bin/python -m pytest -m device         # cần máy thật
```

## Cấu hình

`config/event-check-rules.yaml` — bật/tắt từng check. Sửa xong có hiệu lực ngay, không phải khởi động lại.

## Nguyên tắc

1. **`Chưa test` và `Spec không khai` không bao giờ tính vào fail.** Tool chưa đo được thì không kết luận về app. Fail oan một loạt là cách nhanh nhất để tester bỏ không dùng tool nữa.
2. **Không verify được thì nói không verify được**, không pass giả.
3. Sai cú pháp config hay spec thì **báo lỗi rõ** chứ không chạy bừa — kiểu im lặng nguy hiểm hơn crash.
