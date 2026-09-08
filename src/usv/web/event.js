/* Luong: dan spec -> chon may/app -> Ghi -> danh dau tung buoc -> Dung -> Cham.
 *
 * KHONG cho Ghi khi spec con loi. Spec sai thi bao cao sai, va sai am tham -
 * day la ly do bang preview la buoc bat buoc chu khong phai tien nghi.
 */
'use strict';

const { renderMarks, markProgress, escapeHtml } = window.USV_MARKS;
const { renderPreview, renderSummary, renderResults } = window.USV_RENDER;
const $ = (id) => document.getElementById(id);

const ui = {
  spec: { text: $('spec-text'), btn: $('btn-spec'), info: $('spec-info'),
          errors: $('spec-errors'), preview: $('spec-preview') },
  device: $('device'), pkg: $('package'), pkgFilter: $('pkg-filter'),
  fromLaunch: $('from-launch'), btnDevices: $('btn-devices'),
  btnRecord: $('btn-record'), recordInfo: $('record-info'),
  markFilter: $('mark-filter'), marks: $('marks'), progress: $('mark-progress'),
  btnStop: $('btn-stop'), btnCheck: $('btn-check'), btnReset: $('btn-reset'),
  summary: $('summary'), results: $('results'),
  linkReport: $('link-report'), linkXlsx: $('link-xlsx'),
  steps: { device: $('step-device'), mark: $('step-mark'), check: $('step-check') },
};

let events = [];              // event trong spec
let allPackages = [];
const done = new Set();       // event da bam moc
let current = null;
let stage = 'need_spec';

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

function fail(node, message) {
  node.innerHTML = `<div class="alert">${escapeHtml(message)}</div>`;
}

function setStage(next) {
  stage = next;
  const recording = stage === 'recording';
  ui.steps.device.setAttribute('aria-disabled', stage === 'need_spec');
  ui.steps.mark.setAttribute('aria-disabled', !recording);
  ui.steps.check.setAttribute('aria-disabled',
    !['ready_to_check', 'done'].includes(stage));
  ui.btnRecord.disabled = stage !== 'ready_to_record';
  ui.btnStop.disabled = !recording;
  ui.btnCheck.disabled = stage !== 'ready_to_check';
}

/* --- buoc 1: spec --- */
ui.spec.btn.addEventListener('click', async () => {
  ui.spec.errors.innerHTML = '';
  try {
    const data = await post('/event/spec', { text: ui.spec.text.value });
    events = data.events || [];
    done.clear();
    current = null;
    ui.spec.info.textContent =
      `${data.event_count} event · ${data.param_count} param`;
    if (data.errors?.length) {
      ui.spec.errors.innerHTML = '<div class="alert"><b>Bảng chưa đọc được:</b><ul>'
        + data.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join('') + '</ul></div>';
    }
    renderPreview(ui.spec.preview, events);
    renderMarkPanel();
    setStage(data.stage);
    if (data.stage !== 'need_spec') loadDevices();
  } catch (error) {
    fail(ui.spec.errors, error.message);
  }
});

/* --- buoc 2: may va app --- */
async function loadDevices() {
  try {
    const data = await api('/devices');
    ui.device.innerHTML = data.devices
      .map((d) => `<option value="${escapeHtml(d.serial)}"${d.usable ? '' : ' disabled'}>`
        + `${escapeHtml(d.label)}${d.usable ? '' : ' — ' + escapeHtml(d.state)}</option>`)
      .join('') || '<option value="">không thấy máy nào</option>';
    if (ui.device.value) loadPackages();
  } catch (error) {
    fail(ui.spec.errors, error.message);
  }
}

async function loadPackages() {
  try {
    const data = await api(`/packages?serial=${encodeURIComponent(ui.device.value)}`);
    allPackages = data.packages || [];
    renderPackages();
  } catch (error) {
    fail(ui.spec.errors, error.message);
  }
}

function renderPackages() {
  const needle = ui.pkgFilter.value.toLowerCase();
  const list = allPackages.filter((p) => p.includes(needle));
  ui.pkg.innerHTML = list.map((p) =>
    `<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`).join('')
    || '<option value="">không có app nào khớp</option>';
}

ui.btnDevices.addEventListener('click', loadDevices);
ui.device.addEventListener('change', loadPackages);
ui.pkgFilter.addEventListener('input', renderPackages);

ui.btnRecord.addEventListener('click', async () => {
  ui.btnRecord.disabled = true;
  ui.recordInfo.textContent = 'đang bật log Firebase và mở lại app…';
  try {
    const data = await post('/event/record', {
      serial: ui.device.value, package: ui.pkg.value,
      from_launch: ui.fromLaunch.checked,
    });
    ui.recordInfo.textContent = 'đang ghi — bấm nút của bước sắp làm';
    setStage(data.stage);
  } catch (error) {
    ui.recordInfo.textContent = '';
    fail(ui.spec.errors, error.message);
    setStage(stage);
  }
});

/* --- buoc 3: danh dau --- */
function renderMarkPanel() {
  renderMarks(ui.marks, events, {
    filter: ui.markFilter.value, done, current, onMark: sendMark,
  });
  ui.progress.textContent = markProgress(events, done);
}

async function sendMark(event) {
  try {
    await post('/event/mark', { spec_event: event.name, note: event.triggered });
    done.add(event.name);
    current = event.name;
    renderMarkPanel();
  } catch (error) {
    fail(ui.spec.errors, error.message);
  }
}

ui.markFilter.addEventListener('input', renderMarkPanel);

ui.btnStop.addEventListener('click', async () => {
  ui.btnStop.disabled = true;
  try {
    const data = await post('/event/stop');
    ui.recordInfo.textContent = `đã dừng — ${data.event_count} event, `
      + `${data.window_count} bước đã đánh dấu`;
    setStage(data.stage);
  } catch (error) {
    fail(ui.spec.errors, error.message);
  }
});

/* --- buoc 4: cham --- */
ui.btnCheck.addEventListener('click', async () => {
  ui.btnCheck.disabled = true;
  try {
    const data = await post('/event/check');
    renderSummary(ui.summary, data);
    renderResults(ui.results, data.results || []);
    ui.linkReport.hidden = false;
    ui.linkXlsx.hidden = false;
    setStage(data.stage);
  } catch (error) {
    fail(ui.summary, error.message);
    setStage(stage);
  }
});

ui.btnReset.addEventListener('click', async () => {
  await post('/event/reset').catch(() => {});
  events = []; done.clear(); current = null;
  ui.spec.preview.innerHTML = ''; ui.spec.errors.innerHTML = '';
  ui.spec.info.textContent = ''; ui.recordInfo.textContent = '';
  ui.summary.innerHTML = ''; ui.results.innerHTML = '';
  ui.marks.innerHTML = ''; ui.progress.textContent = '';
  ui.linkReport.hidden = true; ui.linkXlsx.hidden = true;
  setStage('need_spec');
});

setStage('need_spec');
