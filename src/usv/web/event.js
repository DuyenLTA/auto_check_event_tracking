/* Luong: dan spec -> chon may/app -> Ghi -> danh dau tung buoc -> Dung -> Cham.
 *
 * KHONG cho Ghi khi spec con loi. Spec sai thi bao cao sai, va sai am tham -
 * day la ly do bang preview la buoc bat buoc chu khong phai tien nghi.
 */
'use strict';

/* Boc IIFE de khong ro ten ra pham vi toan cuc - xem event-marks.js. */
(() => {

const { renderMarks, markProgress, escapeHtml } = window.USV_MARKS;
const { renderPreview, renderSummary, renderResults } = window.USV_RENDER;
const { api, post, fail } = window.USV_API;
const { initDevice } = window.USV_DEVICE;
const { initSpec } = window.USV_SPEC;
const { initArtifact } = window.USV_ARTIFACT;
const watch = window.USV_PROGRESS;
const $ = (id) => document.getElementById(id);

const ui = {
  spec: { text: $('spec-text'), btn: $('btn-spec'), info: $('spec-info'),
          errors: $('spec-errors'), preview: $('spec-preview') },
  specUrl: { input: $('spec-url'), btn: $('btn-spec-url'),
             info: $('spec-url-info') },
  device: $('device'), pkg: $('package'), pkgInfo: $('package-info'),
  btnDevices: $('btn-devices'),
  deviceInfo: $('device-info'), devicePick: $('device-pick'),
  btnRecord: $('btn-record'), recordInfo: $('record-info'),
  recordAlert: $('record-alert'),
  markFilter: $('mark-filter'), marks: $('marks'), progress: $('mark-progress'),
  btnStop: $('btn-stop'), btnCheck: $('btn-check'), btnReset: $('btn-reset'),
  summary: $('summary'), results: $('results'),
  linkReport: $('link-report'), linkArtifact: $('link-artifact'),
  steps: { mark: $('step-mark'), check: $('step-check') },
};

let events = [];              // event trong spec
const done = new Set();       // event da bam moc
let current = null;
let stage = 'need_spec';

function setStage(next) {
  stage = next;
  const recording = stage === 'recording';
  ui.steps.mark.setAttribute('aria-disabled', !recording);
  ui.steps.check.setAttribute('aria-disabled',
    !['ready_to_check', 'done'].includes(stage));
  ui.btnRecord.disabled = stage !== 'ready_to_record';
  ui.btnStop.disabled = !recording;
  ui.btnCheck.disabled = stage !== 'ready_to_check';
}

/* --- buoc 1: spec --- */
/* Nap xong (tu link hay dan tay deu vao day) -> dua vao trang thai app. */
function applySpec(data, info) {
  events = data.events || [];
  done.clear();
  current = null;
  info.textContent = `${data.event_count} event · ${data.param_count} param`;
  if (data.errors?.length) {
    ui.spec.errors.innerHTML = '<div class="alert"><b>Bảng chưa đọc được:</b><ul>'
      + data.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join('') + '</ul></div>';
  }
  renderPreview(ui.spec.preview, events);
  renderMarkPanel();
  setStage(data.stage);
}

initSpec({
  text: ui.spec.text, btn: ui.spec.btn, info: ui.spec.info,
  url: ui.specUrl.input, urlBtn: ui.specUrl.btn, urlInfo: ui.specUrl.info,
  errors: ui.spec.errors, onLoaded: applySpec,
});

ui.btnRecord.addEventListener('click', async () => {
  ui.btnRecord.disabled = true;
  ui.recordInfo.textContent = 'đang bật log Firebase và mở lại app…';
  try {
    const data = await post('/event/record', {
      serial: ui.device.value, package: ui.pkg.value,
    });
    // Tool khong tu mo duoc -> phai nhac mo NGAY BAY GIO: log Firebase chi bat
    // duoc tu lan app khoi dong sau khi tool set property, mo truoc thi ca
    // phien khong co dong FA nao.
    const label = data.launched
      ? 'đang ghi, thao tác trên máy rồi bấm Dừng ghi'
      : 'đang ghi — MỞ APP trên máy bây giờ, rồi thao tác';
    ui.recordInfo.textContent = label;
    ui.recordAlert.innerHTML = data.launched ? ''
      : `<div class="alert warn"><b>Tự mở app trên máy bây giờ.</b> `
        + `${escapeHtml(data.hint || '')}</div>`;
    setStage(data.stage);
    // Theo doi lien tuc: mat may giua phien phai biet NGAY, khong phai luc Cham.
    deviceUi.stopWatch();     // dang ghi thi dung dong vao danh sach may/app
    watch.start({ info: ui.recordInfo, alert: ui.recordAlert }, label,
                () => { ui.btnRecord.disabled = false; });
  } catch (error) {
    ui.recordInfo.textContent = '';
    // Loi cua buoc GHI phai hien o buoc ghi. Truoc day day vao o loi cua buoc
    // 1 (bang spec) - nguoi dung dang o buoc 2, bam Ghi khong thay gi, con
    // loi thi nam tren cao co khi ngoai man hinh.
    fail(ui.recordAlert, error.message);
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
  watch.stop();
  deviceUi.startWatch();
  try {
    const data = await post('/event/stop');
    ui.recordInfo.textContent = data.quick
      ? `đã dừng — đọc được ${data.event_count} event trong cả phiên`
      : `đã dừng — ${data.event_count} event, ${data.window_count} bước đã đánh dấu`;
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
    // artifactUi so huu CA HAI nut xem bao cao - hien dung mot cai, xem
    // event-artifact.js.
    artifactUi.show();
    setStage(data.stage);
  } catch (error) {
    fail(ui.summary, error.message);
    setStage(stage);
  }
});

ui.btnReset.addEventListener('click', async () => {
  watch.stop();                 // khong tat thi no con poll va ghi de len o info
  await post('/event/reset').catch(() => {});
  events = []; done.clear(); current = null;
  ui.spec.preview.innerHTML = ''; ui.spec.errors.innerHTML = '';
  ui.spec.info.textContent = ''; ui.recordInfo.textContent = '';
  ui.specUrl.info.textContent = '';
  ui.recordAlert.innerHTML = '';
  ui.summary.innerHTML = ''; ui.results.innerHTML = '';
  ui.marks.innerHTML = ''; ui.progress.textContent = '';
  artifactUi.clear();
  setStage('need_spec');
  deviceUi.loadDevices();       // may co the da doi giua chung
  deviceUi.startWatch();
});

const artifactUi = initArtifact({
  link: ui.linkArtifact, local: ui.linkReport,
});

const deviceUi = initDevice({
  device: ui.device, pkg: ui.pkg, pkgInfo: ui.pkgInfo,
  refresh: ui.btnDevices, errorNode: ui.spec.errors,
  info: ui.deviceInfo, pick: ui.devicePick,
});

setStage('need_spec');
// Tim may NGAY khi mo trang, khong doi nap spec: may cam san thi khong co ly
// do bat nguoi dung bam them mot nut. Roi do tiep lien tuc - cam may luc nao
// cung phai thay luc do.
deviceUi.loadDevices();
deviceUi.startWatch();
})();
