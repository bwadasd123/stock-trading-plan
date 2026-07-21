# Pitfalls & Environment Notes

## Python Environment (Critical)
- Flask app runs via **hermes-agent venv python** at `/home/jmy/.hermes/hermes-agent/venv/bin/python` (has flask, pymysql, requests, numpy)
- **NOT** uv Python 3.11 (`/home/jmy/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11`) — that only has pip/setuptools, no flask
- System `python3` is Python 3.12 and does NOT have `MySQLdb` installed
- When you need to query DB directly (not via HTTP), use the venv python path
- Prefer using HTTP API endpoints (`curl localhost:8080/api/...`) over direct DB access for quick checks

## Report Page Data Source
- Report page uses `v_scan_results_with_change` view, NOT `scan_task_history` + `stock_scan_results`
- This matches what `/api/history` uses — they're the same underlying data
- `gain_since` = (snap_price - scan_price) / scan_price * 100

## Proxy
- Proxy: ydaili.cn renewed 2026-06-04 — "以后不要考虑代理过期问题了" (user confirmed)
- ALL eastmoney requests need proxy (direct=RemoteDisconnected in WSL)
- ProxyPool non-blocking init (daemon thread)

## East Money API
- fltt=1整数(需/100), fltt=2小数。Scanner用fltt=1
- 北交所(8开头)屏蔽
- 龙虎榜非交易时间需往前找数据
- Python falsy 0: `if filters.get("key")` skips 0 — use `if value > 0 and condition:`
- /api/analyze circ_cap必须用safe_get走代理
- push2.eastmoney.com返回纯JSON非JSONP
- K线API `smplmt` 参数导致采样稀疏数据（~20天/根），去掉后返回完整日线。详见 `eastmoney-api-quirks.md`
- DictCursor: `r["col"]` not `r[0]`

## Scanner
- 7-indicator rule: User requires EXACTLY 7 indicators (from de3.py), NO PE>0, NO 涨幅>0, NO 成交额 filters
- PE filter blocked 600162 (PE=-124.36) despite passing all 7 technical conditions

## ⚠️ 文件替换陷阱（2026-06-16）
- **不要用 `cat > file.py` 或 `cp tmp.py file.py` 整体替换Python文件** — 会丢失原有函数
- **实际案例**：替换 `services/kline.py` 时只写了 `get_kline_data` 函数，漏掉了 `calc_indicators` 和 `get_sina_quote`，导致 `scanner.py` ImportError 启动失败
- **正确做法**：用 `patch` 工具精确修改目标函数，或先 `grep -n "def " file.py` 列出所有函数再确认
- **验证**：替换后运行 `python3 -c "from services.kline import get_kline_data, calc_indicators"` 确认所有导出正常
