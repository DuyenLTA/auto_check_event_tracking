/* Nut xem bao cao: MOT nut duy nhat, va no luon tro vao LUOT VUA CHAM.
 *
 * Tool KHONG publish duoc artifact - no chay o 127.0.0.1, khong co duong nao
 * toi claude.ai. Claude publish xong thi POST /event/artifact, o day chi doc
 * lai URL da ghi.
 *
 * Vi sao mot nut chu khong hai: hai nut "Xem report" va "Link artifact" canh
 * nhau bat nguoi doc phai tu doan cai nao la luot moi. Nen o day chon san:
 *   artifact DA la luot nay -> hien "Link artifact", an nut local
 *   chua co / con la luot cu -> hien "Xem report" (local, chac chan la luot
 *                               nay), an nut artifact
 * Khong bao gio hien mot artifact CU: gui cho team bao cao cu ma tuong moi la
 * kieu sai im lang.
 *
 * Publish mat vai giay sau khi bam Cham, nen phai DO LAI vai lan - khong thi
 * nguoi dung phai F5 moi thay nut doi.
 */
'use strict';

/* Boc IIFE de khong ro ten ra pham vi toan cuc - xem event-marks.js. */
(() => {

const { api: aApi } = window.USV_API;

const NHIP_MS = 3000;      // moi lan do cach nhau bao lau
const SO_LAN = 20;         // ~60 giay; publish lau hon the thi coi nhu khong co

function initArtifact({ link, local }) {
  let hen = null;          // setTimeout dang cho, de huy duoc

  function huyHen() {
    if (hen !== null) { clearTimeout(hen); hen = null; }
  }

  function dat(khop, url) {
    if (khop && url) {
      link.href = url;
      link.hidden = false;
      local.hidden = true;
    } else {
      link.hidden = true;
      local.hidden = false;
    }
  }

  /* Tra ve true khi artifact da la luot nay -> khong can do nua. */
  async function doMotLan() {
    let data;
    try {
      data = await aApi('/event/artifact');
    } catch (error) {
      dat(false, '');        // tien nghi thoi, khong lam sap gi
      return false;
    }
    const khop = Boolean(data.url) && data.khop === true;
    dat(khop, data.url);
    return khop;
  }

  async function show() {
    huyHen();
    local.hidden = false;    // luon co cai de bam ngay, khong doi mang
    if (await doMotLan()) return;
    let conLai = SO_LAN;
    const lap = async () => {
      hen = null;
      if (conLai-- <= 0) return;
      if (await doMotLan()) return;
      hen = setTimeout(lap, NHIP_MS);
    };
    hen = setTimeout(lap, NHIP_MS);
  }

  function clear() {
    huyHen();
    link.hidden = true;
    local.hidden = true;
  }

  return { show, clear };
}

window.USV_ARTIFACT = { initArtifact };
})();
