/* Buoc 2: chon may va app.
 *
 * Danh sach app loc bang o text vi may test co hang chuc app - cuon tim trong
 * <select> 85 dong thi khong dung duoc.
 */
'use strict';

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

  async function loadDevices() {
    info.textContent = 'đang tìm máy…';
    try {
      const data = await dApi('/devices');
      const devices = data.devices || [];
      device.innerHTML = devices
        .map((d) => `<option value="${dEsc(d.serial)}"${d.usable ? '' : ' disabled'}>`
          + `${dEsc(d.label)}${d.usable ? '' : ' — ' + dEsc(d.state)}</option>`)
        .join('') || '<option value="">không thấy máy nào</option>';
      show(devices);
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

  refresh.addEventListener('click', loadDevices);
  device.addEventListener('change', loadPackages);
  pkgFilter.addEventListener('input', renderPackages);
  return { loadDevices };
}

window.USV_DEVICE = { initDevice };
