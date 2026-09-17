---
name: auto-check-event-tracking
description: >
  Đối chiếu event Firebase Analytics mà app Android thật bắn ra với bảng spec event
  tracking, ra report pass/fail kèm note sai ở đâu (thiếu event, bắn trùng, thiếu param,
  sai giá trị, sai kiểu, thừa param). Một lệnh: link Confluence + package → tự lái máy
  theo flow đã ghi → chấm → link artifact.
  Kích hoạt khi user nói về: check event tracking, verify event Firebase, đối chiếu event
  với spec, nạp spec từ link Confluence, log FA-SVC, logcat event, report event tracking,
  auto check event, ghi flow lái app.
  Cần adb + máy Android thật cắm cáp, bật USB debugging. Spec từ Confluence cần
  CONFLUENCE_BASE_URL + CONFLUENCE_TOKEN.
  Không dùng cho đối chiếu UI với design Figma — đó là tool ui-spec-verifier.
---

# Auto Check Event Tracking

Repo gốc: https://github.com/DuyenLTA/auto_check_event_tracking

## Đọc trước khi làm gì

`README.md` trong thư mục skill này là tài liệu đầy đủ: bảng verdict, format bảng spec,
cách tool đọc logcat, ràng buộc `setprop` không sống qua reboot, và nguyên tắc
"không verify được thì nói không verify được".

`flows/README.md` là format file flow — đường đi để lái app.

## Hai lệnh

```bash
usv-check --spec <link Confluence> --package com.example.app
usv-record --package com.example.app dump
```

Lần đầu trong repo: `.venv/Scripts/python.exe -m pip install -e .` (Windows) hoặc
`.venv/bin/python -m pip install -e .`.

## `check` — chấm một lượt

**Luôn chạy nền** (`run_in_background`): một lượt đủ case mất vài phút, user còn làm
việc khác.

```bash
usv-check --spec <link Confluence> --package com.example.app
usv-check --spec-tsv spec.tsv --package com.example.app --flows flows/com.example.app.yaml
usv-check --spec-tsv spec.tsv --package com.example.app --serial 29301FDH2006K7
```

- **stdout chỉ đúng một dòng JSON** — đọc dòng cuối stdout, parse ra:
  `{report, generated_at, package, app_version, metrics, pass, fail, not_tested, cases, results}`
- Tiến độ từng case đi ra **stderr** — không phải đọc.
- Cắm nhiều máy mà không có `--serial` → tool dừng và liệt kê serial, **không chọn bừa**.

### Sau khi chạy xong

1. Publish `report` thành artifact (Claude làm — tool chạy ở 127.0.0.1, không có đường
   tới claude.ai).
2. Ghi lại link để lần sau còn biết:
   ```bash
   usv-artifact --url <link artifact> --generated-at "<generated_at trong JSON>"
   ```
3. Trả lời user: link + `12 pass / 2 fail / 3 chưa test · bản 2.4.1 (125)`.

### Đọc kết quả đúng cách

- `fail > 0` → **nêu thẳng tên event sai trong câu trả lời**, đừng bắt user mở link mới biết.
- `not_tested` kèm "chưa có flow" → gợi ý chạy `record` để ghi case cho event đó.
- `not_tested` kèm "Lái hụt ở case ..." → flow sai selector, không phải app sai. Sửa flow.
- `fa_silent: true` → logcat không có dòng FA nào. **Không** kết luận app thiếu event.
- **Lái hụt không bao giờ là FAIL.** Chưa lái tới màn thì chưa đo gì cả.

## `record` — ghi flow, có người ngồi xem

Đường duy nhất sinh flow. `check` không bao giờ tự mò UI: AI bấm loạn trên máy thật có
thể mua hàng, gửi form, đăng xuất.

Mỗi lệnh là một lần gọi riêng; bước đã bấm giữ trong `out/record-<package>.json`.

```bash
usv-record --package com.example.app launch
usv-record --package com.example.app dump
usv-record --package com.example.app tap --id btnResult --index 0
usv-record --package com.example.app wait 2
usv-record --package com.example.app wait-text "Widget" --timeout 10
usv-record --package com.example.app swipe --id listContainer --huong up
usv-record --package com.example.app back
usv-record --package com.example.app show
usv-record --package com.example.app save --event widget_show --label "placement=result" --expect placement_name=result
usv-record --package com.example.app drop
```

- `dump` in cây UI rút gọn: chỉ node bấm được hoặc có chữ, mỗi dòng kèm `index=`.
- Ưu tiên selector: `--id` > `--desc` > `--text`. Khoá bằng chữ thì vỡ khi app đổi
  ngôn ngữ — tool cảnh báo nhưng không chặn.
- `save` nối case vào `flows/<package>.yaml` (giữ bản `.bak`), rồi dọn phiên để ghi case tiếp.
- Reset trước case: `--rc widget_enabled=true --clear-prefs apero_rate_prefs.xml`.

## Nguyên tắc không được phá

1. **Lái hụt ≠ FAIL** — step chết / tiền đề chưa đạt / chưa có flow đều ra `NOT_TESTED`.
2. **Không `pm clear`** — nó xoá login. Reset đi qua Remote Config + xoá vài file prefs.
3. `setprop log.tag.FA-SVC` chỉ ăn từ lần app khởi động **sau** nó — `check` đã đặt
   đúng thứ tự, đừng tự mở app trước.
4. **Không cài APK.** User tự cài đúng bản; report ghi lại `versionName (versionCode)`
   đọc được trên máy.
5. Ảnh trong report là bằng chứng **ngữ cảnh**, không phải bằng chứng thời điểm.
