#!/usr/bin/env python3
"""Validate & enrich an industry-chain draft via the iFinD plugin (agent-gw).

Reads a chain draft JSON (see references/chains/ai.draft.json), then:
  phase "info": batch-call ifind_get_stock_info (max 3 tickers/call) for every
                company; saves raw CSVs and a compact <chain>.validated.jsonl
  phase "seg":  batch-call ifind_get_stock_business_segmentation for segment
                leaders; tries 20251231 first, falls back to 20241231

Usage:
  python3 ifind_batch.py --draft references/chains/ai.draft.json \
      --out-dir data --phase info
  python3 ifind_batch.py --draft references/chains/ai.draft.json \
      --out-dir data --phase seg

All data comes from the iFinD datasource via agent-gw. Never invent values.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

IFIND_DIR = Path(
    "/Users/sirius/Library/Application Support/kimi-desktop/daimon-share/"
    "daimon/runtime/kimi-code/home/plugins/managed/ifind"
)
IFIND_TOOL = IFIND_DIR / "scripts" / "ifind_tool.py"

INFO_FIELDS = {
    "code": "thscode",
    "name": "ths_stock_short_name_stock",
    "main_products": "ths_mo_product_name_stock",
    "main_business": "ths_main_businuess_stock",
    "competitors": "ths_opponent_company_stock",
    "comparables": "ths_comparing_company_stock",
}


def run_ifind(api_name: str, params: dict) -> tuple[bool, str]:
    cmd = [
        sys.executable, str(IFIND_TOOL), "call",
        "--api-name", api_name,
        "--params-json", json.dumps(params, ensure_ascii=False),
    ]
    proc = subprocess.run(
        cmd, cwd=str(IFIND_DIR), capture_output=True, text=True, timeout=180
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out


def batches(items: list[dict], n: int = 3):
    for i in range(0, len(items), n):
        yield i // n + 1, items[i : i + n]


def phase_info(draft: dict, out_dir: Path) -> None:
    companies = [
        {**c, "segment": s["name"], "segment_id": s["id"]}
        for s in draft["segments"]
        for c in s["companies"]
    ]
    jsonl_path = out_dir / f"{draft['chain']}.validated.jsonl"
    records: dict[str, dict] = {}
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                records[rec["code"]] = rec
    # incremental: skip companies already validated without error
    todo = [c for c in companies if not (c["code"] in records and "error" not in records[c["code"]])]
    skipped = len(companies) - len(todo)
    if skipped:
        print(f"skip {skipped} already-validated companies")
    total = len(companies)

    for bno, group in batches(todo):
        tickers = ",".join(c["code"] for c in group)
        csv_path = out_dir / f"{draft['chain']}_info2_b{bno}.csv"
        if not csv_path.exists():
            ok, out = run_ifind(
                "ifind_get_stock_info",
                {"ticker": tickers, "file_path": str(csv_path)},
            )
            print(f"[info b{bno}] {tickers} -> {'OK' if ok else 'FAIL'}")
            if not ok:
                print(out[-600:])
                for c in group:
                    records.setdefault(c["code"], {**c, "error": "ifind_get_stock_info failed"})
                continue
        rows = {}
        if csv_path.exists():
            with open(csv_path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    rows[row.get("thscode", "")] = row
        for c in group:
            row = rows.get(c["code"])
            if not row:
                records[c["code"]] = {**c, "error": "missing in ifind response"}
                continue
            rec = {**c}
            for k, col in INFO_FIELDS.items():
                if k in ("code",):
                    continue
                rec[k] = (row.get(col) or "").strip()[:600]
            if row.get("ths_stock_short_name_stock", "").strip() != c["name"]:
                rec["name_mismatch"] = row.get("ths_stock_short_name_stock", "").strip()
            records[c["code"]] = rec

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for code, rec in records.items():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    ok_n = sum(1 for r in records.values() if "error" not in r)
    print(f"info phase done: {ok_n}/{len(companies)} validated -> {jsonl_path}")


def phase_seg(draft: dict, out_dir: Path) -> None:
    leaders = [
        {**c, "segment": s["name"]}
        for s in draft["segments"]
        for c in s["companies"]
        if c.get("leader")
    ]
    jsonl_path = out_dir / f"{draft['chain']}.segment_leaders.jsonl"
    records: list[dict] = []
    done_codes: set[str] = set()
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                records.append(rec)
                if "error" not in rec:
                    done_codes.add(rec["code"])
    todo = [c for c in leaders if c["code"] not in done_codes]
    if len(leaders) - len(todo):
        print(f"skip {len(leaders) - len(todo)} leaders already fetched")
    for bno, group in batches(todo):
        tickers = ",".join(c["code"] for c in group)
        got = None
        for period in ("20251231", "20241231"):
            csv_path = out_dir / f"{draft['chain']}_seg2_b{bno}_{period}.csv"
            ok, out = run_ifind(
                "ifind_get_stock_business_segmentation",
                {
                    "ticker": tickers,
                    "financial_parameter": period,
                    "file_path": str(csv_path),
                },
            )
            if ok and csv_path.exists() and csv_path.stat().st_size > 50:
                got = (period, csv_path)
                break
            print(f"[seg b{bno}] {tickers} period={period} -> retry/fail")
        if not got:
            print(f"[seg b{bno}] {tickers} -> FAIL both periods")
            for c in group:
                records.append({**c, "error": "segmentation failed"})
            continue
        period, csv_path = got
        print(f"[seg b{bno}] {tickers} -> OK ({period})")
        with open(csv_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for c in group:
            mine = [r for r in rows if c["code"] in json.dumps(r, ensure_ascii=False)]
            records.append({**c, "report_period": period, "rows": mine[:8]})
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"seg phase done: {len(records)} leaders -> {jsonl_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--phase", choices=["info", "seg"], required=True)
    args = ap.parse_args()
    draft = json.loads(Path(args.draft).read_text(encoding="utf-8"))
    # ifind_tool.py writes files relative to the plugin cwd, so pass absolute paths
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.phase == "info":
        phase_info(draft, out_dir)
    else:
        phase_seg(draft, out_dir)


if __name__ == "__main__":
    main()
