# 产业链看板项目 · 交接文档

> 交接日期：2026-08-18 · 接收方：workbuddy
> 项目目录：`/Users/sirius/Documents/kimi/workspace/industry-chain`
> 线上地址：https://sirius2843.github.io/industry-chain/ （GitHub Pages，main 分支根目录）
> 仓库：`git@github.com:sirius2843/industry-chain.git`

---

## 1. 项目是什么

四条 A 股产业链（人工智能 / 医药 / 机器人 / 有色金属）的**产业链图谱 + 每日行情看板**，外加一个**门户页**（Tab 切换 + 各链当日行情总览）。每个交易日 16:00 自动刷新行情并推送到 GitHub Pages。

| 链 | 图谱文件 | 看板文件 | 公司数 / 环节数 |
|---|---|---|---|
| 人工智能 | `AI产业链图谱.html` | `ai-chain-dashboard.html` | 689 / 21 |
| 医药 | `医药产业链图谱.html` | `pharma-chain-dashboard.html` | 452 / 14 |
| 机器人 | `机器人产业链图谱.html` | `robot-chain-dashboard.html` | 231 / 11 |
| 有色金属 | `有色金属产业链图谱.html` | `metal-chain-dashboard.html` | 154 / 15 |

门户页：`index.html`（总览卡片含各链中位涨跌幅、上涨占比、领涨/领跌环节、龙头当日表现，标注行情日期）。

## 2. 每日更新链路（核心维护对象）

**定时任务**：Kimi Work Automation `automation_6cf515ee-cbca-4ae0-908a-7b5f15c44c1e`
- 触发：cron `0 16 * * *`，时区 Asia/Shanghai，已启用
- 执行方式：agent local_conversation，工作区 = 本项目目录
- 动作：运行 `scripts/daily_refresh.sh` 并汇报结果

**`scripts/daily_refresh.sh` 流程**（手动执行效果相同）：

```bash
bash scripts/daily_refresh.sh
```

1. 删除四条链的行情缓存 `data/dash_wm*/px_*.csv`
   ⚠️ **必须删**：`refresh_dashboard.py` 的 fetch 阶段对已有文件直接跳过，不删缓存就永远用旧数据
2. 逐链执行 `python3 scripts/refresh_dashboard.py --chain <ai|pharma|robot|metal> --phase fetch`（通联 `getMktEqudAdj` 前复权日线，50 家/批）和 `--phase build`（重算快照/环节统计/龙头，写回看板 HTML）
3. `python3 scripts/build_portal.py` 重建 `index.html`
4. `git add -A`；有变更则 `git commit -m "daily refresh <日期>"` 并 `git push`；无变更（非交易日）自动跳过

**迁移到 workbuddy 时的最小动作**：把每日定时触发指向 `bash scripts/daily_refresh.sh`（退出码非 0 即失败），或直接把脚本逻辑搬进 workbuddy 的调度器。脚本自包含，不依赖 Kimi Work。

## 3. 数据源与凭据

| 用途 | 数据源 | 说明 |
|---|---|---|
| 每日行情 / 流通市值 | **通联数据 WMCloud** `market/getMktEqudAdj` | token 在 `config/wmcloud_token.txt`（**已被 .gitignore 排除，严禁提交**）。token 失效时重新获取并覆盖该文件即可 |
| 建链骨架（一次性） | Wind 概念板块 + iFinD `ifind_get_stock_info` / 业务分部 | 仅在新增产业链或大修时使用，日常刷新不依赖 |

GitHub 推送：本机 SSH key（`~/.ssh/id_ed25519`）已配置，git 身份 `sirius2843 <sirius2843@users.noreply.github.com>`（仓库级 config）。

## 4. 目录结构

```
industry-chain/
├── index.html                  # 门户页（build_portal.py 生成，勿手改）
├── *.html                      # 4 图谱 + 4 看板（看板由脚本写回，勿手改 DATA）
├── SKILL.md                    # 建链方法论全流程文档（新增产业链必读）
├── HANDOVER.md                 # 本文档
├── config/wmcloud_token.txt    # 通联 token（不进 git）
├── data/                       # 行情缓存与中间数据（不进 git）
├── references/chains/          # 各链 draft JSON（骨架真相源）
└── scripts/
    ├── daily_refresh.sh        # ★ 每日刷新总入口
    ├── refresh_dashboard.py    # 拉行情 + 重建看板（CHAIN_META 配置各链）
    ├── build_portal.py         # 从 4 个看板 DATA 生成门户页
    ├── gen_*_map.py            # 各链图谱生成器
    ├── build_*_draft.py        # 各链骨架构建
    ├── filter/clean_*.py       # 概念污染清洗
    └── wind_concepts.py / ifind_batch.py  # Wind/iFinD 批量取数
```

## 5. 关键规则（改动前必读）

1. **龙头规则**：每环节取最新流通市值最大的公司为唯一龙头，build 阶段自动重定，可能随行情变化。
2. **「待定」组**（`metal-tbd` 等）只在图谱展示，不进看板（`exclude_groups`）。
3. **看板 DATA 是内嵌在 HTML 里的**（`var DATA = {...}`），所有统计由 build 阶段写回；改结构要同步改 `build_portal.py` 的读取逻辑。
4. **北交所代码**（920xxx.BJ）涨跌停 30%，`board_limit()` 已处理；通联 ticker 用纯数字（`wm_ticker()` 去后缀）。
5. 新增产业链走「老流程」，完整步骤见 `SKILL.md`：Wind 概念发现 → draft → iFinD 验证 → 两轮污染清洗 → 生成图谱 → `CHAIN_META` 注册 → fetch/build 看板 → 门户页 `CHAINS` 加一行。

## 6. 故障排查

| 症状 | 原因 / 处理 |
|---|---|
| 看板日期不更新 | px 缓存没删 → 确认经 `daily_refresh.sh` 入口；或当天非交易日（正常） |
| fetch 报错 / 401 | 通联 token 失效 → 更新 `config/wmcloud_token.txt` |
| push 失败 | 检查 `ssh -T git@github.com`；本地刷新结果不受影响，恢复后手动 `git push` |
| GitHub Pages 未更新 | Pages 部署有 1-2 分钟延迟；确认 push 成功且 Pages 源 = main/root |
| 某环节龙头变成跨界公司 | 骨架混入概念污染 → 按 `SKILL.md` 清洗流程从 draft 剔除，重新生成图谱和看板 |

## 7. 交接检查单

- [ ] 能手动跑通 `bash scripts/daily_refresh.sh`
- [ ] 定时调度已指向该脚本（或逻辑已迁入 workbuddy）
- [ ] `config/wmcloud_token.txt` 已就位且未进 git
- [ ] `git push` 通（SSH key）
- [ ] https://sirius2843.github.io/industry-chain/ 可访问
