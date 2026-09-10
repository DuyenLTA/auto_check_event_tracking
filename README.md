# Auto Check Event Tracking

Đối chiếu **event Firebase Analytics app Android thật bắn ra** với **bảng spec event tracking**, ra report pass/fail và note rõ sai ở đâu.

> Đối chiếu **UI** với design Figma/pen.dev là tool khác: [ui-spec-verifier](https://github.com/DuyenLTA/ui-spec-verifier).

## Kiểm được gì

Với mỗi dòng trong bảng spec:

| Tiêu chí | Kết luận |
|---|---|
| Event có bắn ra trong phiên ghi không | `Khớp` / `Thiếu` |
| Param spec khai mà app không gửi | `Thiếu` |
| Giá trị ngoài danh sách spec cho phép | `Sai giá trị` |
| Kiểu: spec `Number` mà app gửi chữ | `Sai kiểu` |
| App gửi param spec không khai | `Thừa param` |
| Kiểu: spec `String` mà app gửi số | `Chưa kết luận` — logcat in Long `3` và chuỗi `"3"` y hệt nhau |
| Số lần bắn | in ra ở cột *App gửi* (`bắn 2 lần: …`) — **không** chấm fail, xem dưới |

**Bắn trùng không bị chấm fail.** Một phiên ghi dài vào ra cùng một màn thì
event đó bắn lại là đúng, tool không biết bạn vào mấy lần nên không kết luận
thay bạn được. Nó in số lần bắn kèm giờ, bạn tự so với số lần mình thật sự vào
màn đó.

Chỉ chấm **event có trong bảng spec**. Event khác app bắn ra (`ad_load`,
`track_ad_request`, `screen_view`…) không được liệt kê: một phiên thật có hàng
chục event như vậy, in hết ra thì thứ cần đọc bị chìm.

## Cần gì trước khi chạy

1. **Python 3.12+** (`python3 --version`)
2. **adb** — cài Android platform-tools. Không nằm trong PATH thì:
   ```bash
   export ADB_PATH=$HOME/Android/Sdk/platform-tools/adb
   ```
3. **Điện thoại Android** bật *USB debugging*, cắm cáp, bấm **Allow** trên máy.
   Kiểm tra: `adb devices` phải hiện `device` (không phải `unauthorized`).

Không cần token gì để chấm. Chỉ khi nạp spec **bằng link Confluence** mới cần
hai biến môi trường — xem mục *Bảng spec*; dán tay thì không cần.

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

## Vì sao không chia phiên theo từng bước

Bản đầu có panel đánh dấu: tester bấm nút của bước sắp làm, tool chèn một dòng
mốc `USV_MARK` vào chính logcat rồi cắt phiên thành các cửa sổ theo mốc đó.

Đã bỏ. Mốc do **tester** bấm còn event do **app** bắn, hai cái không đồng bộ
được. Đo trên máy thật: app bật màn daily checkin ngay khi mở, event
`daily_checkin_screen_view` bắn lúc `16:54:10` trong khi mốc đầu tiên bấm được
là `16:54:15` — event rơi ra ngoài mọi cửa sổ và bị báo `Thiếu`. Cùng app cùng
log, không bấm mốc thì `2 pass`, bấm mốc thì `1 pass 1 fail`. Một verdict đổi
theo thứ tự bấm nút thì không dùng được.

Nên giờ tool chấm trên **cả phiên ghi**: mất khả năng kết luận "bắn đúng lúc",
đổi lại không còn fail oan. Cơ chế mốc vẫn còn ở tầng API (`POST /event/mark`)
cho kịch bản tự động, chỉ là giao diện không dùng.

## Bảng spec

Hai cách nạp. Cột bắt buộc ở cả hai: `Event_Name`, `Params`, `Value Type`.

### Cách 1 — link Confluence (nên dùng)

Dán link trang có bảng event tracking rồi bấm *Đọc từ link*. Tool tự tìm bảng
trên trang bằng **tên cột**, không theo thứ tự — một trang thường có thêm bảng
Requirements và List Remote Key, lấy nhầm bảng là chấm sai toàn bộ.

Hơn hẳn dán tay ở chỗ **ô gộp** (`rowspan`). Bảng thật hay gộp ô Event_Name cho
nhiều dòng param; khi đó hàng thứ hai chỉ có 2 thẻ `<td>` trong khi bảng rộng 8
cột. Đếm ô theo dấu tab sẽ ra "2 cột, cần 8" và báo lỗi oan trên một bảng hoàn
toàn hợp lệ. Lấy ranh giới ô từ lưới HTML thì chuyện đó biến mất.

Cần hai biến môi trường (đặt trong `~/.bashrc`):

```bash
export CONFLUENCE_BASE_URL=https://confluence.cong-ty.vn
export CONFLUENCE_TOKEN=<personal access token>
```

Nhiều trang Confluence **không** chứa bảng mà chỉ trỏ sang Google Sheet — tool
không đọc được Sheet, lúc đó dùng cách 2.

### Cách 2 — dán TSV

Dán trực tiếp từ Excel/Google Sheet.

```
Screen Name  Event_Name               Triggered              Params          Param Description  Value Type  Value                                   Value Description
Home         rating_placement_viewed  Khi màn rating hiện    placement_name                     String      result, exit_click, app_shortcut, home  Vị trí màn rating
Home         rating_star_clicked      Khi user click rate    star_value                         Number      1,2,3,4,5                               Số sao
                                                             placement_name                     String      result, exit_click, app_shortcut, home  Vị trí
```

- Cột `Event_Name` để trống = param tiếp của event phía trên.
- Cột `Value` để trống = free-form, chỉ kiểm có mặt + kiểu.
- Cột `Triggered` là văn xuôi cho người đọc, in kèm tên event trong report — **không** chạm verdict.

**Một hàng một dòng.** Hàng sai số cột bị báo lỗi kèm số dòng chứ không tự ghép lại: ghép theo số cột làm **mất ô rỗng** ở điểm gãy và sinh ra spec sai mà không báo gì.

## Chạy

```bash
./start.sh                    # http://127.0.0.1:8000
PORT=9000 ./start.sh          # đổi cổng
USV_NO_BROWSER=1 ./start.sh   # không tự mở browser
```

Lần đầu mất ~30 giây (tự tạo môi trường ảo + cài thư viện). Các lần sau ~1 giây.

Ba bước trên giao diện:

1. **Nạp spec**: dán link Confluence → *Đọc từ link*; hoặc mở phần dán tay. Hàng nào sai số cột thì báo kèm số dòng. Còn lỗi thì không cho Ghi.
2. **Máy và app**: dán package name → *Bắt đầu ghi*, thao tác trên máy, rồi *Dừng ghi* (hai nút nằm cạnh nhau). Máy thì tool tự nhận, cắm giữa chừng cũng thấy. Luôn ghi **từ lúc app mở**: tìm thấy app trên máy thì tool tự tắt–mở lại; không tìm thấy thì vẫn ghi và bạn tự mở app (mở **sau** khi bấm Ghi — `setprop log.tag.FA-SVC` chỉ ăn từ lần khởi động sau đó). Không chặn, vì tool không tự mở bừa: `monkey` với app không tồn tại in `No activities found to run` mà trả exit 0, mở thất bại trong im lặng rồi ghi log của app đang mở sẵn.
3. **Chấm** → xem report HTML.

Giữa lúc ghi, ô trạng thái đếm số dòng log đọc được. Máy rớt khỏi USB là báo
ngay tại đó chứ không đợi tới lúc Chấm — đã từng mất 70 phút vì im lặng.

## Gọi từ Python

Không cần giao diện thì dùng trực tiếp:

```python
from usv import event_check_runner, report_event_html
from usv.check_config import load
from usv.event_spec_parse import parse_paste
from usv.event_window import whole_session
from usv.fa_event_parse import parse_log

spec = parse_paste(open("spec.tsv").read())
assert not spec.errors, spec.errors

events = [e for e in parse_log(open("capture.log").read())[0] if e.from_app]
windows = whole_session(tuple(e.name for e in spec.events), events)
config = load().with_option("event_presence", "duplicate", False)
results, summary = event_check_runner.run(
    spec, windows, config, session_events=tuple(events))
open("report.html", "w").write(
    report_event_html.build(spec, results, summary, package="com.x", quick=True))
```

## Test

`./start.sh` chỉ cài thư viện để **chạy** tool. Muốn chạy test thì cài thêm:

```bash
.venv/bin/python -m pip install -e ".[dev]"   # lần đầu
.venv/bin/python -m pytest                    # 424 test, ~1 giây
```

Cả suite chạy **không cần cắm máy** — adb được thay bằng bản giả trong test.
Marker `device` để dành cho test cần điện thoại thật (`pytest -m device`,
`addopts` trong `pyproject.toml` mặc định loại chúng ra); hiện chưa có test nào
mang marker đó.

Ba việc test bắt được mà `curl` không bắt được, nên đừng bỏ:

| Kiểm | Bắt được gì |
|---|---|
| `scripts/check-web-loads.js` | JS lỗi lúc nạp — file vẫn trả 200 nhưng trang không khởi tạo được |
| `test_web_html_balanced.py` | thẻ HTML chưa đóng làm lệch layout; browser không báo lỗi |
| `test_readme_vi_du_chay_duoc.py` | đoạn code trong README này lệch API |

## Cấu hình

`config/event-check-rules.yaml` — bật/tắt từng check. Sửa xong có hiệu lực ngay, không phải khởi động lại.

## Nguyên tắc

1. **`Chưa kết luận`, `Chưa test` và `Spec không khai` không bao giờ tính vào fail.** Tool chưa đo được thì không kết luận về app. Fail oan một loạt là cách nhanh nhất để tester bỏ không dùng tool nữa.
2. **Không verify được thì nói không verify được**, không pass giả.
3. Sai cú pháp config hay spec thì **báo lỗi rõ** chứ không chạy bừa — kiểu im lặng nguy hiểm hơn crash.
