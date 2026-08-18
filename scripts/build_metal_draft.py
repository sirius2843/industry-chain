#!/usr/bin/env python3
"""Build non-ferrous metals chain draft from Wind concept book + curated seeds.

Same methodology as build_robot_draft.py: concept hit_by priority for
auto-assignment; curated seed map for segment overrides, roles, leaders.
Codes never invented — seeds not in the concept book were resolved via Wind
(data/metal_seed_lookup.csv).

Output: references/chains/metal.draft.json
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "data/metal_wind_concepts.jsonl"
LOOKUP = ROOT / "data/metal_seed_lookup.csv"

SEGMENTS = [
    ("metal-copper", "工业金属·铜"),
    ("metal-alu", "工业金属·铝"),
    ("metal-pbzn", "工业金属·铅锌"),
    ("metal-tin-ni", "工业金属·锡与镍"),
    ("metal-gold", "贵金属·黄金"),
    ("metal-silver", "贵金属·白银"),
    ("metal-w-mo", "小金属·钨与钼"),
    ("metal-sb", "小金属·锑"),
    ("metal-ti", "小金属·钛与锆"),
    ("metal-other", "小金属·其他小金属"),
    ("metal-rare", "稀土磁材·稀土矿与分离"),
    ("metal-magnet", "稀土磁材·永磁材料"),
    ("metal-li", "能源金属·锂"),
    ("metal-co", "能源金属·钴"),
    ("metal-tbd", "待定·待甄别"),
]

# name -> (segment_id, role, leader)
SEEDS = {
    # 铜
    "紫金矿业": ("metal-copper", "铜金锂资源巨头，全球矿业龙头", True),
    "江西铜业": ("metal-copper", "国内最大阴极铜生产商", True),
    "铜陵有色": ("metal-copper", "铜冶炼+铜箔", False),
    "云南铜业": ("metal-copper", "中铝系铜平台", False),
    "西部矿业": ("metal-copper", "铜铅锌采选", False),
    "金诚信": ("metal-copper", "矿山工程建设与采矿运营", False),
    # 铝
    "中国铝业": ("metal-alu", "氧化铝/电解铝双龙头", True),
    "云铝股份": ("metal-alu", "绿色水电铝", False),
    "神火股份": ("metal-alu", "电解铝+煤炭", False),
    "南山铝业": ("metal-alu", "铝深加工一体化", False),
    "天山铝业": ("metal-alu", "电解铝+氧化铝", False),
    "明泰铝业": ("metal-alu", "铝板带箔加工", False),
    "鼎胜新材": ("metal-alu", "电池铝箔龙头", False),
    "中孚实业": ("metal-alu", "电解铝+铝加工", False),
    # 铅锌
    "中金岭南": ("metal-pbzn", "铅锌采选冶炼龙头", True),
    "驰宏锌锗": ("metal-pbzn", "铅锌锗综合采选", False),
    "株冶集团": ("metal-pbzn", "锌冶炼", False),
    # 锡与镍
    "锡业股份": ("metal-tin-ni", "全球锡业龙头", True),
    "兴业银锡": ("metal-tin-ni", "银锡采选", False),
    # 黄金
    "山东黄金": ("metal-gold", "国内黄金产量龙头", True),
    "中金黄金": ("metal-gold", "央企黄金平台", False),
    "赤峰黄金": ("metal-gold", "高成长金矿", False),
    "山金国际": ("metal-gold", "原银泰黄金，金银矿", False),
    "西部黄金": ("metal-gold", "新疆黄金采选", False),
    "四川黄金": ("metal-gold", "梭罗沟金矿", False),
    # 白银
    "盛达资源": ("metal-silver", "白银采选龙头", True),
    "白银有色": ("metal-silver", "铜铅锌银综合冶炼", False),
    # 钨与钼
    "厦门钨业": ("metal-w-mo", "钨全产业链+稀土+磁材", True),
    "中钨高新": ("metal-w-mo", "硬质合金龙头", False),
    "章源钨业": ("metal-w-mo", "钨采选冶", False),
    "翔鹭钨业": ("metal-w-mo", "钨制品", False),
    "金钼股份": ("metal-w-mo", "钼采选冶龙头", True),
    # 锑
    "湖南黄金": ("metal-sb", "锑+黄金，锑品龙头", True),
    "华钰矿业": ("metal-sb", "锑金矿", False),
    # 钛与锆
    "宝钛股份": ("metal-ti", "钛材龙头，军工航空", True),
    "西部超导": ("metal-ti", "钛合金+高温合金+超导线材", False),
    "西部材料": ("metal-ti", "钛及稀有金属加工", False),
    "龙佰集团": ("metal-ti", "钛白粉龙头+海绵钛", False),
    "钛能化学": ("metal-ti", "原中核钛白，钛白粉", False),
    "东方锆业": ("metal-ti", "锆制品", False),
    "三祥新材": ("metal-ti", "锆系材料+镁合金", False),
    # 稀土
    "北方稀土": ("metal-rare", "轻稀土龙头，资源配额第一", True),
    "中国稀土": ("metal-rare", "中重稀土整合平台", False),
    "中稀有色": ("metal-rare", "原广晟有色，中重稀土", False),
    "盛和资源": ("metal-rare", "稀土冶炼分离+海外矿", False),
    "包钢股份": ("metal-rare", "稀土精矿资源", False),
    # 永磁
    "金力永磁": ("metal-magnet", "高性能钕铁硼，新能源车/机器人", True),
    "中科三环": ("metal-magnet", "钕铁硼老牌", False),
    "正海磁材": ("metal-magnet", "高性能钕铁硼", False),
    "宁波韵升": ("metal-magnet", "钕铁硼+伺服", False),
    "大地熊": ("metal-magnet", "烧结钕铁硼", False),
    "英洛华": ("metal-magnet", "磁材+电机", False),
    "银河磁体": ("metal-magnet", "粘结钕铁硼", False),
    # 锂
    "赣锋锂业": ("metal-li", "锂盐+锂矿+电池一体化", True),
    "天齐锂业": ("metal-li", "锂辉石资源龙头", True),
    "盐湖股份": ("metal-li", "盐湖提锂+钾肥", False),
    "永兴材料": ("metal-li", "云母提锂+特钢", False),
    "中矿资源": ("metal-li", "锂铯铷资源", False),
    "藏格矿业": ("metal-li", "盐湖提锂+钾铜", False),
    "江特电机": ("metal-li", "云母提锂+电机", False),
    "融捷股份": ("metal-li", "锂辉石采选", False),
    "天华新能": ("metal-li", "锂盐加工", False),
    "雅化集团": ("metal-li", "锂盐+民爆", False),
    # 钴
    "华友钴业": ("metal-co", "钴镍冶炼+前驱体一体化", True),
    "洛阳钼业": ("metal-co", "铜钴矿+钼铌，全球矿业巨头", False),
    "格林美": ("metal-co", "钴镍回收+前驱体", False),
    "寒锐钴业": ("metal-co", "钴粉", False),
    "腾远钴业": ("metal-co", "钴盐", False),
}

# auto-assignment priority by concept hit
PRIORITY = [
    ({"锑"}, "metal-sb"),
    ({"钨"}, "metal-w-mo"),
    ({"钛"}, "metal-ti"),
    ({"稀土"}, "metal-rare"),
    ({"稀土永磁"}, "metal-magnet"),
    ({"锂", "锂矿", "盐湖提锂"}, "metal-li"),
    ({"钴"}, "metal-co"),
    ({"铜"}, "metal-copper"),
    ({"铝"}, "metal-alu"),
    ({"铅锌"}, "metal-pbzn"),
    ({"镍"}, "metal-tin-ni"),
    ({"黄金"}, "metal-gold"),
    ({"白银有色"}, "metal-silver"),
    ({"小金属"}, "metal-other"),
]


def main() -> None:
    book: dict[str, dict] = {}
    for line in BOOK.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            book[r["name"]] = r
    for row in csv.DictReader(open(LOOKUP, encoding="utf-8")):
        name = row["证券简称"].strip()
        if name not in book:
            book[name] = {"code": row["Wind代码"].strip(), "name": name,
                          "concepts": [], "hit_by": ["手工补入"]}

    seg_cos: dict[str, list[dict]] = {sid: [] for sid, _ in SEGMENTS}
    assigned: set[str] = set()
    for name, (sid, role, leader) in SEEDS.items():
        r = book.get(name)
        if not r:
            print(f"WARN seed {name} not found anywhere, skipped")
            continue
        seg_cos[sid].append({"code": r["code"], "name": name, "leader": leader,
                             "role": role, "concepts": r.get("concepts") or r.get("hit_by")})
        assigned.add(name)
    for name, r in book.items():
        if name in assigned:
            continue
        hits = set(r.get("hit_by", []))
        sid = "metal-tbd"
        for cond, target in PRIORITY:
            if hits & cond:
                sid = target
                break
        seg_cos[sid].append({"code": r["code"], "name": name, "leader": False,
                             "role": "", "concepts": r.get("hit_by")})
        assigned.add(name)

    segments = [{"id": sid, "name": sname, "companies": seg_cos[sid]}
                for sid, sname in SEGMENTS if seg_cos[sid]]
    draft = {"chain": "metal", "chain_name": "有色金属产业链（全量版）",
             "drafted": "2026-08-18", "segments": segments}
    out = ROOT / "references/chains/metal.draft.json"
    out.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(s["companies"]) for s in segments)
    print(f"draft -> {out} ({total} companies)")
    for s in segments:
        n_ld = sum(1 for c in s["companies"] if c["leader"])
        print(f'  {s["id"]:16s} {s["name"]:18s} {len(s["companies"]):3d}家 龙头{n_ld}')


if __name__ == "__main__":
    main()
