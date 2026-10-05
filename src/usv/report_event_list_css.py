"""CSS cho bo cuc the dem + khoi can xu ly + danh sach event gap/mo.

Chi dung token da khai o report_event_css (khong them mau moi). Khong co bang
ngang nao: moi param la mot khoi doc tu tren xuong, man hep van doc duoc ma
khong phai keo ngang.
"""

LIST_CSS = """<style>
  .counts{font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:var(--ink-soft);margin:0;}
  .tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:0.6rem;}
  .tile{display:flex;flex-direction:column;gap:0.1rem;text-align:left;cursor:pointer;
    font:inherit;color:inherit;background:var(--surface);border:1px solid var(--line);
    border-radius:10px;padding:0.75rem 0.9rem;}
  .tile[aria-pressed="true"]{outline:2px solid var(--accent);outline-offset:-2px;}
  .tile .num{font-family:'Manrope',sans-serif;font-weight:800;font-size:1.9rem;line-height:1.1;}
  .tile .lab{font-size:0.8rem;color:var(--ink-soft);}
  .tile.fail .num{color:var(--fail);} .tile.pass .num{color:var(--pass);}
  .tile.pending .num{color:var(--pending);} .tile.muted .num{color:var(--ink-soft);}
  .todo-card{background:var(--surface);border:1px solid var(--line);border-radius:12px;
    padding:1rem 1.25rem;display:grid;gap:1rem;
    grid-template-columns:repeat(auto-fit,minmax(260px,1fr));}
  .todo-card h3{margin:0 0 0.4rem;font-family:'Manrope',sans-serif;font-size:0.95rem;}
  .todo-card h3.fail{color:var(--fail);} .todo-card h3.pending{color:var(--pending);}
  .todo-card h3.muted{color:var(--ink-soft);}
  .todo-card.all-ok h3{color:var(--pass);}
  .todo-card p{margin:0;font-size:0.88rem;color:var(--ink-soft);}
  .todo-card ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:0.45rem;}
  .todo-card li{display:flex;flex-direction:column;font-size:0.82rem;color:var(--ink-soft);
    overflow-wrap:anywhere;}
  .jump code{font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:var(--accent);}
  .bar{position:sticky;top:0;z-index:5;background:var(--paper);padding:0.6rem 0;
    display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;border-bottom:1px solid var(--line);}
  .fchip{font:600 0.78rem 'Public Sans',sans-serif;border:1px solid var(--line);
    background:var(--surface);color:var(--ink);border-radius:99px;padding:0.3rem 0.8rem;cursor:pointer;}
  .fchip[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink);}
  .search{flex:1;min-width:160px;font:inherit;border:1px solid var(--line);background:var(--surface);
    color:var(--ink);border-radius:8px;padding:0.35rem 0.6rem;}
  .linkbtn{font:600 0.8rem 'Public Sans',sans-serif;background:none;border:0;color:var(--accent);cursor:pointer;}
  .bar .cnt{font-size:0.78rem;color:var(--ink-soft);margin-left:auto;}
  .sections{display:flex;flex-direction:column;gap:1.25rem;}
  .bucket{display:flex;flex-direction:column;background:var(--surface);
    border:1px solid var(--line);border-radius:12px;overflow:hidden;}
  .bucket-h{margin:0;padding:0.75rem 1.1rem;font-family:'Manrope',sans-serif;font-size:1.05rem;}
  .bucket-h span{font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:var(--ink-soft);}
  .bucket-h.fail{color:var(--fail);} .bucket-h.pass{color:var(--pass);}
  .bucket-h.pending{color:var(--pending);}
  details.ev{border-top:1px solid var(--line);scroll-margin-top:4rem;}
  details.ev[data-st="fail"]{box-shadow:inset 3px 0 0 var(--fail);}
  details.ev>summary{list-style:none;cursor:pointer;display:grid;
    grid-template-columns:7.5rem 1fr auto;gap:0.75rem;align-items:start;padding:0.6rem 1.1rem;}
  details.ev>summary::-webkit-details-marker{display:none;}
  details.ev>summary:hover{background:var(--surface-alt);}
  @media (max-width:560px){details.ev>summary{grid-template-columns:1fr auto;}
    details.ev>summary .status{grid-column:1/-1;justify-self:start;}}
  .ev-t{display:flex;flex-direction:column;min-width:0;}
  .ev-name{display:flex;flex-wrap:wrap;gap:0.4rem;align-items:baseline;}
  .ev-name code{font-family:'JetBrains Mono',monospace;font-size:0.85rem;overflow-wrap:anywhere;}
  .scr{font-size:0.7rem;color:var(--ink-soft);border:1px solid var(--line);border-radius:5px;padding:0 0.35rem;}
  .ev-sub{font-size:0.78rem;color:var(--ink-soft);overflow:hidden;text-overflow:ellipsis;
    white-space:nowrap;}
  details.ev[open] .ev-sub{white-space:normal;}
  .ev-frac{font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--ink-soft);
    white-space:nowrap;padding-top:0.15rem;}
  .ev-body{padding:0 1.1rem 0.9rem;}
  .ev-body .trig{margin:0 0 0.6rem;font-size:0.8rem;color:var(--ink-soft);max-width:80ch;}
  .lines{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:0.5rem;}
  .lines li{border:1px solid var(--line);border-radius:8px;padding:0.5rem 0.7rem;min-width:0;}
  .lines li.row-fail{border-color:var(--fail);background:var(--fail-soft);}
  .line-head{display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;}
  .pname{font-family:'JetBrains Mono',monospace;font-size:0.82rem;font-weight:600;}
  .kv{margin:0.35rem 0 0;display:grid;grid-template-columns:5.5rem 1fr;gap:0.15rem 0.6rem;
    font-size:0.8rem;overflow-x:auto;}
  .kv dt{color:var(--ink-soft);} .kv dd{margin:0;font-family:'JetBrains Mono',monospace;
    overflow-wrap:anywhere;}
  .ctx{font-size:0.72rem;color:var(--ink-soft);}
  .empty{padding:1rem;color:var(--ink-soft);}
</style>"""
