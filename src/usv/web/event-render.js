/* Ve cac bang: preview spec, tom tat, ket qua.
 *
 * Tach khoi event.js de moi file duoi 200 dong, va vi day la phan CHI VE -
 * khong goi API, khong doi trang thai. De rieng thi doc code de thay cai gi
 * sinh ra request cai gi khong.
 */
'use strict';

const { escapeHtml: esc } = window.USV_MARKS;

/* Mot event nhieu param -> nhieu hang, chi hang dau in ten event. */
function renderPreview(node, list) {
  if (!list.length) { node.innerHTML = ''; return; }
  const rows = list.flatMap((event) => {
    const params = event.params.length ? event.params : [null];
    return params.map((param, index) => `<tr>
      <td>${index === 0 ? esc(event.screen || '—') : ''}</td>
      <td class="mono">${index === 0 ? esc(event.name) : ''}</td>
      <td>${index === 0 ? esc(event.triggered) : ''}</td>
      <td class="mono">${param ? esc(param.name) : '—'}</td>
      <td class="mono">${param ? esc(param.value_type) : ''}</td>
      <td class="mono">${param
        ? (param.free_form ? '(không giới hạn)' : esc(param.allowed.join(', ')))
        : ''}</td></tr>`);
  });
  node.innerHTML = `<div class="scroll"><table><thead><tr>
    <th>Màn</th><th>Event</th><th>Khi nào</th><th>Param</th><th>Kiểu</th>
    <th>Giá trị cho phép</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}

/* Chip dem + hai canh bao khong duoc de nguoi doc hieu sai thanh loi app. */
function renderSummary(node, data) {
  const s = data.summary || {};
  const chips = [
    ['pass', `${s.pass ?? 0} khớp`],
    s.fail ? ['fail', `${s.fail} sai`] : null,
    s.not_verifiable ? ['pending', `${s.not_verifiable} chưa kết luận`] : null,
    s.not_tested ? ['muted', `${s.not_tested} chưa test`] : null,
    s.extra ? ['muted', `${s.extra} spec không khai`] : null,
  ].filter(Boolean);

  let html = `<div class="row">${chips
    .map(([cls, text]) => `<span class="tag ${cls}">${esc(text)}</span>`)
    .join('')}</div>`;

  if (data.quick) {
    html += '<div class="alert warn"><b>Chế độ nhanh:</b> chỉ kết luận event có '
      + 'bắn và param đúng hay không — <b>không</b> kết luận bắn đúng lúc. '
      + 'Kiểm bắn trùng đã tắt.</div>';
  }
  if (data.fa_silent) {
    html += '<div class="alert"><b>Không đọc được log Firebase.</b> Cả phiên ghi '
      + 'không có dòng <code>FA-SVC</code> nào — rất có thể bản này không in log '
      + 'Firebase, <b>không phải</b> app thiếu event. Đừng kết luận app sai.</div>';
  }
  if (data.near_edge?.length) {
    html += '<div class="alert warn"><b>Event bắn sát mốc:</b> '
      + esc(data.near_edge.join(', '))
      + ' — có thể thuộc bước liền kề, tool không tự đổi bước cho chúng.</div>';
  }
  node.innerHTML = html;
}

/* Verdict nao KHONG phai fail thi phai co mat o day - mac dinh la 'fail'. */
const TAG_OF = {
  PASS: 'pass', NOT_VERIFIABLE: 'pending', NOT_TESTED: 'muted', EXTRA: 'muted',
};

function renderResults(node, list) {
  if (!list.length) { node.innerHTML = ''; return; }
  const rows = list.map((r) => `<tr>
    <td><span class="tag ${TAG_OF[r.verdict] || 'fail'}">${esc(r.verdict)}</span></td>
    <td class="mono">${esc(r.element)}</td>
    <td class="mono">${esc(r.expected)}</td>
    <td class="mono">${esc(r.actual)}</td>
    <td>${esc(r.message)}</td></tr>`);
  node.innerHTML = `<div class="scroll"><table><thead><tr>
    <th>Trạng thái</th><th>Event / Param</th><th>Spec cần</th><th>App gửi</th>
    <th>Giải thích</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}

window.USV_RENDER = { renderPreview, renderSummary, renderResults };
