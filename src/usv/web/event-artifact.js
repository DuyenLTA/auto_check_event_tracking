/* Nut xem bao cao: MOT nut duy nhat, va no luon tro vao LUOT VUA CHAM.
 *
 * Tool KHONG publish duoc artifact - no chay o 127.0.0.1, khong co duong nao
 * toi claude.ai. Claude publish xong thi POST /event/artifact, o day chi doc
 * lai URL da ghi.
 *
 * Vi sao mot nut chu khong hai: hai nut "Xem report" va "Link artifact" canh
 * nhau bat nguoi doc phai tu doan cai nao la luot moi. Nen nut artifact la nut
 * CHINH, va no di qua ba trang thai:
 *   artifact DA la luot nay -> "Link artifact", co href, an nut local
 *   dang doi Claude publish  -> "Dang publish artifact..." mo di, KHONG href
 *   doi qua lau van chua co  -> an nut artifact, con lai nut local
 *
 * Luon dung MOT nut: hien ca hai thi nguoi doc phai tu doan cai nao la luot
 * moi. Nen luc doi khong hien nut local - doi mai khong xong thi moi tra nut
 * local lai, va luc do no la duong duy nhat, khong phai mot trong hai.
 * KHONG BAO GIO gan href khi artifact chua phai luot nay: gui cho team bao cao
 * cu ma tuong moi la kieu sai im lang.
 *
 * Trang thai doi phai NOI RA. Truoc day luc doi chi hien "Xem report", nguoi
 * dung khong biet co artifact dang tren duong hay khong - va mot the <a> mo di
 * khong co href thi bam vao khong xu ly gi, trong y het tool hong.
 *
 * Publish mat vai giay sau khi bam Cham, nen phai DO LAI vai lan - khong thi
 * nguoi dung phai F5 moi thay nut doi.
 */
'use strict';

/* Boc IIFE de khong ro ten ra pham vi toan cuc - xem event-api.js. */
(() => {

const { api: aApi } = window.USV_API;

const NHIP_MS = 3000;      // moi lan do cach nhau bao lau
const SO_LAN = 20;         // ~60 giay; publish lau hon the thi coi nhu khong co
const CHU_CHO = 'Đang publish artifact…';
const CHU_XONG = 'Link artifact';

function initArtifact({ link, local }) {
  let hen = null;          // setTimeout dang cho, de huy duoc

  function huyHen() {
    if (hen !== null) { clearTimeout(hen); hen = null; }
  }

  /* trangThai: 'xong' | 'cho' | 'het' - xem docstring dau file. */
  function dat(trangThai, url) {
    if (trangThai === 'xong') {
      link.href = url;
      link.textContent = CHU_XONG;
      link.removeAttribute('aria-disabled');
      link.removeAttribute('tabindex');
      link.hidden = false;
      local.hidden = true;
      return;
    }
    if (trangThai === 'cho') {
      // Bo han href: co href la tro vao artifact cua luot TRUOC.
      link.removeAttribute('href');
      link.textContent = CHU_CHO;
      link.setAttribute('aria-disabled', 'true');
      link.setAttribute('tabindex', '-1');
      link.hidden = false;
      local.hidden = true;       // MOT nut thoi - xem docstring dau file
      return;
    }
    link.hidden = true;
    local.hidden = false;
  }

  /* Tra ve true khi artifact da la luot nay -> khong can do nua. */
  async function doMotLan() {
    let data;
    try {
      data = await aApi('/event/artifact');
    } catch (error) {
      return false;          // giu nguyen trang thai dang hien, khong lam sap gi
    }
    const khop = Boolean(data.url) && data.khop === true;
    if (khop) dat('xong', data.url);
    return khop;
  }

  async function show() {
    huyHen();
    dat('cho', '');          // noi ra la dang doi, chu khong im lang
    if (await doMotLan()) return;
    let conLai = SO_LAN;
    const lap = async () => {
      hen = null;
      if (conLai-- <= 0) { dat('het', ''); return; }
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
