#!/usr/bin/env python3
"""Second-pass metal draft cleanup (2026-08-18).

First pass (filter_metal_draft.py) removed concept-board noise by keyword; the
dashboard leader step then surfaced remaining cross-industry companies whose
float mcap stole segment leadership (中国人保/阳光电源/宁德时代...).

This pass applies the strict rule: 主营必须以该金属的采选/冶炼/加工为核心；
纯下游应用（电池/电池材料/光伏设备/电子/建材/金融/珠宝零售等）剔除。
Also fixes a few misfiled companies by moving them to the right segment.
Idempotent: safe to re-run.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFT = ROOT / "references" / "chains" / "metal.draft.json"

# code -> remove entirely from the chain
REMOVE = {
    # copper: 矿山服务/电子/PCB/线缆/地产贸易
    "603979.SH", "688668.SH", "688655.SH", "603002.SH", "688519.SH",
    "300548.SZ", "600173.SH", "601869.SH", "300852.SZ", "603328.SH",
    "688020.SH", "300563.SZ", "002902.SZ", "300115.SZ",
    # alu: 陶瓷/PCB/碳材料/工程承包/压铸件
    "003031.SZ", "300328.SZ", "300903.SZ", "600353.SH", "688598.SH",
    "301611.SZ", "300285.SZ", "601068.SH",
    # gold: 珠宝零售
    "002574.SZ", "603900.SH", "002867.SZ", "300945.SZ", "002731.SZ",
    # silver: 金融/水泥/玻璃/建材/地产
    "600641.SH", "601319.SH", "601229.SH", "000877.SZ", "601636.SH",
    "601865.SH", "000786.SZ",
    # w-mo: 电子化学品/特气/氟材料
    "300346.SZ", "688146.SH", "688549.SH", "600378.SH",
    # sb: 碳素/锌/铝合金/衡器/超硬材料/硫氯化工等
    "600516.SH", "600331.SH", "002114.SZ", "002237.SZ", "300489.SZ",
    "300720.SZ", "600172.SH", "600206.SH", "301118.SZ",
    # ti: 光伏设备/线缆/氯碱/磷肥
    "300252.SZ", "002386.SZ", "300724.SZ", "002056.SZ", "300274.SZ",
    "300776.SZ", "600727.SH",
    # other: 装备/硅铁
    "600397.SH", "600295.SH",
    # rare: 工程/设备/软磁/电机/杂项材料
    "000758.SZ", "002645.SZ", "600330.SH", "000969.SZ", "600980.SH",
    "300811.SZ", "002249.SZ",
    # li: 电池厂/电池材料/设备/杂项
    "002141.SZ", "688388.SH", "601969.SH", "603978.SH", "000688.SZ",
    "600478.SH", "002594.SZ", "300068.SZ", "300750.SZ", "603906.SH",
    "300655.SZ", "301210.SZ", "688529.SH", "600869.SH", "601515.SH",
    "688779.SH", "920239.BJ", "002108.SZ", "300647.SZ", "300619.SZ",
    "002326.SZ", "688573.SH", "300477.SZ", "002125.SZ", "300432.SZ",
    "002741.SZ", "688559.SH", "601311.SH", "600152.SH", "300631.SZ",
    "600773.SH",
    # li: 电池材料/电池（主营含"锂"但属电池链，非能源金属）
    "002080.SZ", "688148.SH", "600884.SH", "600110.SH", "920185.BJ",
    "688275.SH", "301238.SZ", "300080.SZ", "002805.SZ", "300769.SZ",
    "603026.SH", "301358.SZ", "688005.SH", "688567.SH", "002733.SZ",
    "300890.SZ", "920523.BJ", "688707.SH", "000049.SZ", "300409.SZ",
    "688499.SH", "603196.SH", "001301.SZ", "300457.SZ", "002850.SZ",
    "688353.SH", "300919.SZ", "002045.SZ", "300173.SZ", "301487.SZ",
    "300035.SZ", "300438.SZ", "301292.SZ", "688155.SH", "000695.SZ",
    "300014.SZ", "001283.SZ", "002759.SZ",
    # co: 工程承包为主
    "601618.SH",
}

# code -> target segment id (move, keeping role text)
MOVE = {
    "002182.SZ": "metal-other",   # 宝武镁业：镁为主，铝→其他小金属
    "002428.SZ": "metal-other",   # 云南锗业：锗，锑→其他小金属
    "001257.SZ": "metal-w-mo",    # 盛龙股份：钼，其他→钨与钼
    "920068.BJ": "metal-ti",      # 天工股份：钛合金，其他→钛与锆
    "600459.SH": "metal-tbd",     # 贵研铂业：铂族金属，无对应环节→待定
    "002057.SZ": "metal-magnet",  # 中钢天源：磁性材料，稀土→永磁
    "300835.SZ": "metal-magnet",  # 龙磁科技：永磁铁氧体，稀土→永磁
    "301141.SZ": "metal-magnet",  # 中科磁业：永磁材料，稀土→永磁
    "002240.SZ": "metal-li",      # 盛新锂能：锂盐，稀土→锂
    "600301.SH": "metal-tin-ni",  # 华锡有色：锡为主，锑→锡与镍
    "002716.SZ": "metal-silver",  # 湖南白银：白银冶炼，锑→白银
}


def main() -> None:
    d = json.loads(DRAFT.read_text(encoding="utf-8"))
    segs = d["segments"] if isinstance(d, dict) and "segments" in d else d
    by_id = {s["id"]: s for s in segs}
    removed, moved = [], []
    for s in segs:
        keep = []
        for c in s["companies"]:
            code = c["code"]
            if code in REMOVE:
                removed.append((code, c["name"], s["id"]))
                continue
            tgt = MOVE.get(code)
            if tgt and tgt != s["id"]:
                by_id[tgt]["companies"].append(c)
                moved.append((code, c["name"], s["id"], tgt))
                continue
            keep.append(c)
        s["companies"] = keep
    total = sum(len(s["companies"]) for s in segs)
    print(f"removed {len(removed)}, moved {len(moved)}, total now {total}")
    for sid in [s["id"] for s in segs]:
        print(f"  {sid}: {len(by_id[sid]['companies'])}")
    DRAFT.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print("draft updated ->", DRAFT)


if __name__ == "__main__":
    main()
