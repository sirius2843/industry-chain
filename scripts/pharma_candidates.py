#!/usr/bin/env python3
"""Build the pharma augmentation candidate draft from the Wind concept book.

Selects companies hitting >=1 core pharma concept, assigns a proposed segment
by concept priority, and writes references/chains/pharma_aug.draft.json for
ifind_batch.py validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# theme concepts: not sufficient on their own to enter the chain
BROAD = {"流感", "干细胞", "精准医疗"}

# concept -> proposed segment, priority order (first match wins)
RULES: list[tuple[str, set[str]]] = [
    ("医疗服务·CXO(研发/生产外包)", {"CRO"}),
    ("医药商业·医药流通", {"医药流通", "医药商业"}),
    ("医药商业·零售药店", {"医药电商"}),
    ("医疗器械·IVD与低值耗材", {"体外诊断"}),
    ("医疗器械·医疗设备", {"医疗器械"}),
    ("创新药·生物制品(疫苗/血制品/生长激素)", {"疫苗", "血制品"}),
    ("创新药·创新药(Biotech/License-out)", {"单克隆抗体", "CAR-T疗法", "创新药", "减肥药"}),
    ("制药·化学制剂", {"化学制药", "仿制药", "独家药"}),
    ("制药·原料药与中间体", {"肝素钠", "维生素", "抗生素"}),
    ("中药·品牌中药", {"中药"}),
    ("医疗服务·专科医疗与医美", {"医美", "眼科医疗", "口腔医疗", "民营医院", "辅助生殖"}),
    ("医疗服务·ICL与诊断服务", {"基因检测"}),
]
FALLBACK = "待定·医药主题概念"


def main() -> None:
    book: dict[str, dict] = {}
    for line in (ROOT / "data/pharma_wind_concepts.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            book[r["code"]] = r
    draft = json.loads((ROOT / "references/chains/pharma.draft.json").read_text(encoding="utf-8"))
    base = {c["code"] for s in draft["segments"] for c in s["companies"]}

    def core_hits(r: dict) -> list[str]:
        return [h for h in r.get("hit_by", []) if h not in BROAD]

    picked: dict[str, dict] = {}
    for r in book.values():
        if r["code"] in base:
            continue
        if len(core_hits(r)) >= 1:
            picked[r["code"]] = r

    segs: dict[str, list[dict]] = {}
    for r in picked.values():
        hits = set(r.get("hit_by", []))
        seg = None
        for name, keys in RULES:
            if hits & keys:
                seg = name
                break
        if not seg:
            seg = FALLBACK
        segs.setdefault(seg, []).append({
            "code": r["code"], "name": r["name"], "leader": False,
            "role": "", "concepts": sorted(hits),
        })

    out = {
        "chain": "pharma_aug",
        "chain_name": "医药产业链补库候选",
        "drafted": "2026-07-21",
        "segments": [
            {"id": seg, "name": seg,
             "companies": sorted(cos, key=lambda c: c["code"])}
            for seg, cos in sorted(segs.items())
        ],
    }
    p = ROOT / "references/chains/pharma_aug.draft.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(s["companies"]) for s in out["segments"])
    print(f"candidates: {total}")
    for s in out["segments"]:
        print(f"  {s['name']}: {len(s['companies'])}")


if __name__ == "__main__":
    main()
