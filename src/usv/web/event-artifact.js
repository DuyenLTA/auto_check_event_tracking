/* Nut link bao cao: local (luon la luot vua cham) va artifact (gui cho team).
 *
 * Tool KHONG publish duoc artifact - no chay o 127.0.0.1, khong co duong nao
 * toi claude.ai. Claude publish xong thi POST /event/artifact, o day chi doc
 * lai URL da ghi.
 *
 * Phan quan trong nhat la noi ro artifact dang la LUOT NAO: gui cho team mot
 * bao cao cu ma tuong moi la kieu sai im lang.
 */
'use strict';

/* Boc IIFE de khong ro ten ra pham vi toan cuc - xem event-marks.js. */
(() => {

const { api: aApi } = window.USV_API;
const { escapeHtml: aEsc } = window.USV_MARKS;

function initArtifact({ link, info }) {
  async function show() {
    let data;
    try {
      data = await aApi('/event/artifact');
    } catch (error) {
      return;                      // tien nghi thoi, khong lam sap gi
    }
    if (!data.url) {
      link.hidden = true;
      info.textContent = '';
      return;
    }
    link.href = data.url;
    link.hidden = false;
    // Chua cham luot nao thi KHONG bao "luot cu": khong co gi de so, va bao
    // vay lam nguoi doc tuong artifact da lac hau so voi mot luot nao do.
    if (!data.run_generated_at) {
      info.textContent = `artifact: lượt ${data.generated_at || '?'}`;
    } else if (data.khop) {
      info.textContent = 'artifact = lượt này';
    } else {
      info.innerHTML = '<b>artifact là lượt cũ</b> ('
        + aEsc(data.generated_at || '?')
        + ') — xem report local cho lượt vừa chấm';
    }
  }

  function clear() {
    link.hidden = true;
    info.textContent = '';
  }

  return { show, clear };
}

window.USV_ARTIFACT = { initArtifact };
})();
