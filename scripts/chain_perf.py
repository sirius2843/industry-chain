#!/usr/bin/env python3
"""Compute rotation metrics for the AI industry chain from daily prices.

Reads data/prices/px_*.csv + references/chains/ai.draft.json, writes
data/ai.perf.json consumed by gen_dashboard.py.

Metrics per company: interval returns (YTD / since Apr / 1M / 3M).
Per segment: equal-weight mean+median interval returns, monthly return matrix,
weekly turnover share (close*volume proxy), YTD NAV curve, rotation flags.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
from pathlib import Path

import pandas as pd

ANCHORS = {
    "ytd": dt.date(2025, 12, 31),
    "apr": dt.date(2026, 3, 31),
    "m1": dt.date(2026, 6, 16),
    "m3": dt.date(2026, 4, 16),
}
ANCHOR_LABELS = {"ytd": "年初以来", "apr": "4月以来", "m1": "近1月", "m3": "近3月"}


def load_prices(px_dir: Path) -> pd.DataFrame:
    dfs = []
    for p in sorted(glob.glob(str(px_dir / "px_*.csv"))):
        dfs.append(pd.read_csv(p))
    df = pd.concat(dfs, ignore_index=True)
    df["date"] = pd.to_datetime(df["time"], format="%Y%m%d").dt.date
    df["amt"] = df["close"] * df["volume"]
    return df[["thscode", "date", "close", "amt"]]


def base_close(s: pd.Series, anchor: dt.date) -> float | None:
    """Close on the last trading day <= anchor."""
    sub = s[s.index <= anchor]
    if sub.empty:
        return None
    return float(sub.iloc[-1])


def interval_ret(s: pd.Series, anchor: dt.date) -> float | None:
    b = base_close(s, anchor)
    if b is None or b == 0:
        return None
    return float(s.iloc[-1]) / b - 1.0


def monthly_returns(s: pd.Series) -> dict[str, float]:
    last_of_month: dict[tuple[int, int], float] = {}
    for d, v in s.items():
        last_of_month[(d.year, d.month)] = float(v)
    out: dict[str, float] = {}
    prev = None
    for (y, mo) in sorted(last_of_month):
        v = last_of_month[(y, mo)]
        key = f"{y}-{mo:02d}"
        if prev is not None and prev != 0:
            out[key] = v / prev - 1.0
        prev = v
    # first month: from first close of that month
    first_key = f"{s.index[0].year}-{s.index[0].month:02d}"
    first_month = s[(s.index >= dt.date(s.index[0].year, s.index[0].month, 1))]
    if len(first_month) >= 2 and first_month.iloc[0] != 0:
        out[first_key] = float(first_month.iloc[-1]) / float(first_month.iloc[0]) - 1.0
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.root)
    out_path = Path(args.out) if args.out else root / "data" / "ai.perf.json"

    draft = json.loads((root / "references/chains/ai.draft.json").read_text(encoding="utf-8"))
    seg_of = {}
    meta_of = {}
    segs = []
    for s in draft["segments"]:
        grp = s["name"].split("·")[0]
        short = s["name"].split("·", 1)[1] if "·" in s["name"] else s["name"]
        segs.append({"id": s["id"], "name": s["name"], "short": short, "grp": grp,
                     "codes": [c["code"] for c in s["companies"]]})
        for c in s["companies"]:
            seg_of[c["code"]] = s["id"]
            meta_of[c["code"]] = {"n": c["name"], "leader": 1 if c.get("leader") else 0}

    px = load_prices(root / "data" / "prices")
    px_end = max(d for d in px["date"])
    have = set(px.thscode.unique())
    missing = [c for c in meta_of if c not in have]

    # per-company metrics
    companies = {}
    close_by = {}
    for code, g in px.groupby("thscode"):
        s = pd.Series(g["close"].values, index=list(g["date"])).sort_index()
        close_by[code] = s
        rets = {k: interval_ret(s, a) for k, a in ANCHORS.items()}
        companies[code] = {
            **meta_of[code], "c": code, "seg": seg_of[code],
            "rets": rets, "monthly": monthly_returns(s),
        }

    # chain median anchors (company-level, for flags)
    def med(vals):
        vals = sorted(v for v in vals if v is not None)
        if not vals:
            return None
        n = len(vals)
        return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2

    chain_med = {k: med([c["rets"][k] for c in companies.values()]) for k in ANCHORS}

    # weekly turnover share per segment (last 12 ISO weeks)
    px2 = px.copy()
    iso = pd.to_datetime(px2["date"].astype(str)).dt.isocalendar()
    px2["yw"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    weeks = sorted(px2["yw"].unique())[-12:]
    wk_total = px2[px2.yw.isin(weeks)].groupby("yw")["amt"].sum()

    months = sorted({m for c in companies.values() for m in c["monthly"]})
    seg_out = []
    for sg in segs:
        codes = [c for c in sg["codes"] if c in companies]
        comps = [companies[c] for c in codes]
        ret = {}
        for k in ANCHORS:
            vals = [c["rets"][k] for c in comps]
            vals_nn = [v for v in vals if v is not None]
            ret[k + "_mean"] = sum(vals_nn) / len(vals_nn) if vals_nn else None
            ret[k + "_med"] = med(vals)
        monthly = {}
        for m in months:
            vals = [c["monthly"][m] for c in comps if m in c["monthly"]]
            monthly[m] = sum(vals) / len(vals) if vals else None
        # weekly amount share
        sub = px2[(px2.thscode.isin(codes)) & (px2.yw.isin(weeks))]
        wk_amt = sub.groupby("yw")["amt"].sum()
        share = {w: (float(wk_amt.get(w, 0)) / float(wk_total[w]) if float(wk_total[w]) else None)
                 for w in weeks}
        # NAV (YTD base=100), weekly sampled
        anchor = ANCHORS["ytd"]
        navs = []
        for c in codes:
            s = close_by[c]
            b = base_close(s, anchor)
            if b:
                navs.append((s / b) * 100.0)
        nav_series = []
        if navs:
            nav_df = pd.concat(navs, axis=1).mean(axis=1)
            nav_df = nav_df[nav_df.index > anchor]
            sampled = list(nav_df.items())[:: max(1, len(nav_df) // 40)]
            if nav_df.items():
                last = list(nav_df.items())[-1]
                if not sampled or sampled[-1][0] != last[0]:
                    sampled.append(last)
            nav_series = [{"d": d.isoformat(), "v": round(float(v), 2)} for d, v in sampled]
        seg_out.append({
            **{k: sg[k] for k in ("id", "name", "short", "grp")},
            "n_co": len(codes),
            "leaders": [meta_of[c]["n"] for c in codes if meta_of[c]["leader"]],
            "ret": ret, "monthly": monthly, "amt_share": share, "nav": nav_series,
        })

    # rotation ranks & flags (mean anchor)
    def ranks(key):
        vals = [(s["id"], s["ret"][key]) for s in seg_out if s["ret"][key] is not None]
        vals.sort(key=lambda x: -x[1])
        return {sid: i + 1 for i, (sid, _) in enumerate(vals)}

    rk_ytd, rk_m1 = ranks("ytd_mean"), ranks("m1_mean")
    for s in seg_out:
        s["rank_ytd"] = rk_ytd.get(s["id"])
        s["rank_m1"] = rk_m1.get(s["id"])
        if s["rank_ytd"] is not None and s["rank_m1"] is not None:
            s["rank_shift"] = s["rank_ytd"] - s["rank_m1"]
        else:
            s["rank_shift"] = None
        weeks_sorted = weeks
        share_now = s["amt_share"].get(weeks_sorted[-1])
        share_4w = s["amt_share"].get(weeks_sorted[-5]) if len(weeks_sorted) >= 5 else None
        s["share_now"], s["share_4w"] = share_now, share_4w
        s["share_delta"] = (share_now - share_4w) if (share_now is not None and share_4w is not None) else None
        flags = []
        r_y, r_1 = s["ret"]["ytd_mean"], s["ret"]["m1_mean"]
        if r_y is not None and r_1 is not None and chain_med["ytd"] is not None and chain_med["m1"] is not None:
            if r_y < chain_med["ytd"] and r_1 > chain_med["m1"]:
                flags.append("转强")
            if r_y > chain_med["ytd"] and r_1 < chain_med["m1"]:
                flags.append("转弱")
        if s["share_delta"] is not None and s["share_delta"] > 0:
            flags.append("放量")
        s["flags"] = flags

    out = {
        "meta": {
            "chain": draft["chain_name"], "computed": dt.date.today().isoformat(),
            "px_start": "2025-12-01", "px_end": px_end.isoformat(),
            "covered": len(companies), "missing": missing,
            "anchors": {k: v.isoformat() for k, v in ANCHORS.items()},
            "anchor_labels": ANCHOR_LABELS,
            "chain_median": chain_med, "months": months, "weeks": weeks,
            "note": "收益为前复权口径；成交额=收盘价×成交量近似；并行科技(839493.BJ)北交所行情两源均未覆盖。",
        },
        "segments": seg_out,
        "companies": [
            {"c": c["c"], "n": c["n"], "seg": c["seg"], "leader": c["leader"], "rets": c["rets"]}
            for c in companies.values()
        ],
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"perf -> {out_path} ({out_path.stat().st_size} bytes, {len(companies)} companies, {len(seg_out)} segments)")


if __name__ == "__main__":
    main()
