#!/usr/bin/env python3
"""Build robot chain draft from Wind concept book + curated seeds.

Data-driven assignment: concept hit_by priority; curated seed map for
segment overrides, roles and leader flags. Codes never invented — seeds not
in the concept book were resolved via Wind (data/robot_seed_lookup.csv).

Output: references/chains/robot.draft.json
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "data/robot_wind_concepts.jsonl"
LOOKUP = ROOT / "data/robot_seed_lookup.csv"

SEGMENTS = [
    ("robot-reducer", "上游·减速器"),
    ("robot-screw", "上游·丝杠与导轨"),
    ("robot-motor", "上游·伺服与电机"),
    ("robot-sensor", "上游·传感器与机器视觉"),
    ("robot-material", "上游·材料与结构件"),
    ("robot-joint", "中游·关节模组与执行器"),
    ("robot-body", "中游·人形机器人本体"),
    ("robot-industrial", "中游·工业机器人与集成"),
    ("robot-ai", "中游·控制与具身智能"),
    ("robot-app", "下游·服务与特种机器人"),
    ("robot-tbd", "待定·待甄别"),
]

# name -> (segment_id, role, leader)
SEEDS = {
    # 减速器
    "绿的谐波": ("robot-reducer", "谐波减速器龙头，人形机器人核心标的", True),
    "双环传动": ("robot-reducer", "齿轮龙头，RV/行星减速器+执行器布局", True),
    # 丝杠与导轨
    "五洲新春": ("robot-screw", "行星滚柱丝杠+轴承，丝杠国产化核心", True),
    "北特科技": ("robot-screw", "行星滚柱丝杠+转向器零部件", False),
    "贝斯特": ("robot-screw", "精密零部件，滚珠丝杠副布局", False),
    "恒立液压": ("robot-screw", "液压龙头，行星滚柱丝杠电动缸延伸", False),
    "长盛轴承": ("robot-screw", "自润滑轴承，丝杠/关节配套", False),
    "斯菱智驱": ("robot-screw", "汽车轴承单元，谐波减速器+丝杠布局", False),
    "秦川机床": ("robot-screw", "机床老牌，RV减速器+丝杠导轨", False),
    # 伺服与电机
    "汇川技术": ("robot-motor", "工控与伺服龙头，机器人电控/伺服一体化", True),
    "鸣志电器": ("robot-motor", "步进/空心杯电机，人形机器人手部电机主线", True),
    "步科股份": ("robot-motor", "伺服系统与人机界面", False),
    "雷赛智能": ("robot-motor", "运动控制+步进/伺服", False),
    "禾川科技": ("robot-motor", "伺服系统国产新锐", False),
    "伟创电气": ("robot-motor", "变频器/伺服，机器人关节电机布局", False),
    "信捷电气": ("robot-motor", "小型PLC+伺服", False),
    "江苏雷利": ("robot-motor", "微特电机，线性执行器/空心杯布局", False),
    "昊志机电": ("robot-motor", "电主轴，谐波减速器+关节模组布局", False),
    "卧龙电驱": ("robot-motor", "工业电机龙头，机器人关节电机", False),
    # 传感器与机器视觉
    "柯力传感": ("robot-sensor", "称重传感器龙头，六维力传感器主线", True),
    "奥比中光-W": ("robot-sensor", "3D视觉传感器龙头，机器人视觉方案", True),
    "汉威科技": ("robot-sensor", "气体传感器，柔性触觉传感器布局", False),
    "东华测试": ("robot-sensor", "结构力学测试，六维力传感器", False),
    "安培龙": ("robot-sensor", "力矩/温度传感器", False),
    "凌云光": ("robot-sensor", "机器视觉龙头", False),
    "奥普特": ("robot-sensor", "机器视觉光源/镜头/系统", False),
    "矩子科技": ("robot-sensor", "机器视觉检测设备", False),
    "天准科技": ("robot-sensor", "机器视觉+智能制造装备", False),
    # 材料与结构件
    "中研股份": ("robot-material", "PEEK材料龙头，人形机器人轻量化主线", True),
    "肇民科技": ("robot-material", "精密注塑，PEEK结构件", False),
    "沃特股份": ("robot-material", "特种高分子材料，PEEK/液晶聚合物", False),
    "凯盛新材": ("robot-material", "PEKK/芳纶单体", False),
    # 关节模组与执行器
    "三花智控": ("robot-joint", "热管理龙头，机器人机电执行器总成（T链核心）", True),
    "拓普集团": ("robot-joint", "汽车零部件平台，机器人执行器/直线模组（T链核心）", True),
    "中大力德": ("robot-joint", "减速器+伺服+驱动一体关节模组", False),
    # 人形机器人本体
    "机器人": ("robot-body", "新松机器人，中科院系本体老牌", True),
    "天奇股份": ("robot-body", "汽车装备，与优必选合作人形机器人", False),
    "博实股份": ("robot-body", "石化后处理装备，人形机器人本体合作", False),
    "均普智能": ("robot-body", "智能制造装备，人形机器人本体与产线", False),
    # 工业机器人与集成
    "埃斯顿": ("robot-industrial", "国产工业机器人本体龙头", True),
    "埃夫特-U": ("robot-industrial", "国产工业机器人本体，奇瑞系", False),
    "新时达": ("robot-industrial", "机器人本体+运动控制", False),
    "克来机电": ("robot-industrial", "柔性自动化装备集成", False),
    "瑞松科技": ("robot-industrial", "焊装机器人系统集成", False),
    # 控制与具身智能
    "固高科技": ("robot-ai", "运动控制器龙头", True),
    "中科创达": ("robot-ai", "智能操作系统，机器人软件平台", False),
    "科大讯飞": ("robot-ai", "星火大模型+具身智能交互", False),
    "虹软科技": ("robot-ai", "视觉AI算法", False),
    # 服务与特种机器人
    "九号公司-WD": ("robot-app", "短交通/配送/割草机器人平台", True),
    "石头科技": ("robot-app", "扫地机器人龙头", False),
    "科沃斯": ("robot-app", "家用服务机器人龙头", False),
    "天智航-U": ("robot-app", "骨科手术机器人", False),
    "申昊科技": ("robot-app", "电力巡检机器人", False),
    "景业智能": ("robot-app", "核工业特种机器人", False),
    "亿嘉和": ("robot-app", "电力巡检/带电作业机器人", False),
}

# auto-assignment priority by concept hit
PRIORITY = [
    ({"减速器"}, "robot-reducer"),
    ({"PEEK材料"}, "robot-material"),
    ({"传感器", "机器视觉"}, "robot-sensor"),
    ({"机器人关节"}, "robot-joint"),
    ({"人形机器人"}, "robot-body"),
    ({"工业机器人"}, "robot-industrial"),
    ({"具身智能"}, "robot-ai"),
]


def main() -> None:
    book: dict[str, dict] = {}
    for line in BOOK.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            book[r["name"]] = r
    # seed codes resolved via Wind (not in concept book)
    for row in csv.DictReader(open(LOOKUP, encoding="utf-8")):
        name = row["证券简称"].strip()
        if name not in book:
            book[name] = {"code": row["Wind代码"].strip(), "name": name,
                          "concepts": [], "hit_by": ["手工补入"]}

    seg_cos: dict[str, list[dict]] = {sid: [] for sid, _ in SEGMENTS}
    assigned: set[str] = set()
    # 1) seeds first
    for name, (sid, role, leader) in SEEDS.items():
        r = book.get(name)
        if not r:
            print(f"WARN seed {name} not found anywhere, skipped")
            continue
        seg_cos[sid].append({"code": r["code"], "name": name, "leader": leader,
                             "role": role, "concepts": r.get("concepts") or r.get("hit_by")})
        assigned.add(name)
    # 2) auto-assign the rest by concept priority
    for name, r in book.items():
        if name in assigned:
            continue
        hits = set(r.get("hit_by", []))
        sid = "robot-tbd"
        for cond, target in PRIORITY:
            if hits & cond:
                sid = target
                break
        seg_cos[sid].append({"code": r["code"], "name": name, "leader": False,
                             "role": "", "concepts": r.get("hit_by")})
        assigned.add(name)

    segments = [{"id": sid, "name": sname, "companies": seg_cos[sid]}
                for sid, sname in SEGMENTS if seg_cos[sid]]
    draft = {"chain": "robot", "chain_name": "机器人产业链（全量版）",
             "drafted": "2026-08-18", "segments": segments}
    out = ROOT / "references/chains/robot.draft.json"
    out.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(s["companies"]) for s in segments)
    print(f"draft -> {out} ({total} companies)")
    for s in segments:
        n_ld = sum(1 for c in s["companies"] if c["leader"])
        print(f'  {s["id"]:20s} {s["name"]:16s} {len(s["companies"]):3d}家 龙头{n_ld}')


if __name__ == "__main__":
    main()
