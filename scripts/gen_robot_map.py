#!/usr/bin/env python3
"""Generate the robot industry-chain interactive map (index.html) from validated data.

Reads references/chains/robot.draft.json + data/robot.validated.jsonl
+ data/robot.segment_leaders.jsonl and emits a self-contained HTML map
(Kimi token-based; optional standalone fallback tokens).

Template kept in sync with gen_map.py (AI chain) / gen_pharma_map.py.

Usage:
  python3 gen_robot_map.py --out <widget workspace>/index.html [--standalone-out <path>]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# 更名备注（Wind 2026-08-18 名称核对）
NOTES = {
    "301550.SZ": "Wind 简称现为 斯菱智驱，原斯菱股份（2026-08-18）",
}

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>机器人产业链图谱</title>
<style>
/* host-control safe zone (kimi-host-safe-zone.css) */
:root{--daimon-widget-host-safe-inline-end:190px;--daimon-widget-host-safe-block-start:44px}
.kimi-host-safe-context{container-type:inline-size}
.kimi-host-safe-header{box-sizing:border-box;min-block-size:var(--daimon-widget-host-safe-block-start,44px);padding-inline-end:var(--daimon-widget-host-safe-inline-end,190px)}
@container (max-width:419px){.kimi-host-safe-header{min-block-size:0;padding-block-start:var(--daimon-widget-host-safe-block-start,44px);padding-inline-end:0}}

*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent}
body{
  font-family:var(--kimi-font-sans,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif);
  color:var(--kimi-color-text-primary);
  letter-spacing:0;
  background-image:
    linear-gradient(var(--kimi-color-border) 1px,transparent 1px),
    linear-gradient(90deg,var(--kimi-color-border) 1px,transparent 1px);
  background-size:28px 28px;
  background-position:-1px -1px;
}
.wrap{max-width:1080px;margin:0 auto;padding:14px 18px 18px}
.grid-fade{/* keep grid subordinate */}
body{background-color:transparent}
.bgmask{position:fixed;inset:0;pointer-events:none;background:linear-gradient(180deg,transparent 0,transparent 40%,var(--kimi-color-surface) 100%);opacity:.35;z-index:-1}

header h1{font-size:19px;font-weight:650;line-height:1.3;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
header h1 .flow-arrow{color:var(--kimi-color-text-tertiary);font-weight:400}
.sub{color:var(--kimi-color-text-secondary);font-size:12px;margin-top:4px}
.stats{display:flex;gap:16px;flex-wrap:wrap;margin-top:10px}
.stat{min-width:0}
.stat output{display:block;font-size:22px;font-weight:650;line-height:1.1;font-variant-numeric:tabular-nums}
.stat span{font-size:11px;color:var(--kimi-color-text-tertiary)}

.controls{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;align-items:center}
.controls input[type=search]{
  flex:1 1 200px;min-width:0;padding:7px 11px;font-size:13px;font-family:inherit;
  color:var(--kimi-color-text-primary);background:var(--kimi-color-surface-muted);
  border:1px solid var(--kimi-color-border);border-radius:8px;outline:none;
}
.controls input[type=search]:focus-visible{border-color:var(--kimi-color-accent)}
.toggle{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--kimi-color-text-secondary);cursor:pointer;user-select:none;padding:6px 4px}
.toggle input{accent-color:var(--kimi-color-accent);width:15px;height:15px}
.match-info{font-size:12px;color:var(--kimi-color-text-tertiary)}

.detail{margin-top:12px;border:1px solid var(--kimi-color-border);border-radius:10px;background:var(--kimi-color-surface-raised);padding:12px 14px;min-height:74px}
.detail h2{font-size:14px;font-weight:650;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.detail .code{font-family:var(--kimi-font-mono,ui-monospace,monospace);font-size:12px;color:var(--kimi-color-text-tertiary)}
.detail dl{margin-top:6px;display:grid;grid-template-columns:auto 1fr;gap:4px 10px;font-size:12px}
.detail dt{color:var(--kimi-color-text-tertiary);white-space:nowrap}
.detail dd{color:var(--kimi-color-text-primary);line-height:1.55;min-width:0}
.detail .placeholder{color:var(--kimi-color-text-tertiary);font-size:12px;line-height:74px}
.leader-star{color:var(--kimi-color-accent);font-weight:700}
.badge{font-size:10px;padding:1px 7px;border-radius:99px;border:1px solid var(--kimi-color-accent);color:var(--kimi-color-accent);font-weight:600}

.tier{margin-top:18px}
.tier-head{display:flex;align-items:center;gap:10px}
.tier-head h2{font-size:15px;font-weight:650}
.tier-head .cnt{font-size:11px;color:var(--kimi-color-text-tertiary)}
.tier-head::after{content:"";flex:1;height:1px;background:var(--kimi-color-border)}
.tier-nav{display:flex;align-items:center;justify-content:center;gap:6px;color:var(--kimi-color-text-tertiary);font-size:11px;margin:14px 0 0}
.tier-nav svg{display:block}

.segs{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;margin-top:10px}
.seg{border:1px solid var(--kimi-color-border);border-radius:10px;background:var(--kimi-color-surface-raised);padding:10px 12px;min-width:0}
.seg h3{font-size:13px;font-weight:600;display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.seg h3 .n{min-width:0}
.seg h3 .c{font-size:10px;color:var(--kimi-color-text-tertiary);font-weight:400;white-space:nowrap}
.cos{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;position:relative}
.cos.collapsed{max-height:90px;overflow:hidden}
.cos-toggle{
  margin-top:6px;font-family:inherit;font-size:11px;line-height:1;padding:5px 9px;border-radius:7px;cursor:pointer;
  border:1px dashed var(--kimi-color-border);background:transparent;color:var(--kimi-color-text-tertiary);
  display:inline-flex;align-items:center;gap:4px;
}
.cos-toggle:hover{border-color:var(--kimi-color-accent);color:var(--kimi-color-accent)}
.co{
  font-family:inherit;font-size:12px;line-height:1;padding:6px 9px;border-radius:7px;cursor:pointer;
  border:1px solid var(--kimi-color-border);background:var(--kimi-color-surface);
  color:var(--kimi-color-text-primary);display:inline-flex;align-items:center;gap:4px;max-width:100%;
}
.co:hover{border-color:var(--kimi-color-accent)}
.co:focus-visible{outline:2px solid var(--kimi-color-accent);outline-offset:1px}
.co.leader{border-color:var(--kimi-color-accent);background:color-mix(in srgb,var(--kimi-color-accent) 8%,var(--kimi-color-surface))}
.co.sel{background:var(--kimi-color-accent);color:var(--kimi-color-on-accent);border-color:var(--kimi-color-accent)}
.co.sel .leader-star{color:var(--kimi-color-on-accent)}
.co.dim{opacity:.22}
.seg.dim{opacity:.35}

footer{margin-top:20px;padding-top:10px;border-top:1px solid var(--kimi-color-border);font-size:11px;color:var(--kimi-color-text-tertiary);line-height:1.7}

@media (max-width:519px){
  .wrap{padding:10px 12px 14px}
  header h1{font-size:16px}
  .segs{grid-template-columns:1fr}
  .stats{gap:12px}
  .stat output{font-size:18px}
}
@media (min-width:520px) and (max-width:759px){
  .segs{grid-template-columns:repeat(2,1fr)}
}
@media (prefers-reduced-motion:no-preference){
  .co{transition:border-color .15s,background-color .15s,opacity .15s}
  .seg{transition:opacity .15s}
}
</style>
</head>
<body>
<main class="wrap kimi-host-safe-context">
  <header class="kimi-host-safe-header" data-kimi-priority="p0">
    <h1>机器人产业链图谱
      <span class="flow-arrow" aria-hidden="true">上游 → 中游 → 下游</span>
    </h1>
    <p class="sub" id="subLine"></p>
    <div class="stats" role="group" aria-label="产业链概览统计">
      <div class="stat"><output id="stSeg"></output><span>环节</span></div>
      <div class="stat"><output id="stCo"></output><span>公司</span></div>
      <div class="stat"><output id="stLd"></output><span>环节龙头</span></div>
      <div class="stat"><output>2025</output><span>龙头验证年报</span></div>
    </div>
  </header>

  <section class="controls" data-kimi-priority="p1" aria-label="筛选">
    <input type="search" id="q" placeholder="搜索公司 / 代码 / 主营产品…" aria-label="搜索公司、代码或主营产品">
    <label class="toggle"><input type="checkbox" id="ldOnly"> 只看龙头</label>
    <span class="match-info" id="matchInfo" aria-live="polite"></span>
  </section>

  <section class="detail" id="detail" data-kimi-priority="p2" aria-live="polite" aria-label="公司详情">
    <p class="placeholder">点击任意公司，查看代码、主营产品、环节角色与龙头年报验证。</p>
  </section>

  <div id="tiers"></div>

  <footer data-kimi-priority="p3">
    数据来源：候选发现 = Wind 概念板块（人形机器人/机器人/工业机器人/具身智能/机器人关节/减速器/传感器/机器视觉/PEEK材料/智能制造/机器换人等 15 个板块，2026-08-18 采集，346 家；丝杠/伺服/本体/应用等无对应板块环节经 Wind 代码核验补入 7 家）；公司主营/产品 = iFinD ifind_get_stock_info（2026-08-18 拉取，350/350 验证通过）；龙头收入构成 = iFinD 业务分部（2025 年报，14 家龙头）。<br>
    环节归属：命中减速器/PEEK材料/传感器/机器视觉/机器人关节/人形机器人/工业机器人/具身智能板块的公司按板块自动归段，丝杠/伺服/应用等环节按主营人工归段；仅命中泛板块（机器人/智能制造/机器换人）的 36 家列入「待定」。301550 已更名斯菱智驱。<br>
    本图谱为经数据源验证的半静态骨架；行情、估值、最新财务请以 Wind/iFinD 实时查询为准。
  </footer>
</main>

<script id="chainData" type="application/json">__DATA__</script>
<script>
(function(){
  var DATA=JSON.parse(document.getElementById('chainData').textContent);
  var tiersEl=document.getElementById('tiers');
  var GROUPS=["上游","中游","下游","待定"];
  var GROUP_DESC={
    "上游":"核心零部件：减速器 · 丝杠 · 电机 · 传感器 · 材料",
    "中游":"本体、关节模组、集成与具身智能",
    "下游":"场景应用与服务机器人",
    "待定":"Wind 概念板块命中，环节归属待进一步甄别"
  };
  var leaderN=0;
  DATA.segments.forEach(function(s){s.cos.forEach(function(co){if(co.l)leaderN++})});
  document.getElementById("stSeg").textContent=DATA.segments.length;
  document.getElementById("stCo").textContent=DATA.total;
  document.getElementById("stLd").textContent=leaderN;
  document.getElementById("subLine").textContent=DATA.segments.length+" 个环节 · "+DATA.total+" 家已验证公司 · 点击公司查看主营与龙头验证数据";
  var selected=null;
  var COLLAPSE_H=90; /* ≈3行公司标签(26px行高+6px间距) */

  function el(tag,cls,txt){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}

  function setupCollapse(box,card){
    box.classList.add("collapsed");
    if(box.scrollHeight<=box.clientHeight+2){box.classList.remove("collapsed");return}
    var hidden=0;
    Array.prototype.forEach.call(box.children,function(ch){if(ch.offsetTop>=box.clientHeight)hidden++});
    if(!hidden){box.classList.remove("collapsed");return}
    var t=el("button","cos-toggle","展开其余 "+hidden+" 家 ▾");
    t.type="button";
    t.setAttribute("aria-expanded","false");
    t.dataset.label="展开其余 "+hidden+" 家 ▾";
    box.dataset.cl="1";
    t.addEventListener("click",function(){
      var wasCollapsed=box.classList.contains("collapsed");
      if(wasCollapsed){box.classList.remove("collapsed");t.textContent="收起 ▴";t.setAttribute("aria-expanded","true")}
      else{box.classList.add("collapsed");t.textContent="展开其余 "+hidden+" 家 ▾";t.setAttribute("aria-expanded","false")}
    });
    card.appendChild(t);
  }

  GROUPS.forEach(function(g){
    var segs=DATA.segments.filter(function(s){return s.group===g});
    if(!segs.length)return;
    var coN=segs.reduce(function(a,s){return a+s.cos.length},0);
    var tier=el("section","tier");tier.setAttribute("aria-label",g);
    var th=el("div","tier-head");
    th.appendChild(el("h2",null,g));
    th.appendChild(el("span","cnt",segs.length+" 环节 · "+coN+" 家"));
    tier.appendChild(th);
    tier.appendChild(el("p","sub",GROUP_DESC[g]));
    var grid=el("div","segs");
    segs.forEach(function(s){
      var card=el("div","seg");card.dataset.seg=s.id;
      var h=el("h3");
      h.appendChild(el("span","n",s.short));h.appendChild(el("span","c",s.cos.length+" 家"));
      card.appendChild(h);
      var box=el("div","cos");
      s.cos.forEach(function(co){
        var b=el("button","co"+(co.l?" leader":""),null);
        b.type="button";
        if(co.l){var st=el("span","leader-star","★");st.setAttribute("aria-hidden","true");b.appendChild(st)}
        b.appendChild(el("span",null,co.n));
        b.setAttribute("aria-label",co.n+" "+co.c+(co.l?"，环节龙头":""));
        b.dataset.code=co.c;b.dataset.seg=s.id;
        b.addEventListener("click",function(){select(co,s,b)});
        box.appendChild(b);
      });
      card.appendChild(box);
      grid.appendChild(card);
    });
    tier.appendChild(grid);
    tiersEl.appendChild(tier);
    if(g==="上游"||g==="中游"){
      var nav=el("div","tier-nav");
      nav.innerHTML='<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 2v10M3.5 8.5 8 13l4.5-4.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg><span>流向下游环节</span>';
      if(g==="中游")nav.querySelector("span").textContent="流向下游应用";
      tiersEl.appendChild(nav);
    }
  });

  /* 必须在卡片挂入文档后测量高度，否则 scrollHeight/clientHeight 均为 0 */
  document.querySelectorAll("#tiers .cos").forEach(function(box){
    setupCollapse(box, box.parentElement);
  });

  function select(co,seg,btn){
    if(selected)selected.classList.remove("sel");
    selected=btn;btn.classList.add("sel");
    var d=document.getElementById("detail");
    d.textContent="";
    var h=el("h2");
    if(co.l){var st=el("span","leader-star","★");st.setAttribute("aria-hidden","true");h.appendChild(st)}
    h.appendChild(el("span",null,co.n));
    h.appendChild(el("span","code",co.c));
    if(co.l){var bd=el("span","badge","环节龙头");h.appendChild(bd)}
    d.appendChild(h);
    var dl=el("dl");
    function row(k,v){if(!v)return;dl.appendChild(el("dt",null,k));dl.appendChild(el("dd",null,v))}
    row("所属环节",seg.name);
    row("环节角色",co.r);
    row("主营产品",co.p);
    if(co.mb)row("主营业务",co.mb);
    if(co.wc)row("Wind概念",co.wc);
    if(co.h)row("龙头验证",co.h);
    if(co.note)row("备注",co.note);
    d.appendChild(dl);
  }

  var q=document.getElementById("q"),ld=document.getElementById("ldOnly"),info=document.getElementById("matchInfo");
  function applyFilter(){
    var kw=q.value.trim().toLowerCase();
    var onlyLd=ld.checked;
    var filtering=!!(kw||onlyLd);
    document.querySelectorAll(".cos[data-cl]").forEach(function(b){b.classList.toggle("collapsed",!filtering)});
    document.querySelectorAll(".cos-toggle").forEach(function(t){
      t.style.display=filtering?"none":"";
      if(!filtering){t.textContent=t.dataset.label;t.setAttribute("aria-expanded","false")}
    });
    var shown=0,total=0;
    document.querySelectorAll(".seg").forEach(function(card){
      var anyCo=false;
      card.querySelectorAll(".co").forEach(function(b){
        total++;
        var co=findCo(b.dataset.code);
        var hay=(co.n+" "+co.c+" "+(co.p||"")+" "+(co.r||"")+" "+(co.wc||"")).toLowerCase();
        var ok=(!kw||hay.indexOf(kw)>=0)&&(!onlyLd||co.l);
        b.classList.toggle("dim",!ok);
        if(ok){anyCo=true;shown++}
      });
      card.classList.toggle("dim",!anyCo);
    });
    info.textContent=(kw||onlyLd)?("匹配 "+shown+" / "+total+" 家"):"";
  }
  var coIdx={};
  DATA.segments.forEach(function(s){s.cos.forEach(function(co){coIdx[co.c]=co})});
  function findCo(code){return coIdx[code]}
  q.addEventListener("input",applyFilter);
  ld.addEventListener("change",applyFilter);
})();
</script>
</body>
</html>
"""

FALLBACK_TOKENS = """
<style>
/* standalone fallback tokens (outside Daimon host) */
:root{
--kimi-color-text-primary:#1f2329;--kimi-color-text-secondary:#51565e;--kimi-color-text-tertiary:#8a9099;
--kimi-color-surface:#ffffff;--kimi-color-surface-muted:#f5f6f7;--kimi-color-surface-raised:#ffffff;
--kimi-color-border:#e4e7eb;--kimi-color-accent:#2f6bff;--kimi-color-on-accent:#ffffff}
@media (prefers-color-scheme:dark){:root{
--kimi-color-text-primary:#eceef1;--kimi-color-text-secondary:#b3b8c0;--kimi-color-text-tertiary:#7d838d;
--kimi-color-surface:#17191d;--kimi-color-surface-muted:#1e2126;--kimi-color-surface-raised:#1e2126;
--kimi-color-border:#2c3138;--kimi-color-accent:#6b93ff;--kimi-color-on-accent:#0d1020}}
body{background-color:var(--kimi-color-surface)}
</style>
"""


def load_highlights(root: Path) -> dict:
    """Build leader revenue-composition highlights from iFinD segmentation (2025年报)."""
    hl = {}
    fp = root / "data/robot.segment_leaders.jsonl"
    if not fp.exists():
        return hl
    for line in fp.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if "error" in r:
            continue
        comp = None
        for row in r.get("rows", []):
            c = (row.get("ths_main_business_composition_stock") or "").strip()
            if c:
                comp = c
                break
        if not comp:
            continue
        parts = []
        for item in comp.split(";"):
            if ":" in item:
                k, v = item.rsplit(":", 1)
                try:
                    parts.append(f"{k}{float(v.rstrip('%')):.1f}%")
                except ValueError:
                    parts.append(item)
        period = r.get("report_period", "20251231")
        hl[r["code"]] = f"{period[:4]}年报主营构成：" + "，".join(parts)
    return hl


def build_data(root: Path, draft_rel: str, validated_rel: str) -> dict:
    draft = json.loads((root / draft_rel).read_text(encoding="utf-8"))
    recs = {}
    for line in (root / validated_rel).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r["code"]] = r
    hl = load_highlights(root)
    segments = []
    for s in draft["segments"]:
        group = s["name"].split("·")[0]
        short = s["name"].split("·", 1)[1] if "·" in s["name"] else s["name"]
        cos = []
        for c in s["companies"]:
            r = recs.get(c["code"], {})
            prod = (r.get("main_products") or "").strip()
            mb = (r.get("main_business") or "").strip()
            wc = "、".join(c.get("concepts", [])) if c.get("concepts") else None
            cos.append({
                "n": c["name"], "c": c["code"], "r": c["role"],
                "p": prod[:300], "mb": mb[:200], "l": 1 if c.get("leader") else 0,
                **({"wc": wc} if wc else {}),
                **({"h": hl[c["code"]]} if c["code"] in hl else {}),
                **({"note": NOTES[c["code"]]} if c["code"] in NOTES else {}),
            })
        segments.append({"id": s["id"], "name": s["name"], "short": short, "group": group, "cos": cos})
    total = sum(len(s["cos"]) for s in segments)
    return {"chain": draft["chain_name"], "updated": draft["drafted"], "segments": segments, "total": total}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--draft", default="references/chains/robot.draft.json")
    ap.add_argument("--validated", default="data/robot.validated.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--standalone-out", default=None)
    args = ap.parse_args()
    root = Path(args.root)
    data = build_data(root, args.draft, args.validated)
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"widget html -> {out} ({len(html)} bytes, {data['total']} companies)")
    if args.standalone_out:
        sa = html.replace("</head>", FALLBACK_TOKENS + "\n</head>")
        Path(args.standalone_out).write_text(sa, encoding="utf-8")
        print(f"standalone -> {args.standalone_out}")


if __name__ == "__main__":
    main()
