#!/usr/bin/env python3
"""Build the augmentation candidate draft from the Wind concept book.

Selects companies hitting >=2 core concepts (plus explicit audit picks),
assigns a proposed segment by concept priority, and writes
references/chains/ai_aug.draft.json for ifind_batch.py validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROAD = {"人工智能", "AI应用", "云计算", "数据要素", "AI手机", "智能驾驶", "机器视觉"}

# concept -> proposed segment, priority order (first match wins)
RULES: list[tuple[str, set[str]]] = [
    ("上游·存储与接口芯片", {"HBM", "存储芯片"}),
    ("上游·先进封装", {"先进封装"}),
    ("上游·半导体设备", {"半导体设备"}),
    ("上游·半导体材料", {"半导体材料"}),
    ("上游·EDA与IP", {"EDA"}),
    ("上游·光模块/器件/光芯片", {"CPO", "光芯片", "光模块", "光通信"}),
    ("上游·连接器与高速铜连接", {"高速铜连接", "铜缆高速连接"}),
    ("上游·PCB与覆铜板", {"PCB", "覆铜板"}),
    ("上游·温控液冷与供配电", {"液冷"}),
    ("上游·AI芯片与SoC", {"AI芯片", "算力芯片", "GPU"}),
    ("上游·AI服务器与整机", {"服务器", "英伟达产业链"}),
    ("中游·IDC与算力服务", {"IDC", "数据中心", "东数西算", "算力租赁", "边缘计算"}),
    ("中游·大模型与算法", {"大模型", "Sora", "多模态AI"}),
    ("下游·医疗AI", {"AI医疗"}),
    ("下游·智能驾驶", {"智能驾驶"}),
    ("下游·安防与视觉物联", {"机器视觉"}),
    ("下游·智能终端", {"AI手机", "AIPC"}),
    ("下游·办公与内容创作", {"AI应用", "人工智能", "AIGC", "ChatGPT"}),
]
FALLBACK = "待定·算力泛概念"

# manual overrides after domain review
OVERRIDE = {
    "000063.SZ": "上游·AI服务器与整机",      # 中兴通讯：通信设备/服务器/算力
    "000066.SZ": "上游·AI服务器与整机",      # 中国长城：信创整机
    "002179.SZ": "上游·连接器与高速铜连接",  # 中航光电：连接器龙头
    "002475.SZ": "上游·连接器与高速铜连接",  # 立讯精密：连接器/整机
    "300166.SZ": "中游·IDC与算力服务",       # 东方国信：大数据+算力服务
    "300454.SZ": "中游·IDC与算力服务",       # 深信服：云计算/安全
    "300249.SZ": "上游·温控液冷与供配电",    # 依米康：机房温控
    "600156.SH": "上游·温控液冷与供配电",    # 华升股份：液冷（主题纯度待验）
}
# audit picks allowed in with <2 core hits
AUDIT_PICKS = {"002130.SZ", "300563.SZ", "002993.SZ", "603773.SH", "301191.SZ"}


def main() -> None:
    book: dict[str, dict] = {}
    for line in (ROOT / "data/wind_concepts.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            book[r["code"]] = r
    draft = json.loads((ROOT / "references/chains/ai.draft.json").read_text(encoding="utf-8"))
    base = {c["code"] for s in draft["segments"] for c in s["companies"]}

    def core_hits(r: dict) -> list[str]:
        return [h for h in r.get("hit_by", []) if h not in BROAD]

    picked: dict[str, dict] = {}
    for r in book.values():
        if r["code"] in base:
            continue
        if len(core_hits(r)) >= 1 or r["code"] in AUDIT_PICKS:
            picked[r["code"]] = r
    # audit picks not present in the concept book (my nomination, codes pre-validated by iFinD name check later)
    extra = {
        "603773.SH": "沃格光电",
        "301191.SZ": "菲菱科思",
    }
    for code, name in extra.items():
        if code not in base and code not in picked:
            picked[code] = {"code": code, "name": name, "concepts": [], "hit_by": ["自查提名"]}

    segs: dict[str, list[dict]] = {}
    for r in picked.values():
        hits = set(r.get("hit_by", []))
        seg = OVERRIDE.get(r["code"])
        if not seg:
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
        "chain": "ai_aug",
        "chain_name": "AI产业链补库候选",
        "drafted": "2026-07-17",
        "segments": [
            {"id": seg, "name": seg,
             "companies": sorted(cos, key=lambda c: c["code"])}
            for seg, cos in sorted(segs.items())
        ],
    }
    p = ROOT / "references/chains/ai_aug.draft.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(s["companies"]) for s in out["segments"])
    print(f"candidates: {total}")
    for s in out["segments"]:
        print(f"  {s['name']}: {len(s['companies'])}")


if __name__ == "__main__":
    main()
