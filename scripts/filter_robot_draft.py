#!/usr/bin/env python3
"""Filter robot chain draft: remove concept-pollution companies.

Keep rule (evidence-based, codes/data from iFinD validation + Wind hits only):
  1. curated seeds (build_robot_draft.SEEDS) always kept;
  2. non-seed kept if iFinD 主营业务/主营产品 matches robot-related keywords;
  3. or hit by >= 2 specific concept boards (泛板块不计).

Removed companies are reported per segment. Re-run build_robot_draft.py first
if seeds change.
"""
from __future__ import annotations

import json
from pathlib import Path

from build_robot_draft import SEEDS

ROOT = Path(__file__).resolve().parent.parent
DRAFT = ROOT / "references/chains/robot.draft.json"
VALIDATED = ROOT / "data/robot.validated.jsonl"
BOOK = ROOT / "data/robot_wind_concepts.jsonl"

KEYWORDS = [
    "机器人", "减速器", "丝杠", "导轨", "伺服", "电机", "执行器", "关节",
    "传感器", "机器视觉", "视觉", "PEEK", "聚醚醚酮", "自动化", "智能装备",
    "智能制造", "数控", "机床", "运动控制", "控制器", "驱动器", "轴承",
    "液压", "电动缸", "机械臂", "具身", "灵巧手", "编码器", "力矩",
    "空心杯", "步进", "变频", "PLC", "工控", "齿轮", "传动", "无人驾驶",
]
SPECIFIC = {"人形机器人", "工业机器人", "具身智能", "机器人关节",
            "减速器", "传感器", "机器视觉", "PEEK材料"}
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
    for sid, name, code in removed:
        print(f"  - [{sid}] {name} {code}")


if __name__ == "__main__":
    main()
