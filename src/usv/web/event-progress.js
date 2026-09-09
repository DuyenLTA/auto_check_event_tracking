/* Theo doi phien ghi DANG chay: dem dong log va bao NGAY khi stream dut.
 *
 * Vi sao can: truoc day tab web khong poll gi ca, nen giua luc ghi tester
 * khong co mot tin hieu nao. Da gap that - may rot khoi USB, tester bam tiep
 * 69 phut roi moi biet luc bam Cham. Co canh bao trong bao cao van la biet
 * QUA MUON: mat 70 phut so voi mat 3 giay.
 */
'use strict';

window.USV_PROGRESS = (() => {
  const POLL_MS = 2000;
  let timer = null;
  let label = '';

  function stop() {
    if (timer !== null) { clearInterval(timer); timer = null; }
  }

  async function tick(ui, onDied) {
    let rec;
    try {
      rec = (await window.USV_API.api('/event/state')).recording;
    } catch (error) {
      return;                 // mang chop chop - de lan poll sau thu lai
    }
    if (!rec || rec.stopped) { stop(); return; }

    if (rec.stream_died) {
      stop();
      window.USV_API.fail(ui.alert,
        'Phiên ghi đã ĐỨT: stream logcat dừng giữa đường, thường là máy rớt '
        + 'khỏi USB. Từ đây log không được ghi nữa. Cắm lại máy rồi bấm Bắt '
        + `đầu ghi lại — phần đã ghi được ${rec.line_count} dòng.`);
      ui.info.textContent = 'đã đứt — không còn ghi';
      onDied();
      return;
    }

    // Khong doc duoc dong FA nao cung la mat trang phien ghi, chi khac nguyen
    // nhan. Bao som de tester doi build thay vi bam het kich ban.
    ui.info.textContent = rec.fa_silent
      ? `${label} — ${rec.line_count} dòng, CHƯA thấy dòng FA nào`
      : `${label} — đã ghi ${rec.line_count} dòng log`;
  }

  function start(ui, text, onDied) {
    stop();
    label = text;
    timer = setInterval(() => tick(ui, onDied), POLL_MS);
  }

  return { start, stop };
})();
