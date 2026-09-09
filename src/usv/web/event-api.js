/* Goi API + hien loi. Tach ra vi ca ba file JS deu dung. */
'use strict';

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
  node.innerHTML = `<div class="alert">${window.USV_MARKS.escapeHtml(message)}</div>`;
}

window.USV_API = { api, post, fail };
