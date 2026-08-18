#!/usr/bin/env python3
"""Merge the base chain (ai.draft.json) with the validated augmentation
(ai_aug.draft.json) into references/chains/ai_full.draft.json and concatenate
data/ai.validated.jsonl + data/ai_aug.validated.jsonl into
data/ai_full.validated.jsonl for gen_map.py.

Base companies win on code conflicts (they carry curated roles/leaders).
Aug-only segments are inserted after the last base segment of the same group
prefix (上游/中游/下游); "待定" goes last.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_draft(name: str) -> dict:
    return json.loads((ROOT / f"references/chains/{name}.draft.json").read_text(encoding="utf-8"))


def main() -> None:
    base = load_draft("ai")
    aug = load_draft("ai_aug")

    segments: list[dict] = []
    by_name: dict[str, dict] = {}
    seen: set[str] = set()
    for s in base["segments"]:
        seg = {"id": s["id"], "name": s["name"], "companies": list(s["companies"])}
        for c in seg["companies"]:
            seen.add(c["code"])
        segments.append(seg)
        by_name[seg["name"]] = seg

    for s in aug["segments"]:
        newcomers = [c for c in s["companies"] if c["code"] not in seen]
        for c in newcomers:
            seen.add(c["code"])
        if not newcomers:
            continue
        if s["name"] in by_name:
            by_name[s["name"]]["companies"].extend(newcomers)
            continue
        group = s["name"].split("·")[0]
        seg = {"id": f"aug-{s['name']}", "name": s["name"], "companies": newcomers}
        # insert after the last segment of the same group; 待定 -> tail
        idx = len(segments)
        if group != "待定":
            for i, cur in enumerate(segments):
                if cur["name"].split("·")[0] == group:
                    idx = i + 1
        segments.insert(idx, seg)
        by_name[s["name"]] = seg

    out = {
        "chain": "ai_full",
        "chain_name": "人工智能产业链（全量版）",
        "drafted": "2026-07-17",
        "segments": segments,
    }
    p = ROOT / "references/chains/ai_full.draft.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    recs: dict[str, dict] = {}
    for name in ("ai", "ai_aug"):
        fp = ROOT / f"data/{name}.validated.jsonl"
        for line in fp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                recs.setdefault(r["code"], r)
    vp = ROOT / "data/ai_full.validated.jsonl"
    with open(vp, "w", encoding="utf-8") as f:
        for r in recs.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    total = sum(len(s["companies"]) for s in segments)
    print(f"segments: {len(segments)}, companies: {total}, validated records: {len(recs)}")
    for s in segments:
        print(f"  {s['name']}: {len(s['companies'])}")


if __name__ == "__main__":
    main()
