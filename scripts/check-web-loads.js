// Nap 6 file JS cua tab web tren mot DOM gia toi thieu, chi de bat LOI LUC NAP.
//
// Vi sao can: mot loi o tang module (vi du goi mot ham chua he dinh nghia) lam
// TAT CA cac dong phia sau khong chay - nhung trang van hien ra binh thuong,
// file van tra 200, va pytest van xanh. Da gap that: applyMode() duoc goi ma
// khong co than ham, nen deviceUi.loadDevices() cuoi file khong bao gio chay
// va o "dang tim may..." dung nguyen. Curl khong bat duoc loai loi nay.
//
// Chay tay:  node scripts/check-web-loads.js
const fs = require('fs');
const path = require('path').join(__dirname, '..', 'src', 'usv', 'web') + '/';
const html = fs.readFileSync(path + 'index.html', 'utf8');
const ids = new Set([...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1]));

const made = new Map();
function node(id) {
  return { id, innerHTML: '', textContent: '', value: '', hidden: false,
           disabled: false, checked: false,
           addEventListener() {}, setAttribute() {}, removeAttribute() {},
           querySelectorAll: () => [], appendChild() {} };
}
global.document = {
  getElementById(id) {
    if (!ids.has(id)) return null;              // y het browser
    if (!made.has(id)) made.set(id, node(id));
    return made.get(id);
  },
  querySelectorAll: () => [], createElement: () => node('x'),
  addEventListener() {},
};
global.window = {};
global.fetch = async () => ({ ok: true, json: async () => ({ devices: [] }) });
global.setInterval = () => 0;
global.clearInterval = () => {};

const order = ['event-api.js', 'event-device.js',
               'event-spec.js', 'event-artifact.js', 'event-progress.js', 'event-render.js', 'event.js'];
// MOT context dung chung cho ca 7 file - y het trinh duyet nap <script> thuong.
// Bo moi file vao mot new Function() rieng thi moi file co pham vi rieng, va
// bo sot dung loai loi nang nhat: hai file khai trung mot ten o tang ngoai
// cung -> SyntaxError, ca file khong chay. Da gap that voi `renderMarks`.
const vm = require('vm');
const ctx = vm.createContext(global);
for (const f of order) {
  try {
    vm.runInContext(fs.readFileSync(path + f, 'utf8'), ctx, { filename: f });
  } catch (e) {
    console.log(`LOI khi nap ${f}:\n  ${e.constructor.name}: ${e.message}`);
    process.exit(1);
  }
}
console.log(`nap het ${order.length} file, khong loi`);
