// MOT nut xem bao cao, va no phai tro vao LUOT VUA CHAM.
//
// Vi sao phai kiem bang node: hai nut an/hien theo trang thai mang, ma curl tra
// 200 thi khong noi gi ve viec nut nao dang hien. Loi hay gap nhat la hien CA
// HAI (nguoi doc phai tu doan cai nao moi) hoac hien artifact CU (gui bao cao
// cu cho team, sai trong im lang).
//
// Chay tay:  node scripts/check-artifact-button.js
const fs = require('fs');
const dir = require('path').join(__dirname, '..', 'src', 'usv', 'web') + '/';

function node() { return { href: '', hidden: true }; }
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
  // 1. Chua publish -> chi co nut local
  let t = moiLuot([{ khop: false, run_generated_at: '16:54' }]);
  await t.a.show();
  motNutThoi(t.link, t.local, 'chua publish');
  if (t.local.hidden) fail('chua publish thi phai hien nut report local');

  // 2. Artifact la LUOT CU -> KHONG duoc hien nut artifact
  t = moiLuot([{ url: 'https://x/cu', khop: false, generated_at: '16:46',
                 run_generated_at: '16:54' }]);
  await t.a.show();
  motNutThoi(t.link, t.local, 'artifact luot cu');
  if (!t.link.hidden) fail('artifact luot cu ma van hien - se gui bao cao cu cho team');

  // 3. Artifact DA la luot nay -> hien artifact, an local
  t = moiLuot([{ url: 'https://x/moi', khop: true, run_generated_at: '16:54' }]);
  await t.a.show();
  motNutThoi(t.link, t.local, 'artifact luot nay');
  if (t.link.hidden) fail('artifact khop luot nay ma khong hien');
  if (t.link.href !== 'https://x/moi') fail(`href sai: ${t.link.href}`);

  // 4. Publish den SAU khi cham -> vong do phai tu doi nut, khong can F5
  t = moiLuot([
    { khop: false, run_generated_at: '16:54' },                       // luc bam Cham
    { url: 'https://x/moi', khop: true, run_generated_at: '16:54' },  // 3 giay sau
  ]);
  await t.a.show();
  if (!t.link.hidden) fail('luc bam Cham chua co artifact ma da hien');
  await tick();
  if (t.link.hidden) fail('publish xong roi ma nut khong tu doi - phai F5 moi thay');
  if (!t.local.hidden) fail('doi sang artifact roi ma nut local con hien');

  // 5. Khop roi thi DUNG do - khong duoc poll mai
  if (hen !== null) fail('da khop ma van hen do tiep');

  // 6. Lam lai -> an het, va huy vong do dang cho
  t = moiLuot([{ khop: false, run_generated_at: '16:54' }]);
  await t.a.show();
  t.a.clear();
  if (!t.link.hidden || !t.local.hidden) fail('Lam lai phai an het nut');
  if (hen !== null) fail('Lam lai ma vong do con hen - se hien lai nut cua luot cu');

  console.log('OK: nut xem bao cao chay dung');
})();
