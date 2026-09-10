/* Ve cac bang: preview spec, tom tat, ket qua.
 *
 * Tach khoi event.js de moi file duoi 200 dong, va vi day la phan CHI VE -
 * khong goi API, khong doi trang thai. De rieng thi doc code de thay cai gi
 * sinh ra request cai gi khong.
 */
'use strict';

/* Boc IIFE de khong ro ten ra pham vi toan cuc - xem event-api.js. */
(() => {

const { escapeHtml: esc } = window.USV_API;

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

  // Noi ro con so nao la EVENT, con so nao la dong kiem. Spec 2 event ra 5
  // dong (2 dong event + 3 dong param) thi de tuong la 5 event.
  if (data.spec_event_count) {
    html += `<p class="hint">${data.spec_event_count} event trong spec · `
      + `${s.total_checked ?? 0} mục đã kiểm (mỗi param là một mục riêng).</p>`;
  }

  if (data.quick) {
    html += '<div class="alert warn"><b>Chế độ nhanh:</b> chỉ kết luận event có '
      + 'bắn và param đúng hay không — <b>không</b> kết luận bắn đúng lúc. '
      + 'Kiểm bắn trùng đã tắt.</div>';
  }
  if (data.checked_package && data.checked_package !== data.package) {
    html += '<div class="alert warn"><b>Đã chấm cho app đang mở:</b> <code>'
      + esc(data.checked_package) + '</code>. Tên bạn dán (<code>'
      + esc(data.package || '') + '</code>) không có trên máy. Nếu không phải '
      + 'app cần test thì dán lại tên đúng rồi ghi lại.</div>';
  }
  if (data.app_seen === false) {
    html += '<div class="alert"><b>App dưới test không chạy lần nào.</b> Log '
      + 'Firebase do Google Play Services in ra nên không cho biết event thuộc '
      + 'app nào — event bắt được là của <b>app khác</b>. Kiểm lại tên package, '
      + 'và nếu tự mở app bằng tay thì mở <b>sau</b> khi bấm Ghi.'
      + (data.foreground
        ? ` Lúc dừng ghi máy đang mở <code>${esc(data.foreground)}</code> — rất `
          + 'có thể đây mới là tên package cần dán.' : '')
      + '</div>';
  }
  if (data.stream_died) {
    html += '<div class="alert"><b>Phiên ghi bị đứt giữa đường.</b> Stream '
      + 'logcat dừng trước khi bấm Dừng ghi — thường là máy rớt khỏi USB. '
      + 'Phần sau không được ghi, nên các mục "không bắn" chỉ là <b>không kiểm '
      + 'được</b>, không phải lỗi app. Cắm lại máy và ghi lại.</div>';
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
})();
