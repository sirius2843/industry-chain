---
name: industry-chain
description: "产业链知识库与取数工作流。用于回答或构建产业链（供应链/上下游/环节）相关问题：梳理某产业链上中下游环节、各环节代表公司及股票代码、环节龙头、产业链公司对比、验证公司是否属于某环节。覆盖重点产业链（首批：人工智能产业链），数据只从 Wind 万得与 iFinD 同花顺插件拉取，不使用网络来源。触发词示例：'XX产业链上下游有哪些公司'、'梳理一下XX产业链'、'XX环节龙头是谁'、'这家公司属于AI产业链哪个环节'、'对比一下产业链各环节'。"
---

# 产业链（industry-chain）

产业链 = 半静态骨架（本知识库）+ 活数据（Wind/iFinD 现查）。

## 数据铁律

1. 公司、财务、行情数据只来自 Wind 万得与 iFinD 同花顺插件（均经 agent-gw 网关），禁止网络搜索兜底、禁止凭记忆杜撰代码或数字。
2. 引用知识库内容时给出来源与日期；行情/估值/最新财务必须当次现查并标注交易日/报告期。
3. 数据源报错（权限、超时、参数错误）按失败处理并如实说明，不得当作"无数据"。

## 知识库

`references/chains/<chain>.md` — 每链一文件：环节结构、公司表（代码/主营/环节角色/龙头）、龙头收入拆分验证、来源与口径说明。
`references/chains/<chain>.draft.json` — 建链草稿（环节 + 公司清单），供验证脚本使用。

现有链：`ai.md`（人工智能，2026-07-17 验证，133 家 / 19 环节）；`ai_full.draft.json`（全量版，2026-07-17，689 家 / 21 环节 = 基础 133 + Wind 概念板块扩充 556，iFinD 全部验证通过；图谱 `AI产业链图谱.html`，由 `scripts/merge_full.py` + `gen_map.py --draft ...ai_full...` 生成）；`pharma_full.draft.json`（医药，2026-07-21 验证，2026-08-18 剔除温氏股份后 452 家 / 14 环节；图谱 `医药产业链图谱.html`，由 `gen_pharma_map.py` 生成）；`robot.draft.json`（机器人，2026-08-18 验证，231 家 / 11 环节 = Wind 概念板块 346 家 + 补入 7 家，剔除 4 家跨界大市值 + `filter_robot_draft.py` 按主营证据过滤 115 家概念污染；图谱 `机器人产业链图谱.html`，由 `gen_robot_map.py` 生成）；`metal.draft.json`（有色金属，2026-08-18 验证，154 家 / 15 环节 = Wind 概念板块 428 家 + 补入 2 家，`filter_metal_draft.py` 一轮过滤 141 家概念污染 + `clean_metal_draft.py` 二轮剔除 133 家跨界公司并将 11 家归位到正确环节；五子链：工业金属/贵金属/小金属/稀土磁材/能源金属；图谱 `有色金属产业链图谱.html`，由 `gen_metal_map.py` 生成）。

## 回答模式（用户问已有链）

1. 读对应 `references/chains/<chain>.md`。
2. 纯结构问题（环节、公司、代码、归属）→ 直接据库回答，注明库日期。
3. 涉及行情/估值/财务 → 按"活数据现查"逐标的拉取（见下），单标的单次调用，合并呈现。
4. 用户问的公司不在库中 → 走"单家验证"：iFinD `ifind_get_stock_info`（可 3 家一批）看主营产品/竞争对手，判断归属后再回答，并提示可入库。

## 建链 / 扩链模式（新增产业链）

1. 与用户确认：链名、环节粒度（粗三段 or 细分）、市场范围（A 股 / 含港美）。
2. 起草 `references/chains/<chain>.draft.json`（仿 `ai.draft.json`：segments[].companies[]，标 leader）。
3. 成员发现可借助 Wind 概念板块筛选：`stock_data.search_stocks`，question 形如 `筛选属于XX概念板块的股票`（去空格）。注意该接口已知 bug：成功响应偶被包装成 NETWORK_ERROR，数据在错误详情内且可能截断——只用作候选发现，不作最终依据。
4. 批量验证（本 skill 脚本，已测试）：
   ```bash
   python3 scripts/ifind_batch.py --draft references/chains/<chain>.draft.json --out-dir data --phase info
   python3 scripts/ifind_batch.py --draft references/chains/<chain>.draft.json --out-dir data --phase seg
   ```
   - `info`：iFinD `ifind_get_stock_info` 逐批（3 家/次）拉主营产品/主营业务/竞争对手 → `data/<chain>.validated.jsonl`
   - `seg`：对 leader 拉 `ifind_get_stock_business_segmentation`（先当年年报，失败回退上年）
   - `--out-dir` 用相对或绝对路径均可（脚本内已转绝对）；原始 CSV 同目录留档。
5. 据 `validated.jsonl` 与分部数据撰写 `<chain>.md`（格式仿 `ai.md`）：公司表 + 龙头收入验证 + 来源日期。
6. 核对：名称 mismatch、error 记录必须逐条处理，不得跳过。

## 活数据现查

- 行情快照：Wind `get_stock_price_indicators`（indexes 逐字取自 wind 插件 indicators.md）或 iFinD `ifind_get_stock_realtime_price`（≤3 代码/次，存 CSV）。
- 历史行情：iFinD `ifind_get_price`（≤3 代码/次，≤3 年）或 Wind `get_stock_kline`（单标的，yyyyMMdd）。
- 财务指标：iFinD `ifind_get_stock_financial_index`（6 类维度）/ `ifind_get_financial_statements`。
- 环节景气指标：Wind `economic_data.get_economic_data`（EDB，metricIdsStr 无空格）。

调用方式见各插件 skill：Wind 用 `wind-mcp-skill/scripts/cli.mjs call <server> <tool> '<json>'`，iFinD 用 `ifind/scripts/ifind_tool.py call --api-name <api> --params-json '<json>'`。

## 轮动分析（行情推演）

基于已验证链成员做环节轮动统计（首批实现：AI 链，数据截至 2026-07-16）：

```bash
python3 scripts/chain_prices.py --draft references/chains/<chain>.draft.json \
    --out-dir data/prices --start 2025-12-01   # iFinD 日线（3家/次，前复权，断点续跑）
python3 scripts/chain_perf.py                   # 计算指标 -> data/<chain>.perf.json
python3 scripts/gen_dashboard.py --out <页面路径> [--standalone-out <独立文件>]
```

- 指标：区间收益（年初以来/4月以来/近1月/近3月，环节等权均值+中位数）、月度收益矩阵、成交额占比（收盘价×成交量近似）周度变化、轮动排名变化、"转强/转弱/放量"标记
- 看板视图：月度热力图、轮动四象限（X=YTD，Y=近1月，气泡=成交额占比）、资金方向、环节净值曲线、公司下钻
- 口径注意：收益为前复权；成交额为近似；北交所（839493.BJ）iFinD/Wind 行情均未覆盖，统计中剔除并注明

## 行情看板刷新（ai-chain-dashboard.html，2026-08-18 重建管线）

看板内嵌 `var DATA = {...}`（master/snap/segstats/summary/leaders），刷新脚本：

```bash
python3 scripts/refresh_dashboard.py --chain ai --phase fetch      # 通联 getMktEqudAdj 前复权日线，50家/批 -> data/dash_wm/
python3 scripts/refresh_dashboard.py --chain ai --phase build      # 重算 snap/leaders/segstats/summary 写回 HTML
python3 scripts/refresh_dashboard.py --chain pharma --phase fetch  # 医药链 -> data/dash_wm_pharma/
python3 scripts/refresh_dashboard.py --chain pharma --phase build  # 生成/更新 pharma-chain-dashboard.html
python3 scripts/refresh_dashboard.py --chain robot --phase fetch   # 机器人链 -> data/dash_wm_robot/
python3 scripts/refresh_dashboard.py --chain robot --phase build   # 生成/更新 robot-chain-dashboard.html
python3 scripts/refresh_dashboard.py --chain metal --phase fetch   # 有色链 -> data/dash_wm_metal/
python3 scripts/refresh_dashboard.py --chain metal --phase build   # 生成/更新 metal-chain-dashboard.html
```

- 看板：AI 链 `ai-chain-dashboard.html`；医药链 `pharma-chain-dashboard.html`；机器人链 `robot-chain-dashboard.html`；有色链 `metal-chain-dashboard.html`（非 AI 看板外壳由 AI 看板自动生成，标题/分组/SEG_DESC/页脚按 `CHAIN_META` 替换，master 取自对应图谱 chainData 并剔除「待定」组）。

- 通联凭据：`config/wmcloud_token.txt`（从 advisor-asset-assistant 复制；不得输出 token）。
- 龙头规则（2026-08-18 用户确认）：每环节取最新流通市值（negMarketValue）最大的公司为唯一龙头，leaders[*].by 全为 "cap"。
- 北交所 839493.BJ 通联未覆盖，snap 无数据属正常。
- 医药图谱生成脚本 `gen_pharma_map.py` 模板已与 `gen_map.py`（AI 链）逐细节对齐。

## 已知数据源限制（2026-07 实测）

- Wind 网关无专门产业链接口；产业链标签以"概念板块"形式存在（如 `英伟达产业链`、`人工智能+`）。
- Wind NL 类接口（search_stocks / analytics / basicinfo）有 payload 截断 bug：成功响应被包装为 NETWORK_ERROR，详情内数据不完整——避免依赖，改用 iFinD 同功能接口。
- Wind `economic_data` 实测返回"权限不足"，EDB 暂不可用。
- iFinD 接口稳定，每次调用最多 3 个代码，结果存 CSV。


## 图谱展示约定（2026-07-21 用户确认）

- 环节卡片内公司标签不全部展示：默认折叠为约 3 行（`.cos.collapsed{max-height:90px}`），超出部分用"展开其余 N 家 ▾"按钮展开/收起；公司数不超过 3 行的卡片不出现按钮。
- 搜索或"只看龙头"筛选激活时自动展开全部并隐藏展开按钮，清空筛选后恢复折叠。
- 已在 `gen_map.py`（AI 链）与 `gen_pharma_map.py`（医药链）实现，后续新链图谱沿用同一交互。
