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
- [x] Flow YAML chạy được tuần tự nhiều case, mỗi case một cửa sổ
- [x] Step thất bại ra `NOT_TESTED` kèm lý do, không phải `FAIL`
- [x] Selector không thấy → lỗi kèm gợi ý node gần giống
- [x] Cảnh báo khi flow dùng `tap_text`
- [x] `pytest -m "not device"` xanh khi rút cáp
- [x] Không thêm dependency. Cả 4 file mới <200 LOC

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

## Đã làm — parser flow (2026-09-08)

`event_flow_parse` xong. Định dạng lấy từ ví dụ YAML ở mục Architecture phía trên;
`Flow`/`FlowCase`/`Step` đã có sẵn nên parser khớp models, không phát minh từ vựng mới.

```
event_flow_validate.py     kiểm dữ liệu thô: khoá lạ, chuỗi, thời gian, index    64
event_flow_step_parse.py   một phần tử `steps` -> Step                          167
event_flow_parse.py        đi cấu trúc event/case, gom lỗi                      193
routes_event.py            + POST /event/flow (chỉ đọc, không chạm máy)         197
```

Tách 3 file vì bản một-file chạm 215 LOC. Ranh giới: kiểm dữ liệu thô (cả hai file
kia dùng) / từ vựng step (dài ra khi thêm thao tác) / cấu trúc flow (không đổi).

### Nguyên tắc: sai âm thầm ở parser ra kết luận sai về app

Vòng đầu parser bỏ qua khoá lạ. Code review bắt được 3 đường sai âm thầm, mỗi đường
kết thúc bằng một verdict sai — không phải bằng một message lỗi:

| Gõ sai | Nếu bỏ qua âm thầm | Kết quả |
|---|---|---|
| `param` thiếu `s` | `expect_params` rỗng | **PASS giả** — mất đúng khả năng bắt "màn Result báo `placement_name=home`" |
| `indx` thay `index` | selector về index 0 | bấm card khác → lái sang màn khác → **FAIL oan** |
| `steps` khai hai lần | yaml lấy cái sau | case chạy thiếu bước → **FAIL oan** |

Nên giờ **mọi mapping đều kiểm khoá lạ** (`unknown_keys`), dùng chung một helper cho
case · reset · selector · swipe · wait_text.

### Quyết định trong code

- **Case có một step không đọc được → bỏ CẢ case.** Chạy case thiếu bước còn tệ hơn
  không chạy: nó ra kết luận về app dựa trên đường đi không phải đường tester mô tả.
- **bool YAML không nháy → báo lỗi, không tự đổi.** `true` cho ra `str(True)` = `'True'`,
  lệch với `'true'` máy giữ → `prepare()` trả BLOCKED kèm message quy tội "build đặt
  `minimumFetchInterval = 0`". Chẩn đoán sai hoàn toàn, tester đi soi build trong khi
  lỗi là một cặp nháy thiếu. Đổi ngầm thành `'true'` thì phải **đoán** app lưu bool kiểu
  gì (RC lưu chuỗi, logcat in bool thành số) — chưa đo nên không đoán.
- **Whitelist keyevent kiểm ngay lúc parse**, import `adb_input.KEYEVENTS` (không tạo
  import cycle). Đợi tới lúc chạy thì case đã reset RC, xoá prefs, force-stop, mở lại
  app, chèn mốc rồi mới `not_tested` vì một chữ gõ sai — mất cả một chu kỳ chạy máy.
  `POWER` lại chính là phím làm hỏng cả phiên test.
- **Nhãn case trùng → báo lỗi.** `expectations()` là dict keyed by label; hai case cùng
  nhãn thì một cái đè mất expectations của cái kia và cả hai cửa sổ nhận cùng một bộ.
  Runner dựa vào bất biến này mà trước đó không ai thực thi nó.
- **Đọc `reset` TRƯỚC khi bỏ case vì thiếu step**, không thì lỗi reset biến mất, tester
  sửa step rồi chạy lại mới lộ ra — đúng vòng lặp mà "gom hết lỗi một lượt" cấm.
- **Khai hai khoá tìm kiếm cùng lúc → báo lỗi**, không chọn ngầm một cái. Chọn ngầm là
  bấm vào node tester không hề ý.
- **`launch: {package: ...}` → báo lỗi.** Dạng này có trong ví dụ ở mục Architecture nên
  tester sẽ gõ đúng thế, nhưng runner lấy package ở cấp flow. Nói rõ thay vì bỏ đối số.
- **`DIRECTIONS` chuyển về `device_actions`** — một nguồn sự thật, `swipe` và parser
  validate cùng một danh sách.

### Test
+58 → tổng **320**, xanh khi không cắm máy. Chia hai file: `test_event_flow_parse.py`
(parser LÀM GÌ) và `test_event_flow_parse_regressions.py` (những gì nó PHẢI TỪ CHỐI —
mỗi test một đường sai âm thầm đã từng xanh).

Hai test bị viết lại vì assert không chứng minh điều tên nó nói:
- test whitelist phím cũ **khoá cứng** hành vi phát hiện muộn → giờ khoá hành vi chặn sớm.
- test "không bỏ sót step nào runner hiểu" chỉ so chuỗi với một list hardcode **trong
  chính test** → đổi tên cho đúng việc, và thêm test chạy thật cả 7 kind qua `run_step`
  (`type` và `home` trước đó chưa đi qua runner lần nào).

## Còn lại

**`POST /event/flow/run` + nút "Sinh case từ spec".** Route chạy phải **gate theo
`flow.ok`**, tuyệt đối không iterate `flow.cases` khi còn lỗi. Nút sinh case phụ thuộc
**open question 2** (bảng spec thật bao nhiêu event/screen → đổi hẳn UX) nên chưa làm.

`routes_event.py` đang 197 LOC — thêm route chạy flow là vượt 200, tách
`routes_event_flow.py` trước.

**Chưa chạy `pytest -m device`.** Nó force-stop app và sửa Remote Config trên máy thật.
