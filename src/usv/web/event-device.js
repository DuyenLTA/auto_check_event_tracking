/* Buoc 2: chon may va app.
 *
 * Danh sach app loc bang o text vi may test co hang chuc app - cuon tim trong
 * <select> 85 dong thi khong dung duoc.
 */
'use strict';

/* Boc IIFE de khong ro ten ra pham vi toan cuc - xem event-marks.js. */
(() => {

const { api: dApi, fail: dFail } = window.USV_API;
const { escapeHtml: dEsc } = window.USV_MARKS;

function initDevice({ device, pkg, pkgFilter, refresh, errorNode, info, pick,
                     onReady }) {
  let allPackages = [];

  /* Mot may thi TU CHON, khong bat nguoi dung cham vao. O chon chi hien khi
   * that su co gi de chon - hau het luc chi cam mot may, hien mot <select>
   * mot dong la bat bam mot cai vo nghia. */
  function show(devices) {
    const usable = devices.filter((d) => d.usable);
    pick.hidden = devices.length < 2;
    if (!devices.length) {
      info.textContent = 'không thấy máy nào — cắm máy rồi bấm Tìm lại máy';
      return;
    }
    if (usable.length === 1 && devices.length === 1) {
      info.textContent = `đã tự nhận: ${usable[0].label}`;
      return;
    }
    const bad = devices.filter((d) => !d.usable)
      .map((d) => `${d.label} (${d.state})`);
    info.textContent = usable.length
      ? `${devices.length} máy đang cắm — chọn một`
      : `máy chưa dùng được: ${bad.join(', ')}`;
  }

  function render(devices) {
    device.innerHTML = devices
      .map((d) => `<option value="${dEsc(d.serial)}"${d.usable ? '' : ' disabled'}>`
        + `${dEsc(d.label)}${d.usable ? '' : ' — ' + dEsc(d.state)}</option>`)
      .join('') || '<option value="">không thấy máy nào</option>';
    show(devices);
  }

  async function loadDevices() {
    info.textContent = 'đang tìm máy…';
    try {
      const devices = (await dApi('/devices')).devices || [];
      signature = devices.map((d) => `${d.serial}:${d.state}`).join(',');
      render(devices);
      if (device.value) await loadPackages();
      onReady?.();
    } catch (error) {
      info.textContent = '';
      dFail(errorNode, error.message);
    }
  }

  async function loadPackages() {
    try {
      const data = await dApi(`/packages?serial=${encodeURIComponent(device.value)}`);
      allPackages = data.packages || [];
      renderPackages();
    } catch (error) {
      dFail(errorNode, error.message);
    }
  }

  function renderPackages() {
    const needle = pkgFilter.value.toLowerCase();
    const list = allPackages.filter((p) => p.includes(needle));
    pkg.innerHTML = list
      .map((p) => `<option value="${dEsc(p)}">${dEsc(p)}</option>`).join('')
      || '<option value="">không có app nào khớp</option>';
  }

  /* Do LIEN TUC: cam may luc nao la thay luc do, khong bat bam nut.
   *
   * Chi ve lai khi DANH SACH MAY DOI THAT. Ve lai moi vong se nap lai danh
   * sach app va xoa mat app dang chon cung cai bo loc dang go - cu 3 giay
   * mot lan thi khong dung noi.
   */
  const WATCH_MS = 3000;
  let timer = null;
  let signature = null;

  async function tick() {
    let devices;
    try {
      devices = (await dApi('/devices')).devices || [];
    } catch (error) {
      return;                  // adb chop chop - vong sau thu lai
    }
    const now = devices.map((d) => `${d.serial}:${d.state}`).join(',');
    if (now === signature) return;
    signature = now;
    render(devices);
    if (device.value) await loadPackages();
  }

  function startWatch() {
    if (timer === null) timer = setInterval(tick, WATCH_MS);
  }

  function stopWatch() {
    if (timer !== null) { clearInterval(timer); timer = null; }
  }

  refresh.addEventListener('click', loadDevices);
  device.addEventListener('change', loadPackages);
  pkgFilter.addEventListener('input', renderPackages);
  return { loadDevices, startWatch, stopWatch };
}

window.USV_DEVICE = { initDevice };
})();
