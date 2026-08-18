#!/usr/bin/env python3
"""Batch-fetch daily prices for all validated chain companies via iFinD.

ifind_get_price: max 3 tickers/call, range <= 3 years, forward-adjusted by
default. CSVs land in data/prices/. Idempotent: a batch is skipped when its
CSV exists and is plausibly complete (>10KB). Re-run to resume after timeout.

Usage:
  python3 chain_prices.py --draft references/chains/ai.draft.json \
      --out-dir data/prices --start 2025-12-01 --end 2026-07-17
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from ifind_batch import run_ifind, batches


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--start", default="2025-12-01")
    ap.add_argument("--end", default=dt.date.today().isoformat())
    args = ap.parse_args()

    draft = json.loads(Path(args.draft).read_text(encoding="utf-8"))
    codes = [c["code"] for s in draft["segments"] for c in s["companies"]]
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    todo = []
    for i, group in batches([{"code": c} for c in codes]):
        csv_path = out_dir / f"px_{i:02d}.csv"
        tickers = ",".join(c["code"] for c in group)
        if csv_path.exists() and csv_path.stat().st_size > 10_000:
            continue
        todo.append((i, tickers, csv_path))

    print(f"{len(codes)} companies, {len(todo)} batches to fetch")
    for i, tickers, csv_path in todo:
        ok, out = run_ifind(
            "ifind_get_price",
            {
                "ticker": tickers,
                "start_date": args.start,
                "end_date": args.end,
                "file_path": str(csv_path),
                "interval": "D",
                "adjust": "forward",
            },
        )
        print(f"[px {i:02d}] {tickers} -> {'OK' if ok else 'FAIL'}")
        if not ok:
            print(out[-400:])


if __name__ == "__main__":
    main()
