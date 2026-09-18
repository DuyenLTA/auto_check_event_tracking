---
description: Dò đường lái app trên máy thật rồi chốt thành case trong flows/<package>.yaml
argument-hint: "<package> [event] [--serial <serial>]"
---

Ghi flow bằng `usv-record`: đọc màn, bấm thử, chốt thành case YAML.
Tham số người dùng đưa vào: $ARGUMENTS

Khác `/check-event` ở nhịp làm việc: đây **không** phải chạy một phát rồi xong.
Mỗi bước là một lệnh riêng, và giữa hai lệnh phải **nhìn màn thật**. Đó là cả
điểm của chế độ này, không phải chỗ bất tiện cần tối ưu: `usv-check` không bao
giờ tự mò UI để bấm, vì bấm loạn trên máy thật có thể mua hàng, gửi form, đăng
xuất.

## 0. Tìm repo trước đã

Lấy cái đầu tiên có `src/usv/cli_record.py`:

1. `git rev-parse --show-toplevel` (nếu CWD đang nằm trong chính repo này)
2. biến môi trường `$EVENT_CHECK_REPO`
3. `~/projects/auto_check_event_tracking`

Không thấy thì dừng, nói rõ đã tìm ở đâu. Gọi đường dẫn tìm được là `<repo>`;
mọi lệnh gọi qua `<repo>/.venv/bin/usv-record` — đường dẫn tuyệt đối, vì
`usv-record` không có trong PATH toàn cục.

Đặt `R="cd <repo> && .venv/bin/usv-record --package <pkg> [--serial <S>]"` cho gọn
trong đầu, nhưng **vẫn gõ đủ** mỗi lệnh: mỗi lần gọi là một tiến trình riêng.

## 1. Package, máy, event

- Package id (`com.abc.xyz`) bắt buộc. `$ARGUMENTS` không có thì **dừng và hỏi** —
  đừng khớp theo tên app, gõ thiếu một ký tự là lái app hàng xóm.
- `adb devices -l`: 0 máy → dừng · 1 máy → khỏi `--serial` · nhiều máy → hỏi.
- Tên event thì **chưa cần** lúc dò, chỉ cần lúc `save`. Người dùng chưa nói thì
  cứ dò trước, hỏi tên event khi chốt.

Một case = **một event**. Cần đo 2 event thì ghi 2 case, đừng gộp.

## 2. Vòng dò: dump → bấm → dump

```
usv-record ... dump                       # cây UI rút gọn, mỗi dòng kèm index=
usv-record ... launch                     # force-stop rồi mở lại
usv-record ... tap --id btnResult --index 0
usv-record ... dump                       # bấm xong ra màn nào?
usv-record ... wait-text "Add Widget" --timeout 25
```

**Luôn `dump` trước khi bấm và sau khi bấm.** Bấm mù rồi đoán là cách chắc nhất
để ghi ra một flow chạy đúng một lần.

Bước dùng được: `dump · show · launch · tap · swipe · back · type · wait ·
wait-text · close-ad · allow · save · drop`.

`dump` và `show` **không ghi bước** (`show` in các bước đã gom ra JSON). Mọi lệnh
còn lại ghi một bước vào phiên đang mở (`out/record-<pkg>.json`).

`allow` và `close-ad` ghi bước **dù màn không có dialog quyền / nút đóng nào** —
đúng ý: chúng là bước "nếu có thì xử", và lượt chạy thật thường khác lượt dò.

`tap`/`swipe` không thấy node thì **báo lỗi và không ghi bước** — cứ `dump` lại
rồi sửa selector, phiên vẫn còn nguyên.

## 3. Selector: chọn cho nó sống được

Ưu tiên `--id` > `--desc` > `--text`. `--text` chạy được nhưng vỡ ngay lần app đổi
ngôn ngữ, nên tool tự in cảnh báo; chỉ dùng khi màn không có `resource_id` nào
dùng được (nút "Add Widget Now" là ca đó).

`--index` là node thứ mấy trong số các node khớp, tính từ 0 — cần thật, không phải
tuỳ chọn cho đẹp: đã gặp một GridView chứa 4 card dùng chung `borderContainer`.

`--optional` cho bước **lúc có lúc không**: quảng cáo xen kẽ, popup, màn onboarding
chỉ hiện ở máy sạch. Bước tuỳ chọn hụt thì case vẫn chạy tiếp và report ghi lại là
đã bỏ qua. Nhờ nó mà một flow chạy được cả máy lần đầu và máy đã dùng rồi.

Ba cái bẫy đo được trên app texttoimage, gặp lại thì đừng mất thời gian dò lại:

- **Đếm indicator trước khi ghim số lần bấm.** Onboarding có 4 trang
  (`indicatorPageOnboarding` 4 dot), cả 4 dùng chung `btnNextOnboarding`, trang
  cuối chỉ đổi chữ thành "Get Started".
- **Bấm ngay sau khi đổi màn là bấm vào không khí.** Chèn `wait 3` giữa hai lần
  bấm liên tiếp, không thì bước sau hụt.
- **Chọn ngôn ngữ phải bấm cả biến thể.** Bấm "English" chỉ mở rộng danh sách con;
  chưa bấm "English (US)" thì chưa tính là đã chọn.

## 4. An toàn — chỗ này quan trọng hơn tốc độ

Máy thật, tài khoản thật. **Không bấm** nút mua/subscribe, không gửi form, không
đăng xuất, không xoá dữ liệu. Gặp paywall thì đóng nó (`close-ad` nhận
"Close Billing Screen"), đừng chọn gói.

Không chắc một nút làm gì thì **hỏi người dùng** trước khi bấm, kèm `dump` của màn
đó. Một câu hỏi rẻ hơn một đơn hàng.

## 5. Chốt case

```
usv-record ... save --event widget_view --label "tại result" --expect placement_name=result
```

- `--event` bắt buộc. `--label` nên có khi một event có nhiều case: mốc mang nhãn
  case, không có nhãn thì 4 cửa sổ của cùng một event không phân biệt được.
- `--expect k=v` là giá trị **lần này phải ra** — chặt hơn spec (spec chỉ nói được
  phép những giá trị nào). Đây là chỗ bắt được lỗi thật: màn Result mà app gửi
  `placement_name=home` thì chấm theo spec là PASS, chấm theo case là FAIL_VALUE.
- `--rc k=v` / `--clear-prefs <file>` chỉ khi trang spec nói rõ vị trí đó bị remote
  key chặn. Đừng với tay tới nó khi một thao tác trên màn đã đủ.

`save` đọc lại case bằng **chính parser của `check`**, sai gì báo ngay tại đây chứ
không để đến lượt chạy thật mới vỡ. Ghi xong: case nối vào `flows/<package>.yaml`
(giữ bản `.bak`), phiên đang mở bị xoá để không dính sang case sau.

Bỏ giữa đường: `usv-record ... drop`.

## 6. Báo lại

In các bước đã chốt (gọi `show` trước khi `save` nếu cần), đường dẫn file flow, và
nói rõ case vừa ghi đo event nào.

Rồi **đề nghị** chạy `/check-event <pkg> <link spec>` để xác nhận flow lái được
thật — nhưng đừng tự chạy: một lượt mất vài phút và người dùng có thể còn muốn ghi
thêm case.

**Không `git add`, không `git commit`.** Lượt ghi flow chỉ sửa `flows/*.yaml`; đưa
vào git là việc của người dùng.
