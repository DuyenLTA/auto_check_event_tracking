"""Token + CSS cho report event. Lay nguyen he thiet ke cua tool ad-checklist-diff.

User chot mau nay, KHONG dung report_css.py cua tab UI - hai report la hai ho
khac nhau.

Khong them mau nao moi. Token `--pending` da co san trong ban goc (chi dung cho
section-frac) nen NOT_VERIFIABLE dung luon; NOT_TESTED/EXTRA dung `--surface-alt`
trung tinh.

Theme viet du 3 tang - thieu tang nao la mot nua nguoi xem doc chu mau nay tren
nen mau kia:
  :root                                   -> sang, dinh nghia DU bo token
  @media (prefers-color-scheme: dark)     -> boc :root:not([data-theme="light"])
  :root[data-theme="dark"]                -> de nut chuyen theme thang ca 2 chieu
Khong mau nao chi ton tai ben trong media query.
"""

from __future__ import annotations

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800'
    "&family=Public+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600"
    '&display=swap" rel="stylesheet">'
)

CSS = """<style>
  :root{
    --ink:#10181a;--ink-soft:#56686a;--paper:#eef2f1;--surface:#fff;
    --surface-alt:#f5f8f7;--line:#d7e1df;
    --accent:#146b6e;--accent-soft:#dcecea;
    --pass:#1f7a4d;--pass-soft:#e2f4e8;
    --fail:#b23b2e;--fail-soft:#fbeae6;
    --pending:#97650f;--pending-soft:#f7ecd7;
  }
  @media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
    --ink:#e8efee;--ink-soft:#9fb3b1;--paper:#0d1516;--surface:#141f20;
    --surface-alt:#182324;--line:#24393a;
    --accent:#55c2bf;--accent-soft:#16302f;
    --pass:#5fce8e;--pass-soft:#16301f;
    --fail:#ef8574;--fail-soft:#341c18;
    --pending:#e0ab54;--pending-soft:#34290f;
  }}
  :root[data-theme="dark"]{
    --ink:#e8efee;--ink-soft:#9fb3b1;--paper:#0d1516;--surface:#141f20;
    --surface-alt:#182324;--line:#24393a;
    --accent:#55c2bf;--accent-soft:#16302f;
    --pass:#5fce8e;--pass-soft:#16301f;
    --fail:#ef8574;--fail-soft:#341c18;
    --pending:#e0ab54;--pending-soft:#34290f;
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--paper);color:var(--ink);
    font-family:'Public Sans',sans-serif;line-height:1.5;
    font-variant-numeric:tabular-nums;}
  .wrap{max-width:980px;margin:0 auto;padding:2.5rem 1.5rem 4rem;
    display:flex;flex-direction:column;gap:1.75rem;}
  .report-head{display:flex;flex-direction:column;gap:1.1rem;}
  .eyebrow{margin:0;font-family:'Manrope',sans-serif;font-weight:800;
    font-size:0.85rem;letter-spacing:0.14em;text-transform:uppercase;
    color:var(--accent);}
  h1{margin:0;font-family:'Manrope',sans-serif;font-weight:800;font-size:2.1rem;
    letter-spacing:0.01em;text-wrap:balance;}
  .meta{margin:0;font-family:'JetBrains Mono',monospace;font-size:0.78rem;
    color:var(--ink-soft);}
  .callout{border:1px solid var(--line);border-left:3px solid var(--pending);
    background:var(--pending-soft);border-radius:0 10px 10px 0;
    padding:1rem 1.25rem;}
  .callout.alarm{border-left-color:var(--fail);background:var(--fail-soft);}
  .callout h3{margin:0 0 0.35rem;font-family:'Manrope',sans-serif;
    font-weight:800;font-size:1.05rem;}
  .callout p{margin:0;font-size:0.88rem;color:var(--ink-soft);max-width:65ch;}
  .chip-list{display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.6rem;}
  .chip{font-family:'JetBrains Mono',monospace;font-size:0.76rem;
    background:var(--surface);border:1px solid var(--line);border-radius:6px;
    padding:0.3rem 0.55rem;color:var(--ink-soft);}
  /* "x5" = nam case cho ra dong giong het nhau, da gop lai lam mot. */
  .times{display:inline-block;margin-left:0.4rem;padding:0.05rem 0.3rem;
    border-radius:0.25rem;background:var(--surface-alt);border:1px solid var(--line);
    font-size:0.72rem;font-weight:600;color:var(--ink-soft);}
  .status{display:inline-flex;align-items:center;gap:0.35rem;
    font-family:'JetBrains Mono',monospace;font-size:0.72rem;font-weight:600;
    padding:0.2rem 0.55rem;border-radius:20px;white-space:nowrap;}
  .status.pass{background:var(--pass-soft);color:var(--pass);}
  .status.fail{background:var(--fail-soft);color:var(--fail);}
  .status.pending{background:var(--pending-soft);color:var(--pending);}
  .status.muted{background:var(--surface-alt);color:var(--ink-soft);
    border:1px solid var(--line);}
  .status .dot{width:6px;height:6px;border-radius:50%;background:currentColor;}
  .note{margin-top:0.4rem;font-family:'JetBrains Mono',monospace;
    font-size:0.76rem;color:var(--ink-soft);max-width:70ch;
    white-space:pre-wrap;overflow-wrap:anywhere;}
  /* Ghi chu triage: PHAI trong khac han phan tool tu do duoc. Doc chung mot
     kieu chu thi nguoi doc tuong tool da xac minh, ma day la suy luan. */
  .triage{margin-top:0.5rem;padding:0.5rem 0.65rem;max-width:42ch;
    border-left:2px solid var(--accent);background:var(--accent-soft);
    border-radius:0 6px 6px 0;}
  .triage-head{display:flex;flex-wrap:wrap;align-items:center;gap:0.4rem;}
  .triage-tag{font-family:'JetBrains Mono',monospace;font-size:0.7rem;
    font-weight:600;color:var(--accent);}
  .triage-vote{font-family:'JetBrains Mono',monospace;font-size:0.66rem;
    color:var(--ink-soft);}
  .triage p{margin:0.3rem 0 0;font-size:0.78rem;color:var(--ink);}
  .triage .ev{font-family:'JetBrains Mono',monospace;font-size:0.72rem;
    color:var(--ink-soft);}
</style>"""
