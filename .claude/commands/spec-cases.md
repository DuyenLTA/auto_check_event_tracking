---
description: Sinh khung case test từ trang spec Confluence, có đối chiếu lại với bảng event
argument-hint: "<link Confluence> [--out out/cases.json] [--ghi-chu \"phạm vi lượt sinh\"]"
---

Chạy workflow `spec-to-cases`. Tham số người dùng đưa vào: $ARGUMENTS

Bảng Event tracking chỉ nói event **tên gì**. Điều kiện để nó bắn — "từ session 2
trở đi", "1 lần/session", "không hiện lại khi user đã bấm rate" — nằm ở mục
Requirements dưới dạng văn xuôi và ở bảng Remote Key. Bỏ qua chúng thì case thiếu
tiền đề, và lượt chấm báo `Chưa test` hàng loạt mà không ai biết vì sao.

Đọc văn xuôi là việc của agent; đối chiếu lại với bảng là việc của Python. Đó là
hai phase của workflow này.

## 0. Tìm repo trước đã

Lấy cái đầu tiên có `.claude/workflows/spec-to-cases.js`:

1. `git rev-parse --show-toplevel` (nếu CWD đang nằm trong chính repo này)
2. biến môi trường `$EVENT_CHECK_REPO`
3. `~/projects/auto_check_event_tracking`

Không thấy thì dừng, nói rõ đã tìm ở đâu. Gọi đường dẫn tìm được là `<repo>`.

Cần `CONFLUENCE_BASE_URL` + `CONFLUENCE_TOKEN` trong env. Thiếu thì workflow chết
ở phase đầu; CLI nói rõ thiếu gì, in nguyên văn cho người dùng.

## 1. Link spec

`$ARGUMENTS` phải có một link Confluence (`http…`). Không có thì **dừng và hỏi** —
workflow cũng tự chặn, nhưng hỏi trước rẻ hơn một lượt agent chạy không.

Đừng đoán link từ lượt trước: khung case sinh từ nhầm trang thì **sai im lặng** —
mọi dòng đều hợp lệ, chỉ là của app khác.

- `--out <đường dẫn>` — mặc định `out/cases.json`. Nhiều trang spec cho cùng một
  app thì đặt tên riêng (`out/cases-widget.json`), không thì trang sau đè trang trước.
- `--ghi-chu "…"` — phạm vi lượt sinh, ví dụ *"chỉ happy case, mọi remote key đều
  bật"*. Để trống thì agent phủ hết mọi nhánh trang mô tả, kể cả nhánh tắt màn,
  tắt banner — thường nhiều hơn cần.

## 2. Gọi workflow

Workflow tool **chỉ nhận `scriptPath` nằm trong working directory của phiên**, mà
command này chạy từ đâu cũng được — nên copy script ra scratchpad trước đã, **luôn
luôn**, đừng chờ nó báo lỗi rồi mới vòng:

```
cp <repo>/.claude/workflows/spec-to-cases.js <scratchpad>/spec-to-cases.js
```

`<scratchpad>` là thư mục scratchpad của phiên (system prompt có nêu). Copy không
đổi hành vi gì: `repoDir` truyền vào là đường dẫn tuyệt đối.

Gọi Workflow tool với `scriptPath: "<scratchpad>/spec-to-cases.js"` và args:

- `url`: link Confluence ở bước 1. Bắt buộc.
- `repoDir`: `<repo>`
- `out`: đường dẫn file case, mặc định `out/cases.json`
- `ghiChu`: chuỗi phạm vi, để `""` nếu người dùng không nêu

Đừng dùng `name: "spec-to-cases"` (chỉ phân giải được khi phiên mở đúng repo root),
cũng đừng đọc file rồi truyền vào `script`.

Workflow tự chạy 2 phase: agent sinh khung case → Python `usv-cases check` đối
chiếu → sai thì cho agent sửa **đúng một vòng** rồi đối chiếu lại. Quá một vòng
thường không phải agent cẩu thả mà là spec thật sự mơ hồ — lúc đó đưa cho người
đọc còn rẻ hơn.

## 3. Đọc kết quả

Workflow trả về `{ cases, file, dat, doi_chieu }`:

- `dat: true` — `usv-cases check` trả exit code 0. Nói rõ bao nhiêu case, file ở đâu.
- `dat: false` — vẫn còn case không khớp bảng sau một vòng sửa. **Đừng tự sửa
  thêm**: in nguyên `doi_chieu` cho người dùng đọc, nêu rõ dòng nào lệch.
- `cases: 0` — agent không sinh được case nào, thường là link sai hoặc trang không
  có bảng event. Kiểm lại link trước khi chạy lượt nữa.

Mục **"Bỏ sót"** trong output là giá trị spec khai mà chưa case nào khẳng định —
đọc nó kể cả khi `dat: true`, vì nó in ra cả khi rỗng. Soi 3/15 giá trị mà im lặng
thì báo cáo trông như đã soi hết.

## 4. Nói rõ bước tiếp

Khung case **không chứa `steps`** — cố ý. Spec không nói nút Continue nằm ở đâu;
bước bấm phải dò trên máy thật. Nên sau lượt này:

```
/record-flow <package>        # dò steps, chốt vào flows/<package>.yaml
/check-event <package> <link> # chấm thật rồi publish artifact
```

Và nói thêm: trang spec thường là tài liệu **SDK dùng chung** cho nhiều app, nên
khung case vừa sinh xài lại được cho mọi app dùng SDK đó. Chỉ `steps` mới riêng
từng app.

**Không `git add`, không `git commit`.** Lượt này chỉ sinh file JSON trong `out/`
(đã gitignore).
