---
phase: 7
title: "Driver tự động lái app theo flow"
status: in-progress
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
- [ ] Flow YAML chạy được tuần tự nhiều case, mỗi case một cửa sổ
- [ ] Step thất bại ra `NOT_TESTED` kèm lý do, không phải `FAIL`
- [ ] Selector không thấy → lỗi kèm gợi ý node gần giống
- [ ] Cảnh báo khi flow dùng `tap_text`
- [ ] `pytest -m "not device"` xanh khi rút cáp
- [ ] Không thêm dependency. Cả 4 file mới <200 LOC

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

## Còn lại — chờ file test case của user

User sẽ đưa file test case, nên **chưa viết** `event_flow_models` / `event_flow_parse` /
`event_flow_run` / `device_actions`: tự nghĩ ra định dạng flow rồi phải viết lại là lãng phí.

User cũng nói không cần lo chuyện 5 sao không hiện lại — tiền đề đó họ tự lo, nên không
xây thêm gì quanh `clear_prefs`.
