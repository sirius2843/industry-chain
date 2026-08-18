#!/usr/bin/env python3
"""Filter metals chain draft: remove concept-pollution companies.

Same rule as filter_robot_draft.py, metal-tuned keywords. Note: bare 金/银
NOT used as keywords (金融/银行 false positives) — use 黄金/白银/金矿/银矿.
Keep rule:
  1. curated seeds (build_metal_draft.SEEDS) always kept;
  2. non-seed kept if iFinD 主营业务/主营产品 matches metal keywords;
  3. or hit by >= 2 specific boards (白银有色/有色金属 不计入 specific).
"""
from __future__ import annotations

import json
from pathlib import Path

from build_metal_draft import SEEDS

ROOT = Path(__file__).resolve().parent.parent
DRAFT = ROOT / "references/chains/metal.draft.json"
VALIDATED = ROOT / "data/metal.validated.jsonl"
BOOK = ROOT / "data/metal_wind_concepts.jsonl"

KEYWORDS = [
    "铜", "铝", "铅", "锌", "锡", "镍", "钴", "锂", "钨", "钼", "锑", "钛",
    "锆", "稀土", "磁", "矿", "冶炼", "金属", "合金", "电解", "采选", "精矿",
    "黄金", "白银", "金银", "镓", "锗", "铟", "镁", "钽", "铌", "钒", "铂",
    "钯", "铍", "钇", "锶", "锰", "铬", "氧化铝", "炭素",
]
SPECIFIC = {"铜", "铝", "铅锌", "镍", "黄金", "钨", "锑", "钛", "稀土",
            "稀土永磁", "锂", "锂矿", "盐湖提锂", "钴", "小金属"}
SEED_NAMES = set(SEEDS)


def main() -> None:
    draft = json.loads(DRAFT.read_text(encoding="utf-8"))
    recs = {}
    for line in VALIDATED.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r["code"]] = r
    book = {}
    for line in BOOK.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            book[r["code"]] = r

    removed: list[tuple[str, str, str]] = []
    for s in draft["segments"]:
        kept = []
        for c in s["companies"]:
            if c["name"] in SEED_NAMES:
                kept.append(c)
                continue
            r = recs.get(c["code"], {})
            text = (r.get("main_business") or "") + (r.get("main_products") or "")
            hits = set(book.get(c["code"], {}).get("hit_by", []))
            if any(k in text for k in KEYWORDS) or len(hits & SPECIFIC) >= 2:
                kept.append(c)
            else:
                removed.append((s["id"], c["name"], c["code"]))
        s["companies"] = kept

    DRAFT.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(s["companies"]) for s in draft["segments"])
    print(f"removed {len(removed)} companies; draft total now {total}")
    from collections import Counter
    cnt = Counter(sid for sid, _, _ in removed)
    print("removed by segment:", dict(cnt))
    for sid, name, code in removed[:60]:
        print(f"  - [{sid}] {name} {code}")
    if len(removed) > 60:
        print(f"  ... 共 {len(removed)} 家")


if __name__ == "__main__":
    main()
