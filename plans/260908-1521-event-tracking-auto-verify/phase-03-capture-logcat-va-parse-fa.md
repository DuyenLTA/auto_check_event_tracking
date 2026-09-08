---
phase: 3
title: "Capture logcat + parse FA-SVC"
status: completed
priority: P1
effort: "5h"
dependencies: [1]
---

# Phase 3: Capture logcat + parse FA-SVC

## Overview
Bật log Firebase, mở stream logcat đã lọc theo tag, chèn marker được, và biến
dòng log thành `ObservedEvent`. Độc lập với phase 2 — chạy song song được.

## Requirements
- Functional: bật `log.tag.FA-SVC VERBOSE`; `logcat -c`; stream tag-filtered; chèn
  marker; tuỳ chọn force-stop + mở lại app; parse dòng → event có `origin`.
- Non-functional: `asyncio.create_subprocess_exec`, **không `shell=True`**; test
  parse chạy được **không cần máy**; test stream gắn marker `device`.

## Architecture
```
logcat_stream.py       enable_fa(client)            setprop log.tag.FA-SVC VERBOSE
                       start(client, from_launch)   -c, spawn `logcat -s FA-SVC:V USV_MARK:I`
                       mark(client, label)          adb shell log -t USV_MARK
                       stop() -> tuple[str,...]
fa_event_parse.py      parse_line(line) -> ObservedEvent | Marker | None
event_system_params.py is_system(key) -> bool
```
Lọc 2 tầng, theo đúng số đo: tag ở device (12 964→1 259), `Logging event:` ở host (→67).
**KHÔNG** lọc `origin=app` ở tầng logcat — mất marker, mất phát hiện R3, mất `ga_screen_class`.

## Related Code Files
- Create: `src/usv/logcat_stream.py` (~140 LOC)
- Create: `src/usv/fa_event_parse.py` (~110 LOC)
- Create: `src/usv/event_system_params.py` (~80 LOC)
- Modify: `src/usv/adb_client.py` (thêm `logcat_clear`, `logcat_stream`, `shell_log`, `setprop`)
- Create: `tests/test_fa_event_parse.py`, `tests/test_logcat_stream.py`

## Implementation Steps
1. `adb_client.py` — 4 hàm mới dùng lại `_run` sẵn có. `logcat_stream` trả process
   để caller đọc dần; timeout riêng (stream sống lâu, không dùng `CMD_TIMEOUT`).
2. `fa_event_parse.py`:
   - `LINE = re.compile(r"Logging event: origin=(\w+),name=([^,]+),params=Bundle\[\{(.*)\}\]\s*$")`
   - **tách param bằng lookahead** `,\s+(?=[A-Za-z_][\w.]*(\([^)]*\))?=)` — verified 67/67.
     Ghi comment nói rõ vì sao không `split(", ")`: giá trị chuỗi chứa dấu phẩy sẽ vỡ.
   - bỏ hậu tố `(_x)` ở cả tên event và tên param
   - dòng có `params=Bundle[{` mà **không đóng** `}]` → trả cờ `truncated=True`
   - nhận cả dạng `Logging event (FE):` của tag `FA` để bền qua version SDK khác,
     rồi **dedupe theo (timestamp, name)**
3. `event_system_params.py` — `^ga_` hoặc `^_`. Heuristic "param có ở 100% event =
   global" viết sẵn nhưng **mặc định TẮT** trong YAML (AIP922 không có global param;
   bật khi open question 3 có lời).
4. `logcat_stream.py` — `enable_fa` + cảnh báo R2 (`setprop` không sống qua reboot,
   app phải restart sau khi set); `from_launch=True` thì force-stop + `am start`.
5. Test không cần máy, dùng fixture `fa-events-aip922.log`:
   - **67/67 dòng parse được**
   - origin đếm đúng `app 42 / auto 8 / am 17`
   - `ga_event_origin(_o)` / `ga_screen_class(_sc)` / `ga_screen_id(_si)` bị lọc
   - `ump_request_failed.error_msg` (513 B, có `:` `;` backtick `.`) **không vỡ**
   - dòng cắt giả → `truncated=True`, không báo thiếu param
   - dòng `USV_MARK` → `Marker`
   - `rating_placement_viewed` ra đúng `{placement_name: "home"}` sau khi lọc
6. Test cần máy → `@pytest.mark.device`.

## Success Criteria
- [x] 67/67 dòng fixture parse đúng
- [x] `pytest` xanh khi **rút cáp** (`-m "not device"`)
- [x] Không chỗ nào `shell=True`
- [x] Cả 3 file mới <200 LOC

## Risk Assessment
- **R3: build strip log Firebase.** Nếu **không dòng `FA-SVC` nào** trong cả phiên →
  trả cờ `fa_silent=True`, phase 5 in callout "không đọc được FA", **không** báo app
  thiếu event. Test bằng fixture rỗng.
- **R2: `setprop` không sống qua reboot** và app phải restart sau khi set. Chặn:
  `enable_fa` gọi mỗi lần Ghi; `from_launch` mặc định bật.
- Ring buffer 256 KiB có thể cuộn mất log nếu tester thao tác lâu. Lọc theo tag đã
  giảm 90%; nếu vẫn lo thì `logcat -G 1M` — chỉ làm khi gặp thật, không làm trước.

## Lệch khỏi plan khi làm

**`adb_client.py` phải tách.** Thêm 6 method logcat làm file lên 257 LOC, vượt 200.
Tách phần logcat thành `adb_logcat.py` (92 LOC) dạng **mixin** — `LogcatMixin` dùng
`self._run`/`self.adb` của `AdbClient`, nên `class AdbClient(LogcatMixin)`.
`adb_client.py` về 185 LOC. Truyền client qua tham số cũng được nhưng chỉ rườm rà hơn
mà không lợi gì.

**Bật cả tag `FA` chứ không chỉ `FA-SVC`.** `FA` không chở event nhưng nó là cách duy
nhất biết FA còn sống (R3), và ở version SDK khác chính nó in `Logging event (FE)`.
Nên `TAGS = (FA-SVC, FA, USV_MARK)` và `fa_silent` kiểm `"/FA" in line`.
