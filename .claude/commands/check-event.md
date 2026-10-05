---
description: Chấm event tracking của một app Android trên máy thật rồi xuất báo cáo artifact
argument-hint: "<package> [link Confluence | --spec-tsv <file>] [--serial <serial>]"
---

Chạy `usv-check` một lượt rồi publish report. Tham số người dùng đưa vào: $ARGUMENTS

## 0. Tìm repo trước đã

Command này chạy được từ thư mục bất kỳ, nên **đừng giả định CWD**. Lấy cái đầu
tiên có `src/usv/cli_check.py`:

1. `git rev-parse --show-toplevel` (nếu CWD đang nằm trong chính repo này)
2. biến môi trường `$EVENT_CHECK_REPO`
3. `~/projects/auto_check_event_tracking`

Không thấy thì dừng, nói rõ đã tìm ở đâu. Gọi đường dẫn tìm được là `<repo>`.

Lệnh luôn gọi qua `<repo>/.venv/bin/usv-check` — **đường dẫn tuyệt đối**.
`usv-check` không có trong PATH toàn cục, và `.venv/bin` chỉ đúng cho repo này.
Báo `command not found` thì chạy `cd <repo> && .venv/bin/python -m pip install -e .`
rồi thử lại: venv cài từ trước khi mấy lệnh này được thêm thì thiếu file lệnh.

## 1. Package và spec

**Chỉ nhận package id**, không nhận tên app: khớp theo tên là khớp mờ, gõ thiếu
một ký tự thì nó lái app hàng xóm và chấm sai app mà không báo gì.
`$ARGUMENTS` không có chuỗi nào trông như `com.abc.xyz` thì **dừng và hỏi**.

Spec lấy theo thứ tự:

- chuỗi `http…` trong `$ARGUMENTS` → `--spec "<link>"`
- **tên chức năng** trong `$ARGUMENTS` (`rating`, `widget`, `daily checkin`,
  `full screen intent`…) → `--spec "<tên>"`, truyền nguyên tên, đừng tự đi tra
  link. Tool phân giải: tên đã lưu trong `specs.json` thì dùng luôn, chưa lưu
  thì hỏi Confluence và chỉ nhận trang có dạng `SDK <tên> V x.y.z`
- `--spec-tsv <file>` → truyền nguyên
- không có gì → **dừng và hỏi**. Đừng đoán: không chỗ nào trên đĩa ghi lại spec
  của lượt trước, và chấm với trang spec sai thì mọi event ra "không có trong
  bảng" — trông như app sai trong khi chỉ là nhầm trang.

Tên khớp nhiều trang, hoặc không trang nào có số version, thì tool **dừng và in
danh sách** — hỏi người dùng chọn, rồi chốt lại một lần cho lượt sau:

```
cd <repo> && .venv/bin/usv-spec --add "<tên>" "<link đã chọn>"
```

`usv-spec` không tham số thì in các tên đã lưu.

Dùng `--spec` thì cần `CONFLUENCE_BASE_URL` + `CONFLUENCE_TOKEN` trong env.
Thiếu thì tool tự nói thiếu gì, in nguyên văn cho người dùng.

Flow thì tool tự tìm `flows/<package>.yaml`, chỉ truyền `--flows` khi người dùng
chỉ đích danh file khác. Không có flow thì mọi case ra `not_tested` kèm "chưa có
flow" — đó là việc của mình (mục 5), không phải kết quả để báo.

## 2. Chọn máy

```
adb devices -l
```

- 0 máy → **dừng**: cần máy Android thật cắm cáp, bật USB debugging
- đúng 1 máy → không truyền `--serial`
- nhiều máy → `--serial` lấy từ `$ARGUMENTS`; không có thì in danh sách ra và
  **hỏi**. Chọn bừa là chấm trên máy người khác đang dùng
- máy `unauthorized` không tính là dùng được

## 3. Chạy nền

Một lượt mất vài phút (qua splash ad, onboarding, paywall), nên **luôn**
`run_in_background`, đừng để người dùng ngồi chờ:

```
cd <repo> && .venv/bin/usv-check --package <pkg> --spec "<link>" [--serial <S>] \
  > <scratchpad>/check-stdout.json 2> <scratchpad>/check-stderr.log
```

`<scratchpad>` là thư mục scratchpad của phiên (system prompt có nêu).

stdout là **đúng một dòng JSON** (`report`, `generated_at`, `app_version`, `pass`,
`fail`, `not_tested`, `cases`, `results`); tiến độ từng case ra stderr. Trong lúc
chờ muốn xem đang tới đâu thì `tail` file stderr, đừng poll `adb`.

## 4. Đọc kết quả

Parse dòng JSON cuối stdout. Chỉ `pass`/`fail` là kết quả; mọi thứ khác là việc
còn dở phải xử ở mục 5:

- `pass` / `fail` — tool đã đo được: event bắn hay không, param đúng hay sai
- `not_tested` — **lái hụt, chưa đo gì cả**. Báo kèm `reason` (tên step chết và
  số giây đã chờ). Nói "app thiếu event" ở đây là báo oan
- `blocked` — reset không ăn (app không debuggable, Remote Config bị đè). Cũng
  chưa đo gì; in kèm cách sửa mà tool đưa ra

`notes` của mỗi case ghi đường đi thật của lượt chạy (bước tuỳ chọn nào bị bỏ
qua, có bỏ lần mở lại của reset không) — đọc nó trước khi đoán nguyên nhân.

## 5. CHỈ CÓ PASS / FAIL — lái tới khi ra kết quả, RỒI mới publish

Tester chốt (05/10/2026), **không ngoại lệ**: report gửi đi chỉ được có **Khớp**
hoặc **Sai**. Không có "Chưa test", không có "Chưa kết luận". Hai thứ đó không
phải kết luận về app mà là việc agent chưa làm xong.

Lượt còn bất kỳ `not_tested` / `not_verifiable` / `blocked` nào thì **chưa xong**
— report local hiện băng đỏ "Lượt chưa xong", và **cấm publish** bản đó. Tự xử
từng cái cho tới khi về 0, đừng hỏi lại người dùng, đừng báo "chưa test được":

- **Chưa có flow** (`flows/<package>.yaml` không có) → dò đường lái trên máy
  (xem `/record-flow`), ghi flow, chạy lại.
- **Event chưa có case nào** ("chưa có case nào cho event này") → tự thêm case
  vào flow: đọc cột Triggered của spec để biết phải làm gì trên app, dò trên máy
  (`uiautomator dump`, `screencap`), ghi case, chạy lại.
- **Lái hụt** (step chết, `reason` ghi tên step + số giây chờ) → lên máy xem màn
  đang chắn (`screencap` + `uiautomator dump`), sửa step trong flow (selector
  sai, thiếu bước đóng popup/ads, chờ chưa đủ…), rồi chạy lại **riêng case đó**
  bằng `--case "<nhãn>"`. Lặp tới khi ra pass/fail.
- **Chưa kết luận** (logcat không phân biệt String/Number…) → đo bằng cách khác
  trên máy (payload upload Firebase, log verbose) cho ra pass/fail.
- **Blocked** (reset không ăn) → làm theo cách sửa tool in ra, chạy lại.

Mỗi vòng nói ngắn một dòng đang kẹt ở màn nào.

**Chỉ chạy lại case hụt, KHÔNG chạy lại cả lượt** (tester chốt 05/10/2026: một
lượt ~30 phút, chạy lại cả lượt cho vài case là phí). Lượt đầy đủ đầu tiên là
**base**; copy stdout của nó thành `check-base.json` (đừng để lượt sau ghi đè).
Sửa flow xong thì chạy lẻ và gộp thẳng vào base:

```
cd <repo> && .venv/bin/usv-check --package <pkg> --spec ... \
  --case "<nhãn case hụt 1>" --case "<nhãn case hụt 2>" \
  --base <scratchpad>/check-base.json \
  > <scratchpad>/check-stdout.json 2> <scratchpad>/check-stderr.log
```

Event của case khớp `--case` lấy kết quả mới (kể cả vẫn hụt — report không
giấu); event khác giữ kết quả base. Report ra **đủ mọi event spec**. Còn hụt thì
lấy stdout vừa ra làm base mới, sửa tiếp, gộp tiếp. Chỉ chạy lại cả lượt khi sửa
flow/tool làm đổi đường đi của **nhiều** case đã Khớp.

Report **không có mục ảnh chụp màn hình** (tester bỏ 05/10/2026). Muốn biết màn
nào đang chắn khi lái hụt thì tự `adb exec-out screencap -p` lúc debug, đừng đưa
ảnh vào report.

Tool chạy ở `127.0.0.1`, không có đường tới claude.ai, nên publish là việc duy
nhất chỉ Claude làm được — đừng bỏ qua khi đã có kết quả thật.

1. Report là HTML **sẵn khuôn artifact** (mở đầu bằng `<title>`, không có thẻ
   `html/head/body`): publish thẳng `file_path` là `<repo>/<report trong JSON>`.
2. Đọc file trước khi publish. Kiểm: không có băng "Lượt chưa xong" — có thì
   quay lại mục 5, chưa được publish.
3. Publish xong ghi link lại:

   ```
   cd <repo> && .venv/bin/usv-artifact --url "<url>" --generated-at "<generated_at trong JSON>"
   ```

   `usv-artifact` không tham số thì in link đã lưu của lượt trước.

## 6. Báo lại

Nói rõ: bao nhiêu pass / fail (không có mục thứ ba), event nào sai và sai gì,
bản app đã chấm, và **link artifact**. Case nào đã phải sửa flow lái lại thì nói
ngắn đã sửa gì.

**Dừng ở đây. Không `git add`, không `git commit`, không `git push`.** Lượt chấm
chỉ sinh ra report trong `out/` (thư mục này đã gitignore). Sửa flow hay sửa tool
là việc riêng, người dùng sẽ tự nói.
