/* Goi API, hien loi, va thoat chuoi HTML. Tach ra vi file JS nao cung dung. */
'use strict';

/* Boc trong IIFE: script thuong (khong phai module) dung CHUNG mot pham vi
 * toan cuc, nen ham khai o day se dung ten voi file khac. Da gap that -
 * event.js destructure mot ten ma file khac da khai bang `function` cung ten,
 * thanh SyntaxError va ca event.js khong chay duoc mot dong nao. Trinh duyet
 * bao o console, con curl van tra 200 - nen loi nay song rat lau.
 * Chi dua ra ngoai qua window.USV_*. */
(() => {

/* Moi chuoi tu spec/API deu di qua day truoc khi vao innerHTML. Ten event va
 * van xuoi cot Triggered do NGUOI khac go, khong duoc tin. */
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `${response.status} ${path}`);
  return body;
}

const post = (path, data) => api(path, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data ?? {}),
});

/* Loi hien ngay tai cho, khong dung alert - alert chan ca trang. */
function fail(node, message) {
  node.innerHTML = `<div class="alert">${escapeHtml(message)}</div>`;
}

window.USV_API = { api, post, fail, escapeHtml };
})();
