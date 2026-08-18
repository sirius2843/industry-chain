#!/usr/bin/env python3
"""Refresh chain market dashboards (ai / pharma / robot).

数据源：通联数据 WMCloud market/getMktEqudAdj（前复权日线，自带
negMarketValue 流通市值 / marketValue 总市值）。凭据 config/wmcloud_token.txt。

Phases（均断点续跑）:
  fetch : 50 家/批拉前复权日线（2026-06-01 起）-> data/dash_wm[_<chain>]/px_NN.csv
  build : 重算 snap / segstats / summary / leaders（每环节取最新流通市值
          最大的公司为唯一龙头）并写回看板 HTML。非 AI 看板首次运行时
          自动从 AI 看板外壳生成（替换标题/分组/环节描述/页脚来源）。

Usage:
  python3 refresh_dashboard.py --chain ai --phase fetch [--time-budget 280]
  python3 refresh_dashboard.py --chain ai --phase build
  python3 refresh_dashboard.py --chain pharma --phase fetch
  python3 refresh_dashboard.py --chain pharma --phase build
  python3 refresh_dashboard.py --chain robot --phase fetch
  python3 refresh_dashboard.py --chain robot --phase build
"""
from __future__ import annotations

import argparse
import csv
import gzip
import http.client
import json
import re
import statistics
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / "config" / "wmcloud_token.txt"
PRICE_START = "20260601"
BATCH = 50

CHAIN_META = {
    "pharma": {
        "dash": "pharma-chain-dashboard.html",
        "px": "data/dash_wm_pharma",
        "map": "医药产业链图谱.html",
        "map_name": "医药产业链图谱",
        "title": "医药产业链行情看板",
        "h1": "医药产业链 · 行情看板",
        "groups": ["制药", "创新药", "中药", "医疗器械", "医疗服务", "医药商业"],
        "group_desc": {
            "制药": "化学制剂与原料药/中间体制造",
            "创新药": "Biotech 创新药与生物制品（疫苗/血制品/生长激素）",
            "中药": "品牌中药与中药饮片/配方颗粒",
            "医疗器械": "医疗设备 · 高值耗材 · IVD 与低值耗材",
            "医疗服务": "CXO 研发生产外包 · 专科医院与医美 · ICL 诊断服务",
            "医药商业": "医药流通批发与零售药店",
        },
        "seg_desc": {
            "pharma-chem": "化学仿制药与制剂出口，集采常态化下看创新转型与出海。",
            "pharma-api": "大宗/特色原料药及中间体，价格周期与环保供给约束驱动弹性。",
            "inno-drug": "Biotech 与 License-out 主线，BD 出海与商业化兑现驱动估值。",
            "inno-bio": "疫苗、血制品、生长激素等生物药，浆站资源与批签发为核心壁垒。",
            "tcm-brand": "老字号与独家品种，品牌溢价叠加渠道库存周期。",
            "tcm-granule": "中药饮片炮制与配方颗粒，国标切换后放量逻辑。",
            "device-equip": "影像、监护、内镜等设备，招采恢复与国产替代双驱动。",
            "device-consumable": "心血管/骨科/眼科等植入介入耗材，集采以价换量。",
            "device-ivd": "体外诊断试剂与仪器、低值耗材，化学发光国产替代主线。",
            "service-cxo": "药物研发与生产外包，全球投融资周期决定订单能见度。",
            "service-hospital": "眼科/口腔/体检等连锁专科与医美服务，消费医疗属性。",
            "service-icl": "第三方医学检验与诊断服务，特检占比提升是核心逻辑。",
            "commerce-dist": "药品批发分销，两票制后行业集中度持续提升。",
            "commerce-retail": "连锁药房，处方外流与门诊统筹带来增量。",
        },
        "exclude_groups": {"待定"},
    },
    "robot": {
        "dash": "robot-chain-dashboard.html",
        "px": "data/dash_wm_robot",
        "map": "机器人产业链图谱.html",
        "map_name": "机器人产业链图谱",
        "title": "机器人产业链行情看板",
        "h1": "机器人产业链 · 行情看板",
        "groups": ["上游", "中游", "下游"],
        "group_desc": {
            "上游": "核心零部件：减速器 · 丝杠 · 电机 · 传感器 · 材料",
            "中游": "本体、关节模组、集成与具身智能",
            "下游": "场景应用与服务机器人",
        },
        "seg_desc": {
            "robot-reducer": "谐波/RV/行星减速器，关节核心传动部件，国产替代已见成效。",
            "robot-screw": "行星滚柱丝杠与导轨，直线执行器核心，人形机器人弹性最大的环节之一。",
            "robot-motor": "伺服系统、空心杯/步进电机，关节与灵巧手的动力源。",
            "robot-sensor": "六维力/触觉/视觉传感器与机器视觉，机器人感知层。",
            "robot-material": "PEEK 等轻量化材料与精密结构件，减重主线。",
            "robot-joint": "机电执行器与关节模组总成，T 链核心环节，价值量占比高。",
            "robot-body": "人形机器人本体与整机集成，产业链核心价值锚。",
            "robot-industrial": "工业机器人本体与系统集成，制造业自动化基本盘。",
            "robot-ai": "运动控制、机器人软件与具身智能大模型。",
            "robot-app": "家用/配送/巡检/手术等服务与特种机器人，商业化最先落地。",
        },
        "exclude_groups": {"待定"},
    },
    "metal": {
        "dash": "metal-chain-dashboard.html",
        "px": "data/dash_wm_metal",
        "map": "有色金属产业链图谱.html",
        "map_name": "有色金属产业链图谱",
        "title": "有色金属产业链行情看板",
        "h1": "有色金属产业链 · 行情看板",
        "groups": ["工业金属", "贵金属", "小金属", "稀土磁材", "能源金属"],
        "group_desc": {
            "工业金属": "铜 · 铝 · 铅锌 · 锡与镍",
            "贵金属": "黄金 · 白银",
            "小金属": "钨与钼 · 锑 · 钛与锆 · 其他小金属",
            "稀土磁材": "稀土矿与分离 · 永磁材料",
            "能源金属": "锂 · 钴",
        },
        "seg_desc": {
            "metal-copper": "铜矿采选与冶炼加工，电网投资与新能源需求叠加供给约束。",
            "metal-alu": "铝土矿-氧化铝-电解铝，产能天花板下看水电铝与再生铝。",
            "metal-pbzn": "铅锌采选冶炼，加工费与矿山供给周期驱动。",
            "metal-tin-ni": "锡焊料与镍（不锈钢/电池），供给集中度高、弹性大。",
            "metal-gold": "黄金采选冶炼，实际利率与央行购金主导价格中枢。",
            "metal-silver": "白银及伴生银，贵金属属性叠加光伏银浆工业需求。",
            "metal-w-mo": "钨（硬质合金）与钼（钢铁添加剂），供给配额制品种。",
            "metal-sb": "锑矿采选与锑品，光伏玻璃澄清剂需求拉动，供给刚性。",
            "metal-ti": "钛白粉与海绵钛/钛材，军工航空与化工双轮驱动。",
            "metal-other": "镁、锗、镓、铟等其他小金属，战略属性与出口管制主题。",
            "metal-rare": "稀土矿开采与冶炼分离，配额管理与整合预期是核心变量。",
            "metal-magnet": "钕铁硼永磁材料，新能源车与机器人需求拉动。",
            "metal-li": "锂矿、盐湖提锂与锂盐加工，供需再平衡是价格主线。",
            "metal-co": "钴矿与钴盐，刚果金供给政策与三元电池需求博弈。",
        },
        "exclude_groups": {"待定"},
    },
}

CHAINS = {
    "ai": {"dash": "ai-chain-dashboard.html", "px": "data/dash_wm"},
    **{k: {"dash": v["dash"], "px": v["px"]} for k, v in CHAIN_META.items()},
}

T0 = time.time()


def wm_get(api: str, query: dict, timeout: int = 60) -> list[dict]:
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    path = "/data/v1/api/" + api + ".json?" + urllib.parse.urlencode(query)
    last = ""
    for _ in range(2):
        conn = None
        try:
            conn = http.client.HTTPSConnection("api.wmcloud.com", 443, timeout=timeout)
            conn.request("GET", path, headers={
                "Authorization": "Bearer " + token,
                "Accept-Encoding": "gzip",
                "User-Agent": "industry-chain-dashboard/1.0",
            })
            resp = conn.getresponse()
            raw = resp.read()
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
            payload = json.loads(raw.decode("utf-8", "replace"))
            if resp.status == 200 and payload.get("retCode") == 1:
                return list(payload.get("data") or [])
            if payload.get("retCode") == -1:
                return []
            last = f"HTTP {resp.status} retCode={payload.get('retCode')} {payload.get('retMsg','')}"
            break
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    print(f"  WM ERROR {api}: {last}", file=sys.stderr)
    return []


def chain_master(chain: str) -> dict:
    """Load chain skeleton from the chain map HTML chainData (待定 excluded)."""
    meta = CHAIN_META[chain]
    html = (ROOT / meta["map"]).read_text(encoding="utf-8")
    m = re.search(r'<script id="chainData" type="application/json">(.*?)</script>',
                  html, re.S)
    raw = json.loads(m.group(1))
    segments = []
    for s in raw["segments"]:
        if s["group"] in meta["exclude_groups"]:
            continue
        cos = [{"n": c["n"], "c": c["c"], "r": c.get("r", ""),
                "p": c.get("p", ""), "mb": c.get("mb", ""), "l": 0}
               for c in s["cos"]]
        segments.append({"id": s["id"], "name": s["name"], "short": s["short"],
                         "group": s["group"], "cos": cos})
    total = sum(len(s["cos"]) for s in segments)
    return {"chain": raw["chain"], "updated": raw["updated"],
            "segments": segments, "total": total}


def build_shell(chain: str) -> str:
    """Create chain dashboard HTML from the AI dashboard shell."""
    meta = CHAIN_META[chain]
    html = (ROOT / "ai-chain-dashboard.html").read_text(encoding="utf-8")
    # drop AI DATA (build phase splices chain DATA in)
    html = re.sub(r"var DATA = \{.*?\};\n", "var DATA = {};\n", html, count=1, flags=re.S)
    html = html.replace("<title>AI 产业链行情看板</title>",
                        f"<title>{meta['title']}</title>")
    html = html.replace(
        "<h1>人工智能产业链 · 行情看板\n"
        "      <span class=\"flow\">上游 → 中游 → 下游</span>",
        f"<h1>{meta['h1']}\n      <span class=\"flow\">"
        + " → ".join(meta["groups"]) + "</span>")
    html = html.replace(
        'var GROUPS = ["上游","中游","下游"];',
        "var GROUPS = " + json.dumps(meta["groups"], ensure_ascii=False) + ";")
    gd = "var GROUP_DESC = {\n" + ",\n".join(
        f'    {json.dumps(k, ensure_ascii=False)}:{json.dumps(v, ensure_ascii=False)}'
        for k, v in meta["group_desc"].items()) + "\n  };"
    html = re.sub(r"var GROUP_DESC = \{.*?\n  \};", gd, html, count=1, flags=re.S)
    sd = "var SEG_DESC = {\n" + ",\n".join(
        f'    {json.dumps(k, ensure_ascii=False)}:{json.dumps(v, ensure_ascii=False)}'
        for k, v in meta["seg_desc"].items()) + "\n  };"
    html = re.sub(r"var SEG_DESC = \{.*?\n  \};", sd, html, count=1, flags=re.S)
    pm = chain_master(chain)
    html = re.sub(
        r"分类与个股取自 AI产业链图谱[^<]*。",
        f"分类与个股取自{meta['map_name']}（iFinD 验证，{pm['total']} 家 / {len(pm['segments'])} 环节）。",
        html, count=1)
    return html


def load_dash_data(chain: str) -> dict:
    dash = ROOT / CHAINS[chain]["dash"]
    if chain != "ai" and not dash.exists():
        dash.write_text(build_shell(chain), encoding="utf-8")
        print(f"{chain} dashboard shell created -> {dash}")
    html = dash.read_text(encoding="utf-8")
    m = re.search(r"var DATA = (\{.*?\});\n", html, re.S)
    data = json.loads(m.group(1))
    if not data:  # fresh shell
        data = {"master": chain_master(chain)}
    return data


def all_codes(data: dict) -> list[str]:
    return [c["c"] for s in data["master"]["segments"] for c in s["cos"]]


def wm_ticker(code: str) -> str:
    return code.split(".")[0]


# ---------------------------------------------------------------- fetch
def phase_fetch(chain: str, budget: float) -> None:
    import datetime as dt
    end = dt.date.today().strftime("%Y%m%d")
    px_dir = ROOT / CHAINS[chain]["px"]
    data = load_dash_data(chain)
    codes = all_codes(data)
    px_dir.mkdir(parents=True, exist_ok=True)
    groups = [codes[i:i + BATCH] for i in range(0, len(codes), BATCH)]
    todo = []
    for i, grp in enumerate(groups):
        fp = px_dir / f"px_{i:02d}.csv"
        if fp.exists() and fp.stat().st_size > 10_000:
            continue
        todo.append((i, grp, fp))
    print(f"[{chain}] {len(codes)} companies, {len(groups)} batches, {len(todo)} to fetch")
    fields = "ticker,tradeDate,secShortName,closePrice,negMarketValue,marketValue,isOpen"
    for i, grp, fp in todo:
        if time.time() - T0 > budget:
            print("time budget reached, re-run to resume")
            return
        tickers = ",".join(wm_ticker(c) for c in grp)
        rows = wm_get("market/getMktEqudAdj", {
            "ticker": tickers, "beginDate": PRICE_START, "endDate": end,
            "field": fields,
        })
        if not rows:
            print(f"[px {i:02d}] FAIL/empty ({len(grp)} tickers)")
            continue
        with open(fp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["ticker", "tradeDate", "secShortName",
                                              "closePrice", "negMarketValue",
                                              "marketValue", "isOpen"])
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in w.fieldnames})
        print(f"[px {i:02d}] OK {len(rows)} rows -> {fp.name}", flush=True)
    print("fetch phase done")


# ---------------------------------------------------------------- build
def board_limit(code: str) -> float:
    num, exch = code.split(".")
    if exch == "BJ" or num.startswith(("8", "4", "920")):
        return 0.30
    if num.startswith(("688", "689", "300", "301", "302")):
        return 0.20
    return 0.10


def read_prices(chain: str, data: dict) -> dict[str, list[dict]]:
    """full code -> [{date, close, cap}] sorted by date."""
    series: dict[str, list[dict]] = {}
    t2c = {}
    for c in all_codes(data):
        t2c.setdefault(wm_ticker(c), c)
    for fp in sorted((ROOT / CHAINS[chain]["px"]).glob("px_*.csv")):
        with open(fp, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                code = t2c.get(row["ticker"])
                if not code:
                    continue
                try:
                    close = float(row["closePrice"])
                except (KeyError, ValueError):
                    continue
                cap = None
                try:
                    cap = float(row.get("negMarketValue") or "") or None
                except ValueError:
                    pass
                series.setdefault(code, []).append(
                    {"date": row["tradeDate"], "close": close, "cap": cap})
    for code in series:
        series[code].sort(key=lambda x: x["date"])
    return series


def pct(a: float, b: float) -> float | None:
    return a / b - 1 if b else None


def phase_build(chain: str) -> None:
    data = load_dash_data(chain)
    master = data["master"]
    series = read_prices(chain, data)
    latest = max(r["date"] for s in series.values() for r in s)
    updated = latest
    print(f"[{chain}] latest trade date: {updated}; series for {len(series)} codes")

    # ---- snap
    snap: dict[str, dict] = {}
    dailies_y: dict[str, float] = {}
    for s in master["segments"]:
        for co in s["cos"]:
            code = co["c"]
            closes = [r["close"] for r in series.get(code, [])]
            rec = {"n": co["n"], "daily": None, "w5": None, "w20": None,
                   "last": None, "spark": None}
            if len(closes) >= 2:
                rec["daily"] = pct(closes[-1], closes[-2])
                rec["last"] = closes[-1]
                if len(closes) >= 3:
                    dailies_y[code] = pct(closes[-2], closes[-3])
            if len(closes) >= 6:
                rec["w5"] = pct(closes[-1], closes[-6])
            if len(closes) >= 21:
                rec["w20"] = pct(closes[-1], closes[-21])
            if closes:
                rec["spark"] = closes[-20:]
            snap[code] = rec

    # ---- leaders: 每环节取最新流通市值最大的公司为唯一龙头
    leaders: dict[str, dict] = {}
    for s in master["segments"]:
        best, best_cap = None, -1.0
        for co in s["cos"]:
            co["l"] = 0
            rows = series.get(co["c"], [])
            cap = rows[-1]["cap"] if rows else None
            if cap and cap > best_cap:
                best, best_cap = co, cap
        if best is not None:
            best["l"] = 1
            leaders[s["id"]] = {"code": best["c"], "name": best["n"], "by": "cap"}
        else:
            print(f"WARN no cap data for segment {s['id']} ({s['short']})")

    # ---- segstats
    today_daily = {c: r["daily"] for c, r in snap.items() if r["daily"] is not None}

    def limit_hits(seg, daily_map, sign):
        n = 0
        for co in seg["cos"]:
            v = daily_map.get(co["c"])
            if v is None:
                continue
            lim = board_limit(co["c"])
            if sign > 0 and abs(v - lim) <= 0.011:
                n += 1
            elif sign < 0 and abs(v + lim) <= 0.011:
                n += 1
        return n

    raw_stats = {}
    for s in master["segments"]:
        vals = [snap[co["c"]]["daily"] for co in s["cos"]
                if snap[co["c"]]["daily"] is not None]
        raw_stats[s["id"]] = {
            "n": len(vals),
            "med": statistics.median(vals) if vals else None,
            "mean": (sum(vals) / len(vals)) if vals else None,
            "rise": (sum(1 for v in vals if v > 0) / len(vals)) if vals else None,
            "lu": limit_hits(s, today_daily, +1),
            "ld": limit_hits(s, today_daily, -1),
            "ylu": limit_hits(s, dailies_y, +1),
            "yld": limit_hits(s, dailies_y, -1),
        }
    order_lu = sorted(master["segments"], key=lambda s: -raw_stats[s["id"]]["lu"])
    order_ld = sorted(master["segments"], key=lambda s: -raw_stats[s["id"]]["ld"])
    order_ylu = sorted(master["segments"], key=lambda s: -raw_stats[s["id"]]["ylu"])
    order_yld = sorted(master["segments"], key=lambda s: -raw_stats[s["id"]]["yld"])
    rk = lambda lst: {s["id"]: i + 1 for i, s in enumerate(lst)}
    rank_lu, rank_ld, yrank_lu, yrank_ld = map(rk, (order_lu, order_ld, order_ylu, order_yld))
    segstats = {}
    for s in master["segments"]:
        st = dict(raw_stats[s["id"]])
        st["rank"] = rank_lu[s["id"]]
        st["rk_delta"] = yrank_lu[s["id"]] - rank_lu[s["id"]]
        st["rank_dn"] = rank_ld[s["id"]]
        st["rk_dn_delta"] = yrank_ld[s["id"]] - rank_ld[s["id"]]
        segstats[s["id"]] = st

    # ---- summary
    eligible = [s for s in master["segments"] if raw_stats[s["id"]]["n"] >= 5]

    def pack(s):
        st = raw_stats[s["id"]]
        return {"id": s["id"], "short": s["short"], "med": st["med"],
                "mean": st["mean"], "rise": st["rise"], "n": st["n"]}

    top_up = [pack(s) for s in sorted(eligible, key=lambda s: -(raw_stats[s["id"]]["med"] or -9))[:3]]
    top_dn = [pack(s) for s in sorted(eligible, key=lambda s: (raw_stats[s["id"]]["med"] or 9))[:3]]
    best = max(eligible, key=lambda s: raw_stats[s["id"]]["rise"] or 0, default=None)
    best_rise = ({"short": best["short"], "rise": raw_stats[best["id"]]["rise"],
                  "n": raw_stats[best["id"]]["n"]} if best else None)

    reso_ok, reso_total, reso_diverge = 0, 0, []
    for s in master["segments"]:
        info = leaders.get(s["id"])
        st = raw_stats[s["id"]]
        if not info or st["med"] is None:
            continue
        ldaily = today_daily.get(info["code"])
        if ldaily is None:
            continue
        reso_total += 1
        same = (ldaily > 0 and st["med"] > 0) or (ldaily < 0 and st["med"] < 0) \
            or (ldaily == 0 and st["med"] == 0)
        if same:
            reso_ok += 1
        else:
            reso_diverge.append({"short": s["short"], "name": info["name"],
                                 "ld": ldaily, "med": st["med"]})
    summary = {"top_up": top_up, "top_dn": top_dn, "best_rise": best_rise,
               "reso_ok": reso_ok, "reso_total": reso_total,
               "reso_diverge": reso_diverge}

    # ---- splice back
    new_data = {"master": master, "snap": snap, "updated": updated,
                "segstats": segstats, "summary": summary, "leaders": leaders}
    dash = ROOT / CHAINS[chain]["dash"]
    html = dash.read_text(encoding="utf-8")
    new_html, nsub = re.subn(
        r"var DATA = \{.*?\};\n",
        "var DATA = " + json.dumps(new_data, ensure_ascii=False) + ";\n",
        html, count=1, flags=re.S,
    )
    if nsub != 1:
        print("ERROR: DATA block not replaced")
        sys.exit(1)
    dash.write_text(new_html, encoding="utf-8")
    missing = [c for c in all_codes(data) if snap[c]["daily"] is None]
    print(f"dashboard updated -> {dash} ({len(new_html)} bytes)")
    print(f"updated={updated}, leaders={len(leaders)}, "
          f"missing daily: {len(missing)} {missing[:8]}")
    for s in master["segments"]:
        info = leaders.get(s["id"])
        print(f"  leader {s['short']}: {info['name'] if info else '—'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", choices=["ai", "pharma", "robot", "metal"], default="ai")
    ap.add_argument("--phase", choices=["fetch", "build"], required=True)
    ap.add_argument("--time-budget", type=float, default=280.0)
    args = ap.parse_args()
    if args.phase == "fetch":
        phase_fetch(args.chain, args.time_budget)
    else:
        phase_build(args.chain)


if __name__ == "__main__":
    main()
