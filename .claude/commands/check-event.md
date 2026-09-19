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
- `--spec-tsv <file>` → truyền nguyên
- không có gì → **dừng và hỏi link**. Đừng đoán: không chỗ nào trên đĩa ghi lại
  link của lượt trước, và chấm với trang spec sai thì mọi event ra "không có
  trong bảng" — trông như app sai trong khi chỉ là nhầm trang.

Dùng `--spec` thì cần `CONFLUENCE_BASE_URL` + `CONFLUENCE_TOKEN` trong env.
Thiếu thì tool tự nói thiếu gì, in nguyên văn cho người dùng.

Flow thì tool tự tìm `flows/<package>.yaml`, chỉ truyền `--flows` khi người dùng
chỉ đích danh file khác. Không có flow **không phải lỗi**: mọi case ra `Chưa test`
kèm "chưa có flow" — nói thẳng là chưa có đường lái, đừng báo như app thiếu event.

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

Parse dòng JSON cuối stdout. Ba loại kết quả, **đừng gộp**:

- `pass` / `fail` — tool đã đo được: event bắn hay không, param đúng hay sai
- `not_tested` — **lái hụt, chưa đo gì cả**. Báo kèm `reason` (tên step chết và
  số giây đã chờ). Nói "app thiếu event" ở đây là báo oan
- `blocked` — reset không ăn (app không debuggable, Remote Config bị đè). Cũng
  chưa đo gì; in kèm cách sửa mà tool đưa ra

`notes` của mỗi case ghi đường đi thật của lượt chạy (bước tuỳ chọn nào bị bỏ
qua, có bỏ lần mở lại của reset không) — đọc nó trước khi đoán nguyên nhân.

Case `not_tested` thì trong report có ảnh **"lúc lái hụt"**: xem nó là biết màn
nào đang chắn, nhanh hơn đọc log.

## 5. Chạy tới khi ra kết quả thật, RỒI mới publish

Lượt không đo được gì thì **không publish**. Trang artifact toàn "Chưa test" không
nói được điều gì về app, mà mỗi cái link lại là một thứ người ta phải mở ra xem
rồi bỏ đi.

Hai trường hợp, xử khác nhau:

- **Chưa có flow** (`flows/<package>.yaml` không tồn tại) → đây mới là đầu việc,
  chưa phải kết quả. Dò đường lái trên máy (xem `/record-flow`), ghi flow, chạy
  lại. Lặp cho tới khi có ít nhất một case ra `ok`. Mỗi vòng nói ngắn gọn đang
  kẹt ở màn nào — đừng im lặng, cũng đừng publish giữa chừng.
- **Có flow mà case lái hụt** → sửa flow rồi chạy lại. Ảnh "lúc lái hụt" trong
  report local nói màn nào đang chắn; đọc nó, đừng đoán.

Publish khi lượt đã **đo được thật**: có `pass`/`fail`, kể cả khi fail — lúc đó
trang artifact mới có nội dung để đọc. Lượt vẫn còn case `Chưa test` xen lẫn thì
publish được, nhưng phải nói rõ case nào chưa đo và vì sao.

Tool chạy ở `127.0.0.1`, không có đường tới claude.ai, nên publish là việc duy
nhất chỉ Claude làm được — đừng bỏ qua khi đã có kết quả thật.

1. Report là HTML **sẵn khuôn artifact** (mở đầu bằng `<title>`, không có thẻ
   `html/head/body`): publish thẳng `file_path` là `<repo>/<report trong JSON>`.
2. Đọc file trước khi publish, nhưng **thay data URI ảnh bằng chỗ giữ chỗ**: file
   ~1 MB mà 99% là base64 ảnh chụp, phần text chỉ ~10 KB. Đọc nguyên nó là đốt
   context vô ích.
3. Publish xong ghi link lại:

   ```
   cd <repo> && .venv/bin/usv-artifact --url "<url>" --generated-at "<generated_at trong JSON>"
   ```

   `usv-artifact` không tham số thì in link đã lưu của lượt trước.

## 6. Báo lại

Nói rõ: bao nhiêu pass / fail / chưa test, giờ bắn của từng event (`actual` trong
`results`), bản app đã chấm, và **link artifact**. Case `not_tested` thì nêu step
chết, đừng để nó lẫn vào đám pass.

**Dừng ở đây. Không `git add`, không `git commit`, không `git push`.** Lượt chấm
chỉ sinh ra report trong `out/` (thư mục này đã gitignore). Sửa flow hay sửa tool
là việc riêng, người dùng sẽ tự nói.

Bằng chứng ảnh là bằng chứng **ngữ cảnh**: Firebase bắn event bất đồng bộ nên ảnh
có thể chụp sớm hơn lúc event thật sự bắn. Dùng ảnh để nói màn nào đang hiện,
đừng dùng để kết luận thời điểm.
