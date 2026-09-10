/* Buoc 1: nap bang spec, tu link Confluence hoac dan tay.
 *
 * Hai nguon di CHUNG mot duong ve ket qua (`onLoaded`). Hai ban rieng la mot
 * ngay mot ben quen cap nhat preview, va bang xem truoc lech voi spec that
 * thi khong ai phat hien ra.
 */
'use strict';

/* Boc IIFE de khong ro ten ra pham vi toan cuc - xem event-marks.js. */
(() => {

const { post: sPost, fail: sFail } = window.USV_API;

function initSpec({ text, btn, info, url, urlBtn, urlInfo, errors, onLoaded }) {
  async function load(path, body, target) {
    errors.innerHTML = '';
    try {
      const data = await sPost(path, body);
      onLoaded(data, target);
      return data;
    } catch (error) {
      target.textContent = '';
      sFail(errors, error.message);
      return null;
    }
  }

  urlBtn.addEventListener('click', async () => {
    urlInfo.textContent = 'đang đọc trang…';
    const data = await load('/event/spec/confluence', { url: url.value }, urlInfo);
    // Ten trang doc duoc = bang chung da vao dung trang, khong phai trang khac
    // cung ten file. In ra de nguoi dung doi chieu bang mat.
    if (data?.source) urlInfo.textContent += ` · ${data.source}`;
  });

  btn.addEventListener('click', () => load('/event/spec', { text: text.value }, info));
}

window.USV_SPEC = { initSpec };
})();
