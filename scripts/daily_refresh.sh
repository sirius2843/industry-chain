#!/bin/bash
# 每日收盘后刷新：四条链行情 -> 看板 -> 门户页 -> 推送 GitHub Pages
# 由定时任务在每个交易日 16:00 调用；非交易日通联返回的最近交易日不变，git 无变更时自动跳过。
set -e
cd "$(dirname "$0")/.."

# 逐链清行情缓存（fetch 默认跳过已有文件，不清则永远用旧数据）再拉取重建
for c in ai pharma robot metal; do
  case $c in
    ai) d=data/dash_wm ;; pharma) d=data/dash_wm_pharma ;;
    robot) d=data/dash_wm_robot ;; metal) d=data/dash_wm_metal ;;
  esac
  rm -f "$d"/px_*.csv
  python3 scripts/refresh_dashboard.py --chain "$c" --phase fetch
  python3 scripts/refresh_dashboard.py --chain "$c" --phase build
done

python3 scripts/build_portal.py

git add -A
if git diff --cached --quiet; then
  echo "[daily_refresh] 无数据变更，跳过提交"
else
  git commit -q -m "daily refresh $(date +%F)"
  git push
  echo "[daily_refresh] 已提交并推送"
fi
