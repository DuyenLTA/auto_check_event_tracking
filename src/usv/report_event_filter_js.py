"""JS loc danh sach event: the dem / chip trang thai / o tim / mo-gap tat ca.

Noi dung da sinh san bang HTML, JS chi an/hien - tat JS thi trang van doc du,
chi mat bo loc.
"""

JS = """<script>
(() => {
  let f = "all", q = "";
  const evs = [...document.querySelectorAll("details.ev")];
  const btns = [...document.querySelectorAll("[data-f]")];
  function apply() {
    let shown = 0;
    evs.forEach(d => {
      const ok = (f === "all" || d.dataset.st === f) && (!q || d.dataset.q.includes(q));
      d.hidden = !ok; if (ok) shown++;
    });
    document.querySelectorAll("section.bucket").forEach(s =>
      s.hidden = !s.querySelector("details.ev:not([hidden])"));
    btns.forEach(b => b.setAttribute("aria-pressed", b.dataset.f === f));
    const c = document.getElementById("evCount");
    if (c) c.textContent = shown + " / " + evs.length + " event";
    const e = document.getElementById("evEmpty");
    if (e) e.hidden = shown > 0;
  }
  btns.forEach(b => b.onclick = () => {
    f = (f === b.dataset.f && b.dataset.f !== "all") ? "all" : b.dataset.f; apply();
  });
  const box = document.getElementById("evQ");
  if (box) box.oninput = e => { q = e.target.value.trim().toLowerCase(); apply(); };
  const all = document.getElementById("evAll");
  if (all) all.onclick = () => {
    const vis = evs.filter(d => !d.hidden), open = !vis.every(d => d.open);
    vis.forEach(d => d.open = open);
    all.textContent = open ? "Thu gọn tất cả" : "Mở tất cả";
  };
  // Bam ten event o khoi "can xu ly": bo loc dang an no thi tra ve "Tat ca".
  document.querySelectorAll("a.jump").forEach(a => a.addEventListener("click", () => {
    const d = document.getElementById(a.getAttribute("href").slice(1));
    if (d && d.hidden) { f = "all"; q = ""; if (box) box.value = ""; apply(); }
    if (d) d.open = true;
  }));
  apply();
})();
</script>"""
