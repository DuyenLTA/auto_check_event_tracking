/* Buoc 2: chon may va app.
 *
 * Danh sach app loc bang o text vi may test co hang chuc app - cuon tim trong
 * <select> 85 dong thi khong dung duoc.
 */
'use strict';

const { api: dApi, fail: dFail } = window.USV_API;
const { escapeHtml: dEsc } = window.USV_MARKS;

function initDevice({ device, pkg, pkgFilter, refresh, errorNode, onReady }) {
  let allPackages = [];

  async function loadDevices() {
    try {
      const data = await dApi('/devices');
      device.innerHTML = data.devices
        .map((d) => `<option value="${dEsc(d.serial)}"${d.usable ? '' : ' disabled'}>`
          + `${dEsc(d.label)}${d.usable ? '' : ' — ' + dEsc(d.state)}</option>`)
        .join('') || '<option value="">không thấy máy nào</option>';
      if (device.value) await loadPackages();
      onReady?.();
    } catch (error) {
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
