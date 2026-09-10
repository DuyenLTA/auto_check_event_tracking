/* Luong: nap spec -> chon may/app -> Ghi -> thao tac tren may -> Dung -> Cham.
 *
 * KHONG cho Ghi khi spec con loi. Spec sai thi bao cao sai, va sai am tham -
 * day la ly do bang preview la buoc bat buoc chu khong phai tien nghi.
 *
 * KHONG con panel danh dau tung buoc. No cat log thanh cua so theo moc TESTER
 * bam, ma event thi APP ban - hai cai khong dong bo duoc. Da gap that: app bat
 * man daily checkin ngay luc mo, event ban truoc moc dau tien 5 giay, va cung
 * mot app cho ra "1 pass 1 fail" khi co bam moc va "2 pass" khi khong bam.
 * Mot verdict doi theo thu tu bam nut thi khong dung duoc.
 */
'use strict';

/* Boc IIFE de khong ro ten ra pham vi toan cuc - xem event-api.js. */
(() => {

const { renderPreview, renderSummary, renderResults } = window.USV_RENDER;
const { post, fail, escapeHtml } = window.USV_API;
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
  btnStop: $('btn-stop'), btnCheck: $('btn-check'), btnReset: $('btn-reset'),
  summary: $('summary'), results: $('results'),
  linkReport: $('link-report'), linkArtifact: $('link-artifact'),
  steps: { check: $('step-check') },
};

let events = [];              // event trong spec
let stage = 'need_spec';

function setStage(next) {
  stage = next;
  const recording = stage === 'recording';
  // Ghi va Dung ghi nam chung mot buoc nen KHONG mo/khoa ca section theo
  // trang thai: khoa se khoa luon o dan package va nut tim may. Chi hai nut
  // tu bat/tat nhau.
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
  info.textContent = `${data.event_count} event · ${data.param_count} param`;
  if (data.errors?.length) {
    ui.spec.errors.innerHTML = '<div class="alert"><b>Bảng chưa đọc được:</b><ul>'
      + data.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join('') + '</ul></div>';
  }
  renderPreview(ui.spec.preview, events);
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

/* --- buoc 3: dung ghi --- */
ui.btnStop.addEventListener('click', async () => {
  ui.btnStop.disabled = true;
  watch.stop();
  deviceUi.startWatch();
  try {
    const data = await post('/event/stop');
    ui.recordInfo.textContent =
      `đã dừng — đọc được ${data.event_count} event trong cả phiên`;
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
  events = [];
  ui.spec.preview.innerHTML = ''; ui.spec.errors.innerHTML = '';
  ui.spec.info.textContent = ''; ui.recordInfo.textContent = '';
  ui.specUrl.info.textContent = '';
  ui.recordAlert.innerHTML = '';
  ui.summary.innerHTML = ''; ui.results.innerHTML = '';
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
