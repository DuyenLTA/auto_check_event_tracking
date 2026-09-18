---
phase: 7
title: "Driver tự động lái app theo flow"
status: completed
priority: P2
effort: "8h"
dependencies: [6]
---

# Phase 7: Driver tự động lái app theo flow

## Overview
Tester viết flow một lần, tool tự lái app tới từng trạng thái rồi chèn marker và
chấm event. Thay **cái nút bấm marker**, không thay tầng check.

## Key insight — vì sao phase 1→6 không đổi

Script tự gọi `adb shell log -t USV_MARK` thay vì tester bấm nút. Phía sau
(`event_window` cắt cửa sổ → `checks/event_*` chấm → report) **giống hệt luồng tay**.
Nên phase này thêm vào, không sửa lại.

Và **luồng tay vẫn cần**: `app_shortcut` không lái được trong app (xem Risk), nên nó
là fallback chứ không phải bản bị thay thế.

## Vì sao không thêm dependency

Đã kiểm: **không** có `maestro`, `uiautomator2`, `appium-python-client` trên máy.
Không cần — `DeviceNode` (`models.py:35-47`) đã có `resource_id` · `text` ·
`content_desc` · `bounds_px` · `clickable`. Bấm một element =
`ui_dump.parse_dump()` → tìm node → `input tap` vào tâm `bounds_px`.
`input keyevent` đã verify chạy trong phiên spike.

## Requirements
- Functional: flow YAML mỗi (event, giá trị param) một case; step tối thiểu
  `launch` · `tap_id` · `tap_text` · `tap_desc` · `back` · `wait_text` · `wait` · `swipe`;
  tự chèn marker trước mỗi case; chạy tuần tự nhiều case một lần.
- Non-functional: selector khoá `(resource_id, index_in_parent)`; không `shell=True`;
  test parse flow + phân giải selector chạy được **không cần máy**; chạy thật gắn `device`.

## Architecture
```
event_flow_models.py   FlowStep · FlowCase(expect_event, expect_params, steps) · Flow
event_flow_parse.py    doc YAML -> Flow, validate ten step + selector
event_flow_run.py      chay 1 case: cac step -> chen marker -> tra ve cua so
device_actions.py      tap_node · tap_text · back · wait_text · swipe (qua adb_client)
```
Ví dụ flow:
```yaml
- event: rating_placement_viewed
  cases:
    - params: {placement_name: home}
      reset: fresh_install          # xem open question 5
      steps:
        - launch: {package: "..."}
        - wait_text: "Home"
        - tap_id: btnHome
        - wait: 2s
```
`params` của case chính là giá trị lấy từ cột `Value` của spec — **không khai lại
bằng tay**: phase 2 đã parse ra `allowed`, UI gợi ý sinh sẵn một case rỗng cho từng
giá trị cho phép, tester chỉ điền `steps`.

## Related Code Files
- Create: `src/usv/event_flow_models.py` (~80 LOC)
- Create: `src/usv/event_flow_parse.py` (~150 LOC)
- Create: `src/usv/event_flow_run.py` (~170 LOC)
- Create: `src/usv/device_actions.py` (~150 LOC)
- Modify: `src/usv/adb_client.py` (`input_tap`, `input_keyevent`, `input_swipe`)
- Modify: `src/usv/routes_event.py` (`POST /event/flow`, `POST /event/flow/run`)
- Create: `tests/test_event_flow_parse.py`, `tests/test_device_actions.py`
- Create: `tests/fixtures/flow-rating.yaml`

## Implementation Steps
1. `device_actions.py` — phân giải selector từ dump sẵn có. `tap_text` khớp
   `text` rồi `content_desc`; không thấy → lỗi **nói rõ đã tìm gì và dump có gì gần giống**
   (đừng chỉ báo "not found").
2. `event_flow_parse.py` — validate tên step, từ chối step lạ (cùng lý do
   `check_config.py:4`: gõ sai mà im lặng thì tệ hơn crash). Cảnh báo khi case dùng
   `tap_text` — selector theo chữ vỡ khi đổi ngôn ngữ.
3. `event_flow_run.py` — mỗi case: reset → chèn marker → chạy step → thu cửa sổ.
   Step thất bại → case đó `NOT_TESTED` kèm lý do, **không** `FAIL` (không lái tới
   được thì chưa kết luận được gì về event).
4. Route + UI: nút "Sinh case từ spec" đọc `allowed` của phase 2.
5. Test không cần máy: parse flow, từ chối step lạ, phân giải selector trên
   `tests/fixtures/spike-dump.xml` sẵn có, cảnh báo `tap_text`.
6. Test cần máy → `@pytest.mark.device`.

## Success Criteria
- [x] Flow YAML chạy được tuần tự nhiều case, mỗi case một cửa sổ — `flow_yaml.py`;
  đo trên máy thật 18/09: 2 case, 2 event, cùng một lần mở app
- [x] Step thất bại ra `NOT_TESTED` kèm lý do, không phải `FAIL` — 4 lượt hỏng đầu
      đều ra `Chưa test` kèm tên step chết và số giây đã chờ
- [x] Selector không thấy → lỗi kèm gợi ý node gần giống (`difflib` trong `device_actions`)
- [x] Cảnh báo khi flow dùng `tap_text` — `FlowCase.fragile_steps`, không chặn
- [x] `pytest -m "not device"` xanh khi rút cáp — 678 test
- [x] Không thêm dependency. Mọi module mới <200 LOC

## Risk Assessment
- **Popup rating bị chặn tần suất — RỦI RO LỚN NHẤT CỦA PHASE NÀY.** Rating thường
  show 1 lần / N session. Lái tới `home` 4 lần **không** làm nó hiện 4 lần, nên
  `reset` giữa các case là bắt buộc. Hai đường: `pm clear` (mất data/login) hoặc
  override Remote Config (đã có kỹ thuật: patch `frc_*.json` + throttle, và bẫy
  mirror prefs của SDK Apero). **Xem open question 5 — chưa chốt, đừng tự quyết.**
- **`app_shortcut` không lái được bằng tap trong app.** Đã kiểm: `cmd shortcut` trên
  máy chỉ có `reset-throttling`, không có `list`/`start`. Phải `am start` bằng intent
  đọc từ `shortcuts.xml` của APK. Vòng 1: để case này **cho luồng tay ở phase 6**.
- Flow vỡ khi UI đổi. Chặn: ưu tiên `resource_id`, cảnh báo khi dùng `text`.
- `wait_text` poll dump liên tục tốn thời gian. Chặn: chu kỳ 500 ms, timeout mặc định
  10 s, khai lại được trong flow.

## Đã làm — tầng nền (2026-09-08)

User chốt **override Remote Config, không `pm clear`**. Đã đo trên máy thật trước khi viết.

### Đo được, dùng làm fact

| Việc | Kết quả |
|---|---|
| Máy 99261FFAZ0077C có root? | **Không** — `su: inaccessible or not found` |
| `run-as` với AIP922 (app có event rating) | **Từ chối** — `package not debuggable`. flags không có `DEBUGGABLE` |
| App debuggable trên máy | **17/85** app cài thêm, gồm nhiều app Apero |
| `files/frc_<appId>_firebase_activate.json` | có (`aimusic.aisonggenerator.songmaker`) |
| `shared_prefs/frc_<appId>_firebase_settings.xml` | có — chỗ chứa `last_fetch_time_in_millis` |
| Prefs mirror của SDK Apero | **`tutorial_remote_first_open.xml`** (34 key), không phải `vsl_template4_remote_first_open.xml` như ghi chú cũ |
| Cái chặn popup rating | **`apero_rate_prefs.xml` → `star_vote_on_store=5`** — pref LOCAL, không phải Remote Config |

### Hai điều sửa lại so với ghi chú cũ

1. **Tên file mirror khác nhau tùy app** → phải **dò tìm**, không hardcode được.
   Ghi chú cũ đo trên Pixel 7 + app khác nên tên khác.
2. **Popup rating bị chặn bởi pref local, không bởi RC.** Override RC một mình không
   làm nó hiện lại. Nên có thêm `clear_prefs` xoá đúng một file — không phải `pm clear`,
   giữ nguyên login và data.

### Module đã viết

```
adb_appdata.py           run-as: is_debuggable · app_read/write/list/remove ·
                         device_time_ms                                    136
adb_input.py             tap · swipe · keyevent (danh sách trắng) · text     71
remote_config_patch.py   sửa nội dung file, THUẦN văn bản                   128
remote_config.py         dò file frc_* · override · clear_prefs · verify    189
```

`AdbClient` giờ là `AdbClient(LogcatMixin, InputMixin, AppDataMixin)`.

### Quyết định trong code

- **Phải sửa cả hai file.** Chỉ sửa file giá trị thì lần mở app sau app fetch thật và
  **đè mất sạch** (đo được: 196 → 200 key). Đòn bẩy là throttle 12h của SDK.
- **Không cắt mạng** để chặn fetch — app cần mạng cho ads/API/analytics, cắt là fail oan.
- **Lấy giờ MÁY** (`date +%s%3N`), không lấy giờ host: SDK so mốc với
  `System.currentTimeMillis()` trên máy, lệch giờ là throttle không ăn.
- **Mirror chỉ sửa key ĐÃ CÓ**, giữ nguyên kiểu XML (`boolean`/`string`/`long`).
  Thêm key app không biết là đoán.
- **`keyevent` danh sách trắng** — `POWER`/`SLEEP` làm hỏng cả phiên test.
- **App không debuggable → BLOCKED kèm cách sửa**, không phải FAIL. Chưa đạt được tiền đề
  thì không kết luận gì về app.
- **Verify sau khi mở lại app**: build dev đặt `minimumFetchInterval = 0` thì throttle vô
  hiệu → lệch thì BLOCKED.

### Test
+54 (19 patch nội dung file, 35 validate adb). Tổng **234**, xanh khi không cắm máy.

## Đã làm — driver (user chốt: **1 case = 1 event**)

Một case = một cửa sổ marker = một event mong đợi. `event_window.cut` cắt sẵn theo mốc
nên không phải làm gì thêm cho chuyện đó.

```
device_actions.py      phân giải selector → bấm/quét, gợi ý khi không thấy   130
event_flow_models.py   Step · Reset · FlowCase · Flow                        104
event_flow_run.py      reset → mở lại → verify → chèn mốc → chạy step        195
```

### Điều đáng giá nhất: case chấm chặt hơn spec

Spec nói `placement_name` **được phép** là result/exit_click/app_shortcut/home. Case thì
lái app tới **đúng một** trong bốn chỗ đó, nên nó biết lần này **phải** ra giá trị nào.

Lỗi thật hay gặp: màn Result nhưng app gửi `placement_name=home`. Chấm theo spec là
**PASS** (vì `home` nằm trong danh sách cho phép). Chấm theo case là **FAIL_VALUE**.
Có hai test cạnh nhau chứng minh: `test_case_bat_duoc_loi_ma_SPEC_KHONG_bat_duoc` và
`test_khong_cham_theo_spec_thi_dung_la_PASS`.

Cài bằng cách thêm `expect_params` vào `Window`; `checks/event_params.py` ưu tiên giá trị
case đòi hỏi, không có thì rơi về danh sách cho phép của spec. Tester bấm mốc tay thì
`expect_params` rỗng → hành vi cũ không đổi.

### Quyết định trong code

- **Thứ tự trong một case không đổi được**: sửa RC/xoá prefs → force-stop + mở lại →
  đọc lại verify → chèn mốc → chạy step. App đọc giá trị mới lúc process start.
- **Step thất bại → `not_tested`, KHÔNG phải fail.** Không lái tới được màn cần test thì
  tool chưa đo gì cả; kết luận app thiếu event lúc đó là báo oan. Cùng nguyên tắc `fa_silent`.
- **Reset không ăn → `blocked`.** Gồm cả trường hợp verify thấy RC bị đè (build dev đặt
  `minimumFetchInterval = 0`).
- **Mốc mang NHÃN CASE**, không chỉ tên event: 4 case cùng một event thì không phân biệt
  nhãn là không biết cửa sổ nào ứng với case nào.
- **Gán `expect_params` tra theo NHÃN, không theo thứ tự**: case thất bại không chèn mốc
  nên số cửa sổ ít hơn số case, zip theo thứ tự sẽ gán lệch — lệch còn tệ hơn không gán.
- **Một case blocked không dừng cả lượt** — các case khác vẫn đo được.
- **Không thấy element → gợi ý node gần giống** (`difflib`). Báo "not found" một mình thì
  tester phải tự đọc dump hàng trăm node.
- **Bấm vào TÂM node**, không phải góc trên-trái (góc có thể nằm ngoài vùng bấm được).
- **Quét TRONG node**, không quét cả màn — quét cả màn dễ trúng thanh điều hướng hoặc
  notification shade.
- **Bỏ node `bounds` 0x0**: node ẩn/chưa layout xong, bấm vào đó là bấm vào không khí.

### Test
+24 (12 selector trên dump thật, 12 runner). Tổng **262**, xanh khi không cắm máy.

## Xong (18/09/2026)

Parser đã viết, tên khác kế hoạch: **`flow_yaml.py`** (+ `flow_yaml_write.py` để
`usv-record` ghi ngược ra YAML), không phải `event_flow_parse.py`. Nó **gom hết lỗi**
thay vì dừng ở dòng sai đầu tiên — sửa một dòng rồi chạy lại để gặp dòng sai tiếp theo
là vòng lặp vô nghĩa. `FlowError` chỉ dành cho trường hợp cả file không đọc được.

User nói không cần lo chuyện 5 sao không hiện lại — tiền đề đó họ tự lo, nên không xây
thêm gì quanh `clear_prefs`.

### Lượt chấm thật đầu tiên — 7 lượt, 4 lỗi phải sửa

App `com.nxl.aiphotocreator.aivideogenerator.texttoimage` 2.1.0 (14), Pixel 7
(`29301FDH2006K7`), spec = trang SDK Widget (`widget_view`, `widget_click`).
Kết quả: **2/2 khớp**, artifact `2mkNh33qpZrNk9tVgKHjia`.

| Lượt | Kết quả | Lỗi tìm ra |
|---|---|---|
| 1 | 0/0/2 | flow thiếu hẳn onboarding — app quay lại Choose Language sau mỗi relaunch |
| 2 | 0/0/2 | onboarding **4** trang (đếm `indicatorPageOnboarding`), không phải 3; và bấm ngay sau màn ngôn ngữ thì trang 1 chưa kịp layout |
| 3 | 0/0/2 | `close_ad` bấm luôn `desc='Close'` của popup Add Widget → event bắn xong popup bị tắt, `wait_text` nhìn màn trống |
| 4 | **2/2** | — |
| 5 | 2/2 | ảnh "sau bước cuối" chụp giữa animation; 3 ảnh trùng byte |
| 6 | 0/0/2 | paywall lên **sau** khi hai bước `close_ad` hết hạn chờ |
| 7 | **2/2** | — (chạy từ đúng trạng thái xấu của lượt 6) |

### Bốn bản sửa, và bài học chung của chúng

1. **`ad_close` tách hai bậc mẫu** (`10eb622`). Mẫu chắc (`dismiss-button`,
   `txtSkipAd`, `"Close Billing Screen"`) đóng ngay; mẫu mơ hồ (`"close"`, `"đóng"`,
   `btnClose`, `ivClose`) chỉ đóng khi node có **tổ tiên** là khung quảng cáo. Xét tổ
   tiên chứ không xét cả màn: home app nào cũng có thể có native ad ở dưới.
2. **Mở app đúng một lần, sau mốc** (`2a861db`). Ba tầng cùng force-stop + launch:
   `logcat_stream.start`, `reset.relaunch` (mặc định `True`), và step `launch`. Mốc chèn
   **sau** reset nên hai lần mở đầu nằm ngoài cửa sổ — với event "1 lần/session" thì
   event cháy ở đó và case báo "không bắn": **FAIL oan**, không phải `Chưa test`.
3. **`wait_text` tự dọn màn chắn** (`4ae2ee0`). Màn chắn lên sau khi `close_ad` hết hạn
   chờ thì ghim thêm một `close_ad` chỉ đẩy vấn đề xuống dưới. Vòng chờ đã poll cây UI
   rồi, nên thấy nút đóng **bậc chắc** thì bấm, gia hạn thêm `timeout`, tối đa 3 màn.
   Chỉ bậc chắc: màn đang chờ có nút `Close` của chính nó.
4. **Ảnh bằng chứng** (`4ae2ee0`). Chờ `SHOT_SETTLE = 1s` trước tấm "sau bước cuối"
   (bottom sheet hệ thống còn đang bay ra); hai tấm giống hệt từng byte thì giữ một,
   caption gộp thành "(màn không đổi)".

Bài học chung: **không màn nào trong app này lên đúng giờ.** Mọi bước ghim cứng thứ tự
và thời gian đều là xúc xắc; chốt chặn phải là "thấy gì thì xử cái đó", không phải
"đến giây thứ N thì chắc màn X đang hiện".

### Chưa làm

- Dedupe ảnh chỉ xét **trong cùng một case**; hai case liền nhau vẫn giữ 2 bản của cùng
  một tấm (đo được 212 KB × 2). Xét chéo case thì report phải chỉ "xem tấm ở case trên".
- Popup Add Widget **không** bị `pm_clear`/`clear_prefs` nào chạm tới trong luồng hiện
  tại; nó hiện lại được vì widget chưa add (`dumpsys appwidget`: 0 instance). Case nào
  bấm tới "Thêm vào màn hình chính" thật thì tiền đề cháy — chưa xử.
