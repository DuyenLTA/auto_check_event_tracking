export const meta = {
  name: 'spec-to-cases',
  description: 'Doc trang spec Confluence roi sinh khung case test, co doi chieu lai voi bang event',
  whenToUse: 'Truoc khi viet flow cho mot app: bien van xuoi Requirements thanh danh sach case',
  phases: [
    { title: 'Doc spec', detail: 'agent doc van xuoi -> khung case' },
    { title: 'Doi chieu', detail: 'Python so case voi bang event, agent sua neu sai' },
  ],
}

// Tang A cua ba tang. Tang nay KHONG dung toi may that va KHONG sinh `steps`:
// spec noi event nao phai ban va ban khi nao, no khong noi nut Continue nam o
// dau. Steps la viec cua tang B (dò trên máy), verdict la viec cua tang C
// (event_flow_run + event_check_runner).
//
// Vi sao dang lam rieng mot tang: trang spec la tai lieu SDK dung chung cho
// nhieu app, nen khung case sinh ra o day xai lai duoc cho moi app dung SDK do.
// Chi `steps` moi rieng tung app.
//
//   args: { url: 'https://confluence.../display/VL/...', repoDir: '/duong/dan' }
//
// Bien moi truong CONFLUENCE_BASE_URL + CONFLUENCE_TOKEN phai co san; CLI se
// bao ro neu thieu.

const repoDir = args?.repoDir ?? '.'
const url = args?.url ?? ''
const out = args?.out ?? 'out/cases.json'
// Pham vi cua luot sinh, do nguoi goi dat. Vi du "chi happy case, moi remote
// key bat/tat deu BAT". De trong thi agent phu het moi nhanh trang mo ta -
// ke ca nhanh tat man, tat banner, ma nhieu luot chay khong can toi.
const ghiChu = args?.ghiChu ?? ''

if (!url) {
  // Khong co url thi agent se di doan mot trang nao do, va mot khung case sinh
  // tu nham trang thi sai im lang - moi dong deu hop le, chi la cua app khac.
  throw new Error('Chua co trang spec: truyen args.url la link Confluence.')
}

const PY = `cd ${repoDir} && PYTHONPATH=src .venv/bin/python -m usv.spec_cases_cli`

const CASES_SCHEMA = {
  type: 'object',
  required: ['cases', 'da_ghi_file'],
  properties: {
    da_ghi_file: { type: 'string' },
    cases: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'event', 'expect_params', 'precondition', 'reset', 'source'],
        properties: {
          id: { type: 'string' },
          event: { type: 'string' },
          expect_params: { type: 'object' },
          precondition: { type: 'string', maxLength: 400 },
          reset: { type: 'string', enum: ['none', 'relaunch', 'pm_clear'] },
          remote_config: { type: 'object' },
          sau: { type: 'string' },
          burns_popup: { type: 'boolean' },
          blocked_by: { type: 'array', items: { type: 'string' } },
          source: { type: 'string', maxLength: 200 },
        },
      },
    },
  },
}

const CHECK_SCHEMA = {
  type: 'object',
  required: ['exit_code', 'output'],
  properties: { exit_code: { type: 'number' }, output: { type: 'string' } },
}

const PHAM_VI = ghiChu ? `
PHAM VI LUOT NAY (nguoi goi dat, uu tien hon moi huong dan khac o duoi):
${ghiChu}
` : ''

const LUAT = `${PHAM_VI}
Doc trang spec bang lenh nay (no lo phan dang nhap va cat muc san):
  ${PY} dump "${url}"

Nhiem vu: bien van xuoi thanh KHUNG CASE. Moi case la mot lan lai app toi mot
trang thai roi cho DUNG MOT event ban ra.

TUYET DOI KHONG sinh 'steps'. Spec khong he noi nut nao nam o dau; doan buoc
bam la bia. Steps do tang sau dò trên máy that moi biet.

Moi truong cua mot case:
  id             ten ngan, khong dau, phan biet duoc (vi du viewed-home)
  event          PHAI lay nguyen van tu bang Event tracking cua trang
  expect_params  gia tri case nay KHANG DINH phai ra. Spec noi "duoc phep 1
                 trong 4 gia tri"; case lai app toi dung mot cho nen no biet
                 lan nay PHAI ra gia tri nao. Gia tri phai nam trong cot Value
  precondition   dieu kien de event ban, lay tu van xuoi. Vi du "tu session 2
                 tro di", "hien 1 lan/session", "xep sau popup FSI va man
                 Widget", "nut Rate disable cho toi khi chon sao"
  reset          none | relaunch | pm_clear - xem duoi
  sau            id cua case ma case nay chay tiep trang thai cua no. BAT BUOC
                 khi reset la 'none'. Khong khai thi thu tu chay nam o thu tu
                 dong trong file, ma doi cho hai dong la case chay tren mot man
                 hinh khac roi bao "Chua test" - hong ma khong bao loi
  remote_config  gia tri remote config PHAI co truoc khi chay case. Day la
                 TIEN DE, khong phai thu de kiem. Ten key phai lay tu bang
                 Remote Key cua trang. DUNG khai lai gia tri o cot Default
                 Value: khai lai khong doi gi, chi bien mot case chay duoc
                 thanh case phai sua Remote Config - tren build khong
                 debuggable la thanh BLOCKED oan. De trong khi mac dinh da dung
  burns_popup    true neu case nay lam popup TAT VINH VIEN (vi du spec noi
                 "khong hien pop-up rating khi user da bam rate")
  blocked_by     remote key co the chan case nay khong chay duoc
  source         muc nao cua trang noi dieu do

Chon reset:
  none      case chay tiep tren trang thai case truoc de lai - PHAI khai 'sau'
  relaunch  force-stop + mo lai app. Du cho thu "1 lan moi session"
  pm_clear  xoa sach data app. Duong duy nhat go duoc trang thai vinh vien,
            doi lai mat login va phai di lai onboarding. DAT khi burns_popup

Khi nao can remote_config: CHI khi trang noi ro mot vi tri bi mot remote key
chan. Doi cau hinh la viec nang; dung voi tay toi no khi mot thao tac tren man
hinh da du. Doi remote config thi BAT BUOC reset la relaunch hoac pm_clear:
app chi doc gia tri moi luc process start.

Nhieu vi tri co the dung CHUNG mot phien - dung mac dinh moi case mot phien.
Do duoc tren may that: popup o 'home' tu hien, tap RA NGOAI cho no tat (dung
bam RATE - bam la tat vinh vien), roi bam back tren thanh dieu huong thi popup
o 'exit_click' hien ra. Mot phien ghi, hai cua so, khong doi cau hinh gi.

Hai nguyen tac:
1. Dung bo qua dieu kien chi nam o van xuoi. Bang event chi noi event ten gi;
   cai lam case that bai oan nam o muc Requirements va bang Remote Key.
2. Dung bia event hay gia tri khong co trong bang. Buoc doi chieu sau se bat
   duoc, nhung moi lan bat duoc la mot vong lam lai.
`

phase('Doc spec')
const sinh = await agent(`${LUAT}

Doc trang, sinh khung case phu HET moi gia tri bang event khai (moi gia tri
trong cot Value phai co it nhat mot case khang dinh no).

Ghi mang JSON cac case ra file ${repoDir}/${out} (tao thu muc neu chua co),
roi tra ve chinh mang do kem duong dan file da ghi.`,
  { label: 'sinh-khung-case', phase: 'Doc spec', schema: CASES_SCHEMA })

if (!sinh || !sinh.cases?.length) {
  log('Agent khong sinh duoc case nao.')
  return { cases: 0 }
}
log(`${sinh.cases.length} case, da ghi ${sinh.da_ghi_file}`)

phase('Doi chieu')
let kiem = await agent(`Chay dung mot lenh nay roi tra ve exit code va toan bo output:
  ${PY} check ${out} --url "${url}"
Khong sua file, khong giai thich them.`,
  { label: 'doi-chieu', phase: 'Doi chieu', schema: CHECK_SCHEMA })

// Mot vong sua. Nhieu hon mot vong thi thuong khong phai agent cau tha ma la
// spec that su mo ho - luc do dua cho nguoi doc con re hon vong tiep.
if (kiem && kiem.exit_code !== 0) {
  log('Co case sai, cho agent sua mot vong.')
  await agent(`${LUAT}

File ${repoDir}/${out} co case khong khop bang spec. Ket qua doi chieu:

${kiem.output}

Sua dung nhung dong bi bao, giu nguyen cac case da dat. Phan "Bỏ sót" la gia
tri spec khai ma chua case nao khang dinh - them case cho chung, tru khi spec
noi ro gia tri do khong test duoc.

Ghi de lai file roi dung lai, khong can giai thich.`,
    { label: 'sua-khung-case', phase: 'Doi chieu' })

  kiem = await agent(`Chay lai dung lenh nay, tra ve exit code va output:
  ${PY} check ${out} --url "${url}"`,
    { label: 'doi-chieu-lai', phase: 'Doi chieu', schema: CHECK_SCHEMA })
}

return {
  cases: sinh.cases.length,
  file: sinh.da_ghi_file,
  dat: kiem?.exit_code === 0,
  doi_chieu: kiem?.output ?? '',
}
