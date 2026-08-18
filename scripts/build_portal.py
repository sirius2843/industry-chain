#!/usr/bin/env python3
"""Build the portal index.html integrating all chain maps + dashboards.

Reads each chain dashboard's embedded DATA (already refreshed by
refresh_dashboard.py) and generates:
  - 总览 home tab: one card per chain with that day's breadth/leaders
  - one tab per chain: sub-tabs embedding 图谱 / 行情看板 via iframe
Run after all dashboards are refreshed. Idempotent.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "index.html"

CHAINS = [
    {"key": "ai", "name": "人工智能", "map": "AI产业链图谱.html",
     "dash": "ai-chain-dashboard.html"},
    {"key": "pharma", "name": "医药", "map": "医药产业链图谱.html",
     "dash": "pharma-chain-dashboard.html"},
    {"key": "robot", "name": "机器人", "map": "机器人产业链图谱.html",
     "dash": "robot-chain-dashboard.html"},
    {"key": "metal", "name": "有色金属", "map": "有色金属产业链图谱.html",
     "dash": "metal-chain-dashboard.html"},
]


def load_dash(path: Path) -> dict:
    html = path.read_text(encoding="utf-8")
    m = re.search(r"var DATA = (\{.*?\});\n", html, re.S)
    return json.loads(m.group(1))


def chain_overview(data: dict) -> dict:
    segs = data["master"]["segments"]
    stats = data.get("segstats", {})
    snap = data.get("snap", {})
    leaders = data.get("leaders", {})
    n_tot, w_med, w_rise = 0, 0.0, 0.0
    seg_rows = []
    for s in segs:
        st = stats.get(s["id"])
        if not st:
            continue
        n = st["n"]
        n_tot += n
        w_med += st["med"] * n
        w_rise += st.get("rise", 0.0) * n
        seg_rows.append({"short": s["short"], "med": st["med"], "n": n})
    seg_rows.sort(key=lambda r: -r["med"])
    lds = []
    for s in segs:
        ld = leaders.get(s["id"])
        if not ld:
            continue
        sp = snap.get(ld["code"], {})
        lds.append({"seg": s["short"], "name": ld["name"],
                    "daily": sp.get("daily")})
    return {
        "updated": data.get("updated", "?"),
        "total": data["master"]["total"],
        "med": (w_med / n_tot) if n_tot else 0.0,
        "rise": (w_rise / n_tot) if n_tot else 0.0,
        "top": seg_rows[:2],
        "bottom": seg_rows[-2:][::-1] if len(seg_rows) >= 2 else [],
        "leaders": lds,
    }


def pct(x, digits=2):
    if x is None:
        return "—"
    v = x * 100
    cls = "up" if v > 0 else ("dn" if v < 0 else "flat")
    sign = "+" if v > 0 else ""
    return f'<span class="{cls}">{sign}{v:.{digits}f}%</span>'


CSS = """
:root{--bg:#0d1117;--panel:#161b22;--line:#2b333d;--fg:#e6e9ee;--mut:#8b949e;
--up:#f0334b;--dn:#1fbf75;--acc:#d29922}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
header{padding:18px 24px 0;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
h1{font-size:20px}
header .mut{color:var(--mut);font-size:12px}
nav.tabs{display:flex;gap:6px;padding:14px 24px;border-bottom:1px solid var(--line);flex-wrap:wrap}
nav.tabs button{background:none;border:1px solid var(--line);color:var(--mut);
border-radius:8px;padding:7px 18px;font-size:14px;cursor:pointer}
nav.tabs button.on{background:var(--acc);border-color:var(--acc);color:#111;font-weight:600}
.page{display:none}.page.on{display:block}
#home{padding:22px 24px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;cursor:pointer;transition:border-color .15s}
.card:hover{border-color:var(--acc)}
.card h2{font-size:16px;display:flex;justify-content:space-between;align-items:baseline}
.card h2 .date{font-size:11px;color:var(--mut);font-weight:400}
.kpis{display:flex;gap:18px;margin:10px 0 12px}
.kpi b{font-size:18px;display:block}
.kpi span{font-size:11px;color:var(--mut)}
.segline{font-size:12.5px;color:var(--mut);margin:2px 0}
.segline b{color:var(--fg);font-weight:500}
.lds{margin-top:10px;border-top:1px dashed var(--line);padding-top:8px;
display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:12px}
.lds .seg{color:var(--mut)}
.up{color:var(--up)}.dn{color:var(--dn)}.flat{color:var(--mut)}
.note{margin-top:18px;color:var(--mut);font-size:12px}
.subtabs{display:flex;gap:6px;padding:10px 24px}
.subtabs button{background:none;border:1px solid var(--line);color:var(--mut);
border-radius:6px;padding:4px 14px;font-size:13px;cursor:pointer}
.subtabs button.on{background:#21262d;color:var(--fg);border-color:var(--acc)}
.frame{display:none;width:100%;border:0;height:calc(100vh - 132px)}
.frame.on{display:block}
"""


def build() -> None:
    ovs = {}
    for ch in CHAINS:
        ovs[ch["key"]] = chain_overview(load_dash(ROOT / ch["dash"]))

    dates = sorted({o["updated"] for o in ovs.values()})
    latest = dates[-1]

    cards = []
    for ch in CHAINS:
        o = ovs[ch["key"]]
        top = "　".join(
            f"<b>{r['short']}</b> {pct(r['med'])}" for r in o["top"])
        bot = "　".join(
            f"<b>{r['short']}</b> {pct(r['med'])}" for r in o["bottom"])
        lds = "".join(
            f'<div><span class="seg">{l["seg"]}</span> {l["name"]} {pct(l["daily"])}</div>'
            for l in o["leaders"])
        cards.append(f"""
    <div class="card" onclick="go('{ch['key']}')">
      <h2>{ch['name']}产业链 <span class="date">更新 {o['updated']} · {o['total']} 家</span></h2>
      <div class="kpis">
        <div class="kpi"><b>{pct(o['med'])}</b><span>全链中位涨跌幅</span></div>
        <div class="kpi"><b>{o['rise']*100:.0f}%</b><span>上涨家数占比</span></div>
      </div>
      <div class="segline">领涨 {top}</div>
      <div class="segline">领跌 {bot}</div>
      <div class="lds">{lds}</div>
    </div>""")

    pages = []
    for ch in CHAINS:
        pages.append(f"""
  <div class="page" id="pg-{ch['key']}">
    <div class="subtabs">
      <button class="on" onclick="sub(this,'{ch['key']}','map')">产业链图谱</button>
      <button onclick="sub(this,'{ch['key']}','dash')">行情看板</button>
    </div>
    <iframe class="frame on" id="fr-{ch['key']}-map" data-src="{ch['map']}"></iframe>
    <iframe class="frame" id="fr-{ch['key']}-dash" data-src="{ch['dash']}"></iframe>
  </div>""")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>产业链雷达 · Chain Radar</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>产业链雷达</h1>
  <span class="mut">行情数据更新至 {latest}（通联数据，前复权）· 每交易日 16:00 自动刷新</span>
</header>
<nav class="tabs">
  <button class="on" onclick="go('home')">总览</button>
  <button onclick="go('ai')">人工智能</button>
  <button onclick="go('pharma')">医药</button>
  <button onclick="go('robot')">机器人</button>
  <button onclick="go('metal')">有色金属</button>
</nav>

<div class="page on" id="pg-home">
  <div id="home">
    <div class="cards">{''.join(cards)}
    </div>
    <p class="note">点击卡片进入对应产业链。环节涨跌幅为该环节成分股当日涨跌幅中位数；上涨家数占比按环节成分股加权。龙头 = 每环节最新流通市值最大的公司。</p>
  </div>
</div>
{''.join(pages)}

<script>
function go(k){{
  document.querySelectorAll('nav.tabs button').forEach(function(b,i){{
    b.classList.toggle('on', ['home','ai','pharma','robot','metal'][i]===k);}});
  document.querySelectorAll('.page').forEach(function(p){{
    p.classList.toggle('on', p.id==='pg-'+k);}});
  var pg=document.getElementById('pg-'+k);
  if(pg)pg.querySelectorAll('iframe').forEach(function(f){{
    if(!f.src)f.src=f.dataset.src;}});
  window.scrollTo(0,0);
}}
function sub(btn,k,kind){{
  btn.parentNode.querySelectorAll('button').forEach(function(b){{b.classList.remove('on')}});
  btn.classList.add('on');
  ['map','dash'].forEach(function(t){{
    var f=document.getElementById('fr-'+k+'-'+t);
    f.classList.toggle('on',t===kind);
    if(t===kind&&!f.src)f.src=f.dataset.src;}});
}}
</script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"portal -> {OUT} ({OUT.stat().st_size} bytes), latest={latest}")


if __name__ == "__main__":
    build()
