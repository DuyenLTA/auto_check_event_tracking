export const meta = {
  name: 'triage-event-fail',
  description: 'Soi nguyen nhan tung dong FAIL cua lan cham event tracking, co phan bien, roi ghi vao report',
  whenToUse: 'Sau khi bam Cham va report co it nhat mot dong FAIL',
  phases: [
    { title: 'Doc luot cham', detail: 'lay danh sach FAIL + event app that su ban' },
    { title: 'Soi', detail: 'mot agent moi dong FAIL' },
    { title: 'Phan bien', detail: 'hai agent doc lap thu bac bo tung ket luan' },
    { title: 'Ghi vao report', detail: 'POST /event/triage' },
  ],
}

const BASE = 'http://127.0.0.1:8000'

const CTX_SCHEMA = {
  type: 'object',
  required: ['generated_at', 'fails', 'ten_app_ban'],
  properties: {
    generated_at: { type: 'string' },
    package: { type: 'string' },
    fails: { type: 'array', items: { type: 'string' } },
    ten_app_ban: { type: 'array', items: { type: 'string' } },
    ghi_chu_phien: { type: 'string' },
  },
}

const NOTE_SCHEMA = {
  type: 'object',
  required: ['element', 'ket_luan', 'ly_do'],
  properties: {
    element: { type: 'string' },
    ket_luan: {
      type: 'string',
      enum: ['app_thieu', 'app_doi_ten', 'spec_cu', 'chua_thao_tac', 'khong_do_duoc'],
    },
    ly_do: { type: 'string', maxLength: 380 },
    bang_chung: { type: 'string', maxLength: 280 },
  },
}

const PHAN_BIEN_SCHEMA = {
  type: 'object',
  required: ['bac_bo', 'ly_do'],
  properties: {
    bac_bo: { type: 'boolean' },
    ly_do: { type: 'string', maxLength: 300 },
  },
}

const LUAT = `
Cong cu chay o ${BASE}. Dung Bash + curl. TUYET DOI KHONG goi
POST /event/check - no cham lai va doi generated_at, lam hong chot chan cua
buoc ghi ket qua.

Duong doc duoc phep:
  GET ${BASE}/event/run        -> ket qua luot cham (results, fails, spec, co ca
                                  fa_silent / stream_died / app_seen)
  GET ${BASE}/event/observed   -> event app THAT SU ban: bang ten + so lan + gio

Hai con so event, DUNG nham:
  /event/observed -> tong_app       : event origin=app, tuc pham vi bang spec
  /event/observed -> tong_ca_phien  : ke ca event Firebase tu ban (auto/am)
  /event/run      -> event_count    : bang tong_ca_phien
Chenh lech giua hai so la BINH THUONG, khong phai log bi cat. Muon biet log co
bi cat that khong thi xem stream_died va fa_silent trong /event/run.

Nam ket luan, dung dung ma nay:
  app_thieu      App co chay toi buoc do ma khong ban event -> bug that.
  app_doi_ten    App ban mot event TEN KHAC cho dung viec do (vi du spec ghi
                 daily_checkin_shown ma app ban daily_checkin_screen_view).
  spec_cu        Spec con khai thu app da bo tu lau.
  chua_thao_tac  Phien ghi khong he di toi man do (vi du dung o splash, ket o
                 quang cao, chua dang nhap). Event khong ban la DUNG.
  khong_do_duoc  Log bi cat, phien dut, build strip log Firebase...

VIET TIENG VIET CO DAU trong 'ly_do'. Doan chu do in THANG vao bao cao gui
cho dev doc - tieng Viet khong dau la loi trinh bay, va bao cao trong cau tha
thi noi dung dung cung bi coi nhe. Rieng 'bang_chung' duoc phep de nguyen ten
event / gio / screen_class dang ASCII vi do la du lieu tho.

Nguyen tac quan trong nhat: KHONG DOAN BUA. Ghi chu nay in thang vao bao cao
gui cho dev. Mot ket luan "app thieu event" sai khien dev di tim mot bug khong
ton tai, va lan sau khong ai tin bao cao nua. Khong du bang chung thi chon
chua_thao_tac hoac khong_do_duoc - do la cau tra loi trung thuc, khong phai
cau tra loi yeu.
`

phase('Doc luot cham')
const ctx = await agent(`${LUAT}

Doc GET /event/run va GET /event/observed. Tra ve:
- generated_at, package
- fails: danh sach element dang FAIL (lay nguyen van tu truong "fails")
- ten_app_ban: ten cac event app that su ban trong phien
- ghi_chu_phien: mot cau mo ta phien ghi nay di toi dau (vi du "chi toi splash
  va quang cao, khong vao duoc man chinh")`,
  { label: 'doc-luot-cham', phase: 'Doc luot cham', schema: CTX_SCHEMA })

if (!ctx || !ctx.fails.length) {
  log('Khong co dong FAIL nao - khong co gi de soi.')
  return { fails: 0 }
}
log(`${ctx.fails.length} dong FAIL. App ban: ${ctx.ten_app_ban.join(', ')}`)

const ket_qua = await pipeline(
  ctx.fails,

  // 1. mot agent soi mot dong
  (element) => agent(`${LUAT}

Soi dong FAIL nay: "${element}"
Phien ghi: ${ctx.ghi_chu_phien}
App that su ban: ${ctx.ten_app_ban.join(', ')}

Doc them /event/run va /event/observed neu can. So sanh ten trong spec voi cac
ten app that su ban - gan giong nhau la dau hieu doi ten. Xem gio bắn de biet
phien di toi dau.

Tra ve ket luan kem ly_do ngan gon cho nguoi doc, va bang_chung la thu kiem lai
duoc (ten event thay the + gio, hoac gio cua event cuoi cung trong phien).`,
    { label: `soi:${element}`, phase: 'Soi', schema: NOTE_SCHEMA }),

  // 2. hai agent doc lap thu BAC BO ket luan do
  (note, element) => {
    if (!note) return null
    const goc = ['Tim bang chung NGUOC LAI trong log',
                 'Kiem xem ket luan nay co the giai thich kieu khac khong']
    return parallel(goc.map((cach, i) => () =>
      agent(`${LUAT}

Mot agent khac vua ket luan ve dong FAIL "${element}":
  ket_luan  = ${note.ket_luan}
  ly_do     = ${note.ly_do}
  bang_chung= ${note.bang_chung || '(khong co)'}

Viec cua ban la THU BAC BO no, khong phai xac nhan. ${cach}.
Tu kiem lai bang /event/run va /event/observed.

bac_bo = true neu ket luan do sai hoac khong du bang chung.
Khi phan van thi nghieng ve bac_bo - ghi chu sai gay hai hon ghi chu thieu.`,
        { label: `phan-bien-${i + 1}:${element}`, phase: 'Phan bien',
          schema: PHAN_BIEN_SCHEMA })))
      .then((phieu) => {
        const co = phieu.filter(Boolean)
        const dong_y = co.filter((v) => !v.bac_bo).length
        return { note, dong_y, tong: co.length,
                 qua: co.length > 0 && dong_y > co.length / 2 }
      })
  },
)

const song = ket_qua.filter(Boolean)
const giu = song.filter((r) => r.qua)
const bo = song.length - giu.length
const chet = ctx.fails.length - song.length
log(`${giu.length} ghi chu qua phan bien, ${bo} bi bac bo, ${chet} agent khong tra ve`)

phase('Ghi vao report')
const notes = giu.map((r) => ({ ...r.note, dong_y: r.dong_y, tong: r.tong }))
const bo_sot = ctx.fails.length - notes.length

const gui = await agent(`${LUAT}

POST ${BASE}/event/triage voi body JSON duoi day, NGUYEN VAN, khong sua gi:

${JSON.stringify({ generated_at: ctx.generated_at, notes, bo_sot }, null, 2)}

Dung: curl -s -X POST ${BASE}/event/triage -H 'Content-Type: application/json' -d @<file>
Ghi body ra file tam roi gui bang -d @file - tranh loi thoat chuoi.

Tra ve nguyen van response cua server. Neu server tra 4xx thi tra ve luon
thong bao loi do, DUNG tu sua du lieu roi thu lai.`,
  { label: 'ghi-vao-report', phase: 'Ghi vao report' })

return {
  fails: ctx.fails.length,
  da_ghi: notes.length,
  bi_bac_bo: bo,
  bo_sot,
  ket_luan: notes.map((n) => `${n.element}: ${n.ket_luan} (${n.dong_y}/${n.tong})`),
  server: gui,
}
