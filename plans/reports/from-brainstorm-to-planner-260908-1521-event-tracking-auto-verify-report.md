# Auto-verify Event Tracking — báo cáo brainstorm

**Ngày:** 2026-09-08 · **Trạng thái:** đã chốt thiết kế, spike XONG, sẵn sàng lên plan
**Nguồn:** user yêu cầu check event tracking theo bảng spec, tương tự tool check UI đang có

---

## 1. Vấn đề

Tester có bảng spec event tracking 8 cột (`Screen Name`, `Event_Name`, `Triggered`, `Params`,
`Param Description`, `Value Type`, `Value`, `Value Description`). Cần tool tự đối chiếu event app
thật bắn ra với bảng đó, ra report pass/fail, fail thì chỉ rõ chỗ.

## 2. Quyết định user đã chốt (KHÔNG tự đổi)

| Hạng mục | Chốt |
|---|---|
| Nguồn event | **Chỉ Firebase Analytics** (không Adjust, không AppsFlyer) |
| Nạp spec | **Dán bảng vào ô text** (không Sheet, không upload file) |
| Ràng lúc bắn | **Gán nhãn từng bước** — tester đánh dấu bước rồi làm động tác |
| FAIL khi | thiếu param spec khai · giá trị ngoài danh sách · bắn trùng nhiều lần · app gửi thêm param spec không khai |
| Vị trí code | ~~cùng repo `ui-spec-verifier`, tab mới~~ → **ĐỔI 2026-09-08: repo riêng `auto_check_event_tracking`**, bỏ hết Figma/pen. Xem mục "Tách repo" trong plan.md |

## 3. Spike — đã đo thật, không phải suy luận

Máy `99261FFAZ0077C` (Pixel 4), app `ai.photogenerator.aivideo.aivideogenerator.aiart` (AIP922).

| Câu hỏi | Kết quả đo |
|---|---|
| `setprop log.tag.FA VERBOSE` cần root? | **Không**, chạy được, đọc lại đúng `VERBOSE` |
| FA có in event ra logcat? | **Có** — 67 dòng `Logging event` trong 1 lần mở app |
| Tag nào in? | **`FA-SVC` 67/67**. Tag `FA` in `Logging telemetry for logEvent` 67x nhưng **không kèm params** |
| Định dạng | `Logging event: origin=app,name=EVENT(_short),params=Bundle[{k(_s)=v, k=v}]` |
| `origin` | `app` 42 · `auto` 8 (`screen_view`,`session_start`,`user_engagement`) · `am` 17 (`ad_query`) |
| Param hệ thống | `ga_event_origin(_o)` 42/42 · `ga_screen_class(_sc)` 40/42 · `ga_screen_id(_si)` 40/42 |
| Global param tự khai (`setDefaultEventParameters`) | **không có** trong app này |
| Dòng bị logcat cắt | **0/67**. Dài nhất 513 B, trần payload 4068 B |
| Marker `adb shell log -t USV_MARK` | **Chạy**, nằm chung timeline với event → **không có lệch giờ host/device** |
| Hai event trong spec user gửi | **có mặt thật**: `rating_placement_viewed{placement_name=home}`, `rating_star_clicked{placement_name=home, star_value=3}` |

Fixture đã lưu: `tests/fixtures/fa-events-aip922.log` (134 dòng, đã redact id thiết bị + ad unit ID).

### 3b. Ba giả định BAN ĐẦU CỦA CLAUDE BỊ SAI, spike sửa lại

1. Nói "chỉ đọc tag `FA`, `FA-SVC` chỉ để chẩn đoán" → **ngược**. Event chỉ có trên `FA-SVC`.
2. Nói param hệ thống tiền tố `firebase_` → **sai tiền tố**. Thật là `ga_`, kèm hậu tố `(_o)`/`(_sc)`.
3. Đề xuất "param nào có ở 100% event thì coi là global" → **không cần** làm cơ chế chính.
   Tiền tố `ga_` lọc sạch. Giữ heuristic làm phương án dự phòng trong YAML, không bật mặc định.

### 3c. Đã chạy end-to-end spec thật × log thật

| Case | Kết quả |
|---|---|
| Spec đúng | **3 PASS, 0 fail oan** — 3 param `ga_*` bị lọc đúng, không sinh `FAIL_PARAM_EXTRA` |
| Bỏ `home` khỏi danh sách cho phép | `FAIL_VALUE` × 2, đúng chỗ |
| Spec ghi `placement_name` là `Number` | `FAIL_TYPE` × 2 |
| Spec khai thêm param app không gửi | `FAIL_MISSING` |
| Spec ghi sai tên event (`rating_star_click`) | `FAIL_MISSING` — event không bắn |

## 4. Ba nhà đã cân, vì sao chọn `ui-spec-verifier`

| Cần gì | ui-spec-verifier (FastAPI) | ad-checklist-diff (Streamlit) | tool mới |
|---|---|---|---|
| Verdict nhiều mức + `NOT_VERIFIABLE` + nhãn VN | ✅ sẵn | ❌ chỉ Khớp/Lệch | ❌ |
| Ma trận hàng × tiêu chí | ✅ `report_matrix.py` | ❌ | ❌ |
| Export xlsx | ✅ `exporter.py` | ❌ HTML only | ❌ |
| adb async + timeout + transport error | ✅ 184 LOC | ⚠️ `subprocess.run` sync | ❌ |
| Config YAML có validate | ✅ `check_config.py` | ❌ hardcode `FILTERS` | ❌ |
| Test xanh khi không cắm máy | ✅ marker `device`, 459 test | ⚠️ | ❌ |
| Capture logcat | ❌ viết ~140 LOC | ✅ sẵn | ❌ |

**Lý do quyết định:** event tracking cần **nhiều mức verdict cho mỗi dòng**; tool ads chỉ có
`found/not-found` nên phải xây lại toàn bộ tầng đó. Đổi stack 459 test để tiết kiệm 140 dòng
subprocess là lỗ.

Thêm hai lý do vận hành:
- Streamlit rerun cả script mỗi lần bấm. Luồng này cần **40-60 lần bấm marker khi stream đang chạy**
  — đúng điểm yếu của Streamlit (tool ads đã phải nhét `capture_proc` vào `session_state` cho 2 nút).
- Tool ads nằm trong `~/.claude/skills/` mà rule cấm sửa trực tiếp; upstream là repo GitHub riêng.

**Hướng gộp về sau (nếu muốn 1 cửa sổ):** port tool ads **vào** `ui-spec-verifier` thành tab thứ 3
(logic diff ~200 LOC, dễ), rồi đổi tên tool. Ba tab: UI · Event · Ads. **Không** làm chiều ngược lại.

## 5. Thiết kế chốt

### Luồng
```
1. Dán bảng spec → parse → BẢNG PREVIEW, tester xác nhận đúng rồi mới cho Ghi
2. Chọn app · tuỳ chọn "Ghi từ lúc mở app" (cho first_open / placement_name=app_shortcut)
3. Ghi: setprop FA-SVC VERBOSE → logcat -c → mở stream
4. Mỗi bước: bấm nút mang nhãn cột `Triggered` → tool chèn marker vào logcat
   → tester làm động tác trên máy → bấm nhãn bước tiếp
5. Dừng ghi → cắt timeline theo marker → mỗi khoảng = 1 bước
6. Check → report HTML + xlsx
```

**MỘT nút một bước**, không phải Bắt đầu+Xong: marker bước sau chính là điểm kết bước trước.
Spec 40-60 event thì tiết kiệm một nửa số lần bấm, cùng lượng thông tin.

### Lọc, theo đúng thứ spike đo được
- **Lọc 2 tầng.** Trên device: `adb logcat -s FA-SVC:V USV_MARK:I` — tag filter, cắt 90% ngay
  trên điện thoại nên tiết kiệm cả đường truyền (đo: 12 964 → 1 259 dòng). Trên host: khớp
  `Logging event:` (→ 67). Bỏ tag `FA` (in `Logging telemetry`, không kèm params).
- **KHÔNG lọc thẳng `Logging event: origin=app`** dù nó ngắn nhất (→ 42). Chỉ hơn 25 dòng /12 964
  = 0,2%, mà mất 3 thứ: (a) **mất dòng `USV_MARK`** → không cắt được cửa sổ, sập cả cơ chế gán nhãn;
  (b) không phân biệt "FA không in log" với "app không bắn event" → đúng rủi ro R3; (c) mất
  `ga_screen_class` do `screen_view` là `origin=auto` → mất dữ liệu cho cột `Screen Name`.
- Chỉ `origin=app` vào phạm vi spec. `origin=auto` và `origin=am` → bucket `EXTRA`, **không fail**.
  Lọc theo **origin**, không theo denylist tên event → bền hơn.
- Param key khớp `^ga_` hoặc `^_` → param hệ thống, bỏ trước khi chấm "thừa param".
- Tách param bằng lookahead `,\s+(?=[A-Za-z_][\w.]*(\([^)]*\))?=)`, **không** `split(", ")`:
  giá trị chuỗi chứa dấu phẩy/hai chấm/backtick sẽ vỡ. Đã verify 67/67 kể cả `error_msg` dài 513 B.
- Dòng có `params=Bundle[{` mà không đóng `}]` → logcat cắt → `NOT_VERIFIABLE`, không báo thiếu param.
- **Bắn trùng chấm theo TỪNG CỬA SỔ marker**, không theo cả phiên: `track_ad_request` bắn 17x/phiên
  là bình thường.

### Không kết luận được thì nói thẳng
- `Value Type` String vs Number khi giá trị là số: logcat in Long `3` và String `"3"` y hệt →
  `NOT_VERIFIABLE`. Nhưng spec `Number` mà app gửi `home` thì **FAIL** — kiểm một chiều.
- Cột `Triggered` là văn xuôi → làm nhãn nút cho tester, **không** chạm verdict.
- Event trong spec mà tester chưa đánh dấu bước → `NOT_TESTED`, **không** FAIL.

### Verdict thêm — chỉ THÊM, không đổi tên 5 cái đang có
Luật này đã ghi ở `src/usv/check_models.py:38`: giá trị enum nằm trong xlsx và report cũ.
```
FAIL_VALUE        gia tri ngoai danh sach spec cho phep
FAIL_TYPE         spec Number ma app ban chu
FAIL_DUPLICATE    mot buoc ma event ban nhieu lan
FAIL_PARAM_EXTRA  app gui param spec khong khai
NOT_TESTED        tester chua danh dau buoc nao cho event nay
```
`FAIL_MISSING` dùng lại cho cả "event không bắn" và "thiếu param".

### Module (mọi file <200 LOC)
```
event_spec_models.py     SpecEvent / SpecParam                ~70
event_spec_parse.py      dán TSV → spec                       ~150   ← rủi ro cao nhất
logcat_stream.py         setprop · -c · stream · chèn marker  ~140
fa_event_parse.py        1 dòng FA-SVC → ObservedEvent        ~110
event_window.py          cắt timeline theo marker             ~90
event_system_params.py   lọc ga_/_ + dò global param          ~80
checks/event_presence.py có bắn · bắn trùng · chưa test       ~120
checks/event_params.py   thiếu · thừa · giá trị · kiểu        ~170
report_event_css.py      token + CSS theo mau tool ads        ~130
report_event_html.py     scorecard · chips · details theo screen ~170
routes_event.py          spec · record · marker · check       ~150
```
Dùng lại nguyên: `adb_client`, `check_models`, `check_runner`, `check_config`, `check_mapping`,
`exporter`, `session_state`.
**KHÔNG** dùng `report_css.py` / `report_blocks.py` / `report_matrix.py` của tool UI — xem mục 5b.

### 5b. Report — theo mẫu tool check ID ads (user chốt)

Không dùng tầng report của tool UI. Bê **hệ thiết kế của `ad-checklist-diff/report_renderer.py`**:

- **Token y nguyên**, không thêm màu: `--accent:#146b6e` · `--paper:#eef2f1` · `--pass:#1f7a4d`
  `--fail:#b23b2e` · `--pending:#97650f`, kèm đủ bộ dark 3 trạng thái
  (`:root` sáng · `@media prefers-color-scheme:dark` bọc `:not([data-theme="light"])` · `[data-theme="dark"]`).
- **Chữ y nguyên**: Manrope 800 tiêu đề · Public Sans thân · JetBrains Mono dữ liệu · `tabular-nums`.
- **Bố cục y nguyên**: eyebrow → h1 → scorecard có progress bar → section chips → callout → `<details>` mỗi mục.

Mở rộng, chỉ những chỗ dữ liệu event cần 5 trạng thái thay vì 2 (`found`/`not-found`):

| Việc | Cách |
|---|---|
| `NOT_VERIFIABLE` | thêm rule `.status.pending` — **token `--pending` đã có sẵn**, chỉ thiếu rule |
| `NOT_TESTED` / `EXTRA` | thêm `.status.not_tested` trung tính (`--surface-alt` + viền `--line`) |
| Bảng 3 cột → 5 cột | Event · Param · Spec cần · App gửi · Kết quả. `min-width` 480 → 720 px |
| Section | **theo `Screen Name`** — khớp đúng pattern section-per-mục của report ads |
| Scorecard | mẫu số = **số dòng đã kiểm**. `NOT_TESTED` và `EXTRA` ra chip riêng, **không bao giờ vào số fail** |
| Callout | dùng lại nguyên vẹn cho 2 việc: liệt kê event `EXTRA`, và cảnh báo R3 "không đọc được FA-SVC nào" |

**Mock đã dựng, số liệu tính từ log thật** (không gõ tay): `plans/reports/260908-1521-event-report-mock.html`
→ https://claude.ai/code/artifact/d33633ec-6594-457f-a024-ac4b153f27e5
Đủ 5 trạng thái: 3 khớp · 1 thiếu param · 1 chưa kết luận (`error_code=3` spec khai String) ·
1 chưa test · 7 event EXTRA + 4 event Firebase tự thu.

## 6. Rủi ro

**R1 — parse bảng dán. CAO. Spike đã bắt lỗi thật.**
Gộp dòng theo số cột **không chạy được**: hàng gãy làm **mất ô rỗng** ở điểm gãy.
Đo: `rating_placement_viewed…placement_name\t` = 4 cột, nối thô với `String\t…` ra **6** cột
(ô `Param Description` rỗng bị `String` chiếm), phải 7 → parser ăn luôn hàng sau, spec sai câm.

Chốt cách làm: **parse TSV nghiêm, một hàng một dòng, KHÔNG tự gộp.** Hàng sai số cột →
in ra ở preview kèm báo lỗi rõ, để tester tự sửa trong ô text. Không đoán.
(Dán từ Excel vào `<textarea>` thật thì giữ nguyên một hàng một dòng và giữ ô rỗng bằng tab liên
tiếp — bảng trong tin nhắn chat bị gãy là do chat reflow, không phải do clipboard.)
Cùng triết lý repo: `check_config.py:4` — "kiểu im lặng nguy hiểm hơn crash".

**R2 — `setprop` không sống qua reboot.** Tool phải set lại mỗi lần Ghi, và **app phải khởi động lại
sau khi set** (property đọc lúc process start). Không thì log rỗng mà tester tưởng app không bắn event.

**R3 — build release strip log Firebase.** Chưa gặp trên AIP922 nhưng chưa loại trừ cho app khác.
Tool phải phân biệt "app không bắn event" với "FA không in log": nếu **không có dòng FA-SVC nào**
trong cả phiên → báo "không đọc được FA", không báo app thiếu event.

**R4 — thứ tự marker vs event.** Event bắn ngay sát lúc bấm marker có thể lệch vài chục ms.
Cần vùng đệm ở biên cửa sổ, và ghi rõ trong report event nào nằm sát biên.

## 7. Câu chưa chốt

1. **Cột `Screen Name` đối chiếu thế nào?** Log cho sẵn `ga_screen_class=AIP922AIPhotoVideoMakerMainActivity`
   (40/42 event), nhưng spec ghi tên người-đọc kiểu "Home". Cần mapping screen↔activity.
   `check_mapping.py` + `config/node-mapping.yaml` đã có sẵn khuôn cho việc này — dùng lại, nhưng
   ai维护 file mapping thì chưa rõ. **Vòng 1 đề xuất: không chấm cột này, chỉ in ra để đối chiếu mắt.**
2. **Bảng spec thật có bao nhiêu event/screen?** Ảnh hưởng trực tiếp UX bấm marker. 5 event thì
   nút nào cũng được; 60 event thì cần tìm kiếm + nhóm theo screen.
3. **Có app nào global param tự khai không?** AIP922 không có. Nếu app khác có thì cần bật
   heuristic dự phòng ở R1/mục 5.
4. **`NOT_VERIFIABLE` cho String-vs-Number có gây ồn không?** Chưa đo được: mẫu này `star_value`
   khai `Number` nên không chạm nhánh đó. Cần một spec có param String mang giá trị số.
5. **Reset giữa các case khi tự động hoá?** Popup rating bị chặn tần suất (1 lần / N session)
   nên lái tới `home` 4 lần **không** hiện 4 lần. `pm clear` (mất data/login) hay override
   Remote Config (đã có kỹ thuật patch `frc_*.json` + throttle, kèm bẫy mirror prefs SDK Apero)?
   Đây là phần khó nhất của tự động hoá, khó hơn chuyện tapping.
6. **Đổi tên repo/tool khi thêm tab?** `ui-spec-verifier` không còn khớp. Cosmetic, chưa gấp.

---

## 8. Bổ sung — tự động lái app (user hỏi thêm sau khi chốt)

**Câu hỏi:** viết test case rồi tool tự thao tác + check, vì `placement_name` có 4 giá trị
(`result`, `exit_click`, `app_shortcut`, `home`) — bấm tay 4 màn mỗi build là không thực tế.

**Trả lời: được, và đáng làm** — khác với check UI. Check UI soi màn **đang hiện**; event thì
phải **lái app tới đúng trạng thái** mới bắn ra.

**Không phải làm lại plan.** Script chỉ thay **cái nút bấm marker**: nó tự gọi
`adb shell log -t USV_MARK`. Phía sau (cắt cửa sổ → chấm check → report) y nguyên.
Thành **phase 7**, phase 1→6 không đổi.

**Không thêm dependency.** Đã kiểm: không có `maestro` / `uiautomator2` / `appium-python-client`
trên máy — và không cần. `DeviceNode` (`models.py:35-47`) đã có `resource_id` · `text` ·
`content_desc` · `bounds_px` · `clickable`, nên bấm một element = `ui_dump.parse_dump()` →
tìm node → `input tap` vào tâm `bounds_px`. `input keyevent` đã verify chạy trong phiên spike.
Selector khoá `(resource_id, index_in_parent)` theo đúng luật `models.py:30`.

**Ba chỗ chặn, cái to nhất KHÔNG phải tapping:**

| # | Chặn | Ghi chú |
|---|---|---|
| 1 | **Popup rating bị chặn tần suất** | Lái tới `home` 4 lần không hiện 4 lần. Phải reset giữa case → **open question 5** |
| 2 | **`app_shortcut` không lái được trong app** | Đã kiểm: `cmd shortcut` trên máy chỉ có `reset-throttling`, không `list`/`start`. Phải `am start` bằng intent từ `shortcuts.xml`. Vòng 1 để cho luồng tay |
| 3 | Flow vỡ khi UI đổi | Ưu tiên `resource_id`; cảnh báo khi flow phải dùng `tap_text` |

Vì (2) nên **luồng bấm tay ở phase 6 không phải công cốc** — nó là fallback cho case không
script được, không phải bản bị thay thế.
