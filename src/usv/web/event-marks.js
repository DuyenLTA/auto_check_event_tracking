/* Panel danh dau tung buoc.
 *
 * Nhom theo Screen Name + o loc + dau da-bam. Cach nay chay tot cho ca spec 5
 * event lan 60 event, nen khong phai biet truoc spec to bao nhieu: 5 event thi
 * chi co mot nhom va o loc khong dung den.
 *
 * Nut mang van xuoi cot `Triggered` de tester biet phai lam dong tac gi. Cot do
 * KHONG cham verdict, no chi la nhan.
 */
'use strict';

/* Boc trong IIFE: script thuong (khong phai module) dung CHUNG mot pham vi
 * toan cuc, nen ham khai o day se dung ten voi file khac. Da gap that -
 * event.js khai `const { renderMarks }` trong khi event-marks.js da co
 * `function renderMarks`, va ca event.js khong chay duoc mot dong nao.
 * Chi dua ra ngoai qua window.USV_*. */
(() => {

const KHONG_KHAI_MAN = 'Không khai màn';

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* Gom event theo screen, giu nguyen thu tu xuat hien trong spec. */
function groupByScreen(events) {
  const groups = new Map();
  for (const event of events) {
    const key = event.screen || KHONG_KHAI_MAN;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(event);
  }
  return groups;
}

function matches(event, needle) {
  if (!needle) return true;
  const hay = `${event.name} ${event.screen} ${event.triggered}`.toLowerCase();
  return hay.includes(needle.toLowerCase());
}

/* `done` = Set ten event da bam. `current` = ten event bam gan nhat. */
function renderMarks(container, events, { filter = '', done, current, onMark }) {
  const marked = done || new Set();
  container.innerHTML = '';
  const shown = events.filter((e) => matches(e, filter));

  if (!shown.length) {
    container.innerHTML = '<p class="hint">Không có event nào khớp ô lọc.</p>';
    return;
  }

  for (const [screen, list] of groupByScreen(shown)) {
    const wrap = document.createElement('div');
    wrap.className = 'group';
    const doneCount = list.filter((e) => marked.has(e.name)).length;
    wrap.innerHTML = `<h3>${escapeHtml(screen)} — ${doneCount}/${list.length}</h3>`;

    const row = document.createElement('div');
    row.className = 'marks';
    for (const event of list) {
      const button = document.createElement('button');
      button.className = 'mark';
      if (marked.has(event.name)) button.classList.add('done');
      if (event.name === current) button.classList.add('current');
      button.innerHTML = `<b>${escapeHtml(event.name)}</b>`
        + `<span>${escapeHtml(event.triggered || 'chưa khai cột Triggered')}</span>`;
      button.addEventListener('click', () => onMark(event));
      row.appendChild(button);
    }
    wrap.appendChild(row);
    container.appendChild(wrap);
  }
}

/* Danh dau la TUY CHON, nen chua bam mot moc nao thi IM LANG.
 *
 * Truoc day in "0/2 buoc — con 2" ngay tu dau: doc vao tuong con viec phai
 * lam, va bam het kich ban roi van thay 0/2 thi tuong tool khong ghi nhan gi.
 * That ra 0/2 la dung - chi co nghia "chua danh dau buoc nao", ma khong danh
 * dau van cham duoc event co ban va param.
 */
function markProgress(events, done) {
  const marked = done || new Set();
  const total = events.length;
  const hit = events.filter((e) => marked.has(e.name)).length;
  if (!total || !hit) return '';
  const left = total - hit;
  return left
    ? `đã đánh dấu ${hit}/${total} event — còn ${left}`
    : `đã đánh dấu cả ${total} event, bấm Dừng ghi`;
}

window.USV_MARKS = { renderMarks, markProgress, escapeHtml };
})();
