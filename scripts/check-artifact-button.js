// MOT nut xem bao cao, va no phai tro vao LUOT VUA CHAM.
//
// Vi sao phai kiem bang node: nut an/hien va co/khong co href theo trang thai
// mang, ma curl tra 200 thi khong noi gi ve viec nut nao dang hien. Hai loi
// hay gap: hien CA HAI nut (nguoi doc phai tu doan cai nao moi), va cho bam
// sang artifact CU (gui bao cao cu cho team, sai trong im lang).
//
// Bat bien so mot kiem theo HREF chu khong theo an/hien: nut artifact CO hien
// luc dang doi publish - de nguoi dung biet co cai gi dang tren duong - nhung
// luc do no khong duoc co href, vi href duy nhat co san la cua luot truoc.
//
// Chay tay:  node scripts/check-artifact-button.js
const fs = require('fs');
const dir = require('path').join(__dirname, '..', 'src', 'usv', 'web') + '/';

function node() {
  return {
    href: '', hidden: true, textContent: '', attrs: {},
    setAttribute(ten, giaTri) {
      this.attrs[ten] = String(giaTri);
      if (ten === 'href') this.href = String(giaTri);
    },
    removeAttribute(ten) {
      delete this.attrs[ten];
      if (ten === 'href') this.href = '';
    },
    getAttribute(ten) { return ten in this.attrs ? this.attrs[ten] : null; },
  };
}
global.window = {};

// Cac lan tra ve lien tiep cua GET /event/artifact.
let lanTra = [];
let daGoi = 0;
global.fetch = async () => ({
  ok: true,
  json: async () => lanTra[Math.min(daGoi++, lanTra.length - 1)],
});

// Dieu khien setTimeout bang tay: cho nhip 3 giay that thi test cham vo ich.
let hen = null;
global.setTimeout = (fn) => { hen = fn; return 1; };
global.clearTimeout = () => { hen = null; };
const tick = async () => { const fn = hen; hen = null; if (fn) await fn(); };

new Function(fs.readFileSync(dir + 'event-api.js', 'utf8'))();
new Function(fs.readFileSync(dir + 'event-artifact.js', 'utf8'))();

const fail = (msg) => { console.log('SAI: ' + msg); process.exit(1); };

function moiLuot(traVe) {
  lanTra = traVe; daGoi = 0; hen = null;
  const link = node(), local = node();
  const a = window.USV_ARTIFACT.initArtifact({ link, local });
  return { a, link, local };
}

function motNutThoi(link, local, canh) {
  if (!link.hidden && !local.hidden) fail(`${canh}: hien CA HAI nut`);
  if (link.hidden && local.hidden) fail(`${canh}: khong hien nut nao`);
}

(async () => {
  // 1. Chua publish -> hien nut artifact o trang thai doi, va KHONG co href.
  //    Truoc day cho nay hien nut local; doi thanh nut doi de nguoi dung biet
  //    artifact dang tren duong chu khong phai khong co.
  let t = moiLuot([{ khop: false, run_generated_at: '16:54' }]);
  await t.a.show();
  motNutThoi(t.link, t.local, 'chua publish');
  if (t.link.hidden) fail('chua publish thi phai hien nut o trang thai doi');
  if (t.link.href !== '') fail('luc doi ma da co href - se bam sang bao cao cu');
  if (t.link.getAttribute('aria-disabled') !== 'true') {
    fail('nut luc doi phai danh dau aria-disabled, khong thi trong nhu bam duoc');
  }
  if (!t.link.textContent) fail('nut luc doi phai co chu, khong duoc de trong');

  // 2. Artifact la LUOT CU -> tuyet doi khong co href tro sang no
  t = moiLuot([{ url: 'https://x/cu', khop: false, generated_at: '16:46',
                 run_generated_at: '16:54' }]);
  await t.a.show();
  motNutThoi(t.link, t.local, 'artifact luot cu');
  if (t.link.href !== '') fail('artifact luot cu ma co href - se gui bao cao cu cho team');

  // 3. Artifact DA la luot nay -> hien artifact, an local
  t = moiLuot([{ url: 'https://x/moi', khop: true, run_generated_at: '16:54' }]);
  await t.a.show();
  motNutThoi(t.link, t.local, 'artifact luot nay');
  if (t.link.hidden) fail('artifact khop luot nay ma khong hien');
  if (t.link.href !== 'https://x/moi') fail(`href sai: ${t.link.href}`);
  if (t.link.getAttribute('aria-disabled') !== null) fail('khop roi ma nut con bi khoa');

  // 4. Publish den SAU khi cham -> vong do phai tu gan href, khong can F5
  t = moiLuot([
    { khop: false, run_generated_at: '16:54' },                       // luc bam Cham
    { url: 'https://x/moi', khop: true, run_generated_at: '16:54' },  // 3 giay sau
  ]);
  await t.a.show();
  if (t.link.href !== '') fail('luc bam Cham chua co artifact ma da co href');
  await tick();
  if (t.link.href !== 'https://x/moi') fail('publish xong roi ma nut khong tu doi - phai F5 moi thay');
  if (!t.local.hidden) fail('doi sang artifact roi ma nut local con hien');

  // 5. Khop roi thi DUNG do - khong duoc poll mai
  if (hen !== null) fail('da khop ma van hen do tiep');

  // 6. Doi mai khong xong -> tra nut local lai, de con duong xem bao cao
  t = moiLuot([{ khop: false, run_generated_at: '16:54' }]);
  await t.a.show();
  for (let i = 0; i < 25 && hen !== null; i += 1) await tick();
  motNutThoi(t.link, t.local, 'doi qua lau');
  if (t.local.hidden) fail('doi mai khong xong thi phai tra nut report local lai');
  if (hen !== null) fail('het luot do ma van hen tiep');

  // 7. Lam lai -> an het, va huy vong do dang cho
  t = moiLuot([{ khop: false, run_generated_at: '16:54' }]);
  await t.a.show();
  t.a.clear();
  if (!t.link.hidden || !t.local.hidden) fail('Lam lai phai an het nut');
  if (hen !== null) fail('Lam lai ma vong do con hen - se hien lai nut cua luot cu');

  console.log('OK: nut xem bao cao chay dung');
})();
