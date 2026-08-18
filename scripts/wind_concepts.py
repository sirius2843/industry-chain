#!/usr/bin/env python3
"""Harvest Wind concept-board memberships for the industry chain.

Calls wind_search_stocks via wind_tool.py (Python channel — prints the full
payload that cli.mjs truncates), extracts per-company rows from the text
(each row: [windcode, name, full_concept_string]), and accumulates a
company -> concepts map in data/wind_concepts.jsonl.

Usage:
  python3 wind_concepts.py --concepts 算力 AI芯片 CPO 液冷 --out-dir data
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

WIND_DIR = Path(
    "/Users/sirius/Library/Application Support/kimi-desktop/daimon-share/"
    "daimon/runtime/kimi-code/home/plugins/managed/wind-allskill/skills/wind-mcp-skill"
)
WIND_TOOL = WIND_DIR / "scripts" / "wind_tool.py"
ROW_RE = re.compile(r"\['([0-9A-Z]{4,9}\.(?:SH|SZ|BJ))',\s*'([^']{1,40})'(?:,\s*'([^']*)')?")
COUNT_RE = re.compile(r"'excelTotalCount':\s*(\d+)")


def probe(concept: str, out_dir: Path) -> tuple[list[dict], int]:
    csv_path = out_dir / f"wind_concept_{concept}.csv"
    params = json.dumps(
        {"question": f"筛选属于{concept}概念板块的股票", "file_path": str(csv_path)},
        ensure_ascii=False,
    )
    if not csv_path.exists():  # skip the API call if we already have the CSV
        cmd = [
            sys.executable, str(WIND_TOOL), "call",
            "--api-name", "wind_search_stocks",
            "--params-json", params,
        ]
        proc = subprocess.run(cmd, cwd=str(WIND_DIR), capture_output=True, text=True, timeout=180)
        out = (proc.stdout or "") + (proc.stderr or "")
    else:
        out = ""
    rows = []
    # primary source: the CSV the tool writes via file_path (full rows, no truncation)
    if csv_path.exists():
        import csv as _csv
        with open(csv_path, encoding="utf-8-sig") as f:
            for rec in _csv.DictReader(f):
                code = (rec.get("Wind代码") or "").strip()
                name = (rec.get("证券简称") or "").strip()
                concepts = (rec.get("所属概念板块") or "").strip()
                if code:
                    rows.append({"code": code, "name": name,
                                 "concepts": [c for c in concepts.split(";") if c]})
        return rows, len(rows)
    # fallback: legacy list-format rows in stdout
    for code, name, concepts in ROW_RE.findall(out):
        rows.append({"code": code, "name": name,
                     "concepts": [c for c in concepts.split(";") if c]})
    m = COUNT_RE.search(out)
    total = int(m.group(1)) if m else -1
    return rows, total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concepts", nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--jsonl", default=None)
    args = ap.parse_args()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = Path(args.jsonl) if args.jsonl else out_dir / "wind_concepts.jsonl"

    book: dict[str, dict] = {}
    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                book[r["code"]] = r

    for concept in args.concepts:
        rows, total = probe(concept, out_dir)
        new = 0
        for r in rows:
            cur = book.setdefault(r["code"], {"code": r["code"], "name": r["name"],
                                              "concepts": [], "hit_by": []})
            for c in r["concepts"]:
                if c not in cur["concepts"]:
                    cur["concepts"].append(c)
            if concept not in cur["hit_by"]:
                cur["hit_by"].append(concept)
            if not r.get("_seen"):
                new += 1
                r["_seen"] = True
        print(f"[{concept}] total={total} parsed={len(rows)} (+{new} new)")

    with open(jsonl, "w", encoding="utf-8") as f:
        for r in book.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"concept book -> {jsonl} ({len(book)} companies)")


if __name__ == "__main__":
    main()
