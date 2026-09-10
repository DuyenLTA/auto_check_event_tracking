// Vong do may: cam may giua chung phai thay, va KHONG duoc ve lai khi danh
// sach khong doi.
//
// Ve lai moi vong se xoa mat app dang chon va bo loc dang go - cu 3 giay mot
// lan thi khong dung noi. Day la phan de sai nhat cua vong do nen phai kiem.
//
// Chay tay:  node scripts/check-device-watch.js
const fs = require('fs');
const dir = require('path').join(__dirname, '..', 'src', 'usv', 'web') + '/';

let handlers_pkg = () => {};
function node(tag) {
  return { innerHTML: '', textContent: '', value: '', hidden: false,
           addEventListener(ev, fn) { if (tag === 'pkg') handlers_pkg = fn; } };
}
global.window = {};
let ticker = null;
global.setInterval = (fn) => { ticker = fn; return 1; };
global.clearInterval = () => { ticker = null; };

let devices = [];
let packageCalls = 0;
global.fetch = async (url) => ({
  ok: true,
  json: async () => {
    if (url.startsWith('/packages')) { packageCalls += 1; return { packages: ['com.a'] }; }
    return { devices };
  },
});

new Function(fs.readFileSync(dir + 'event-api.js', 'utf8'))();
new Function(fs.readFileSync(dir + 'event-device.js', 'utf8'))();

const ui = { device: node(), pkg: node('pkg'), pkgInfo: node(), refresh: node(),
             errorNode: node(), info: node(), pick: node() };
// <select> that: gan innerHTML co option thi value thanh option dau tien.
Object.defineProperty(ui.device, 'innerHTML', {
  set(html) { this._html = html; this.value = (html.match(/value="([^"]*)"/) || [])[1] || ''; },
  get() { return this._html || ''; },
});

const d = window.USV_DEVICE.initDevice(ui);
const fail = (msg) => { console.log('SAI: ' + msg); process.exit(1); };

(async () => {
  // 1. Chua cam may
  await d.loadDevices();
  if (!ui.info.textContent.includes('không thấy máy')) {
    fail(`chua cam may phai noi ro, dang la "${ui.info.textContent}"`);
  }

  d.startWatch();

  // 2. Cam may vao GIUA CHUNG -> vong do phai thay, khong can bam gi
  devices = [{ serial: 'S1', state: 'device', label: 'Pixel 7 (S1)', usable: true }];
  await ticker();
  if (!ui.info.textContent.includes('đã tự nhận')) {
    fail(`cam may giua chung phai tu nhan, dang la "${ui.info.textContent}"`);
  }
  if (ui.pick.hidden !== true) fail('mot may thi phai an o chon');

  // 3. Danh sach khong doi -> KHONG duoc dong vao danh sach app
  const before = packageCalls;
  await ticker();
  await ticker();
  if (packageCalls !== before) {
    fail(`danh sach may khong doi ma van nap lai app ${packageCalls - before} lan `
         + '- se xoa mat app dang chon');
  }

  // 4. Rut may ra -> phai noi ra
  devices = [];
  await ticker();
  if (!ui.info.textContent.includes('không thấy máy')) {
    fail(`rut may phai noi ra, dang la "${ui.info.textContent}"`);
  }

  // 5. Doi chieu package name go bang tay
  ui.pkg.value = 'com.a';
  handlers_pkg();
  if (!ui.pkgInfo.textContent.includes('có trên máy')) {
    fail(`package dung phai xac nhan, dang la "${ui.pkgInfo.textContent}"`);
  }
  ui.pkg.value = 'com.a.go.sai';
  handlers_pkg();
  if (!ui.pkgInfo.textContent.includes('chưa thấy')) {
    fail(`package sai phai canh bao, dang la "${ui.pkgInfo.textContent}"`);
  }
  ui.pkg.value = '';
  handlers_pkg();
  if (ui.pkgInfo.textContent !== '') fail('o rong thi khong noi gi');

  console.log('vong do may + doi chieu package: dung ca 7 truong hop');
})();
