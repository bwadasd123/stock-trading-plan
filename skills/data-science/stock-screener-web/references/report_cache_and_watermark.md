# 报表页面开发指南 (/report)

## 缓存优化（重要！）
`/api/report_data` 应优先从 `daily_digest_cache` 表读取已保存的今日看点数据：
- 有缓存 → 直接返回，秒加载
- 无缓存或 `?force=true` → 实时获取东财API

数据复用映射：
- `inflow_sectors` → `sector_flow.top_inflow`
- `outflow_sectors` → `sector_flow.top_outflow`
- `indices` → `indices`

## 水印实现
铺满屏幕的水印效果：
- CSS: `.watermark-overlay` 使用 `display: flex; flex-wrap: wrap` 铺满
- JS: 动态计算屏幕尺寸，生成足够数量的 `.watermark-item`
- 每个 item 300x150px，倾斜35°，文字 16px rgba 蓝色半透明
- 窗口 resize 时自动重铺
- `pointer-events: none` 不影响页面操作

## 数据导入
从原表 `stock_screen_results` 导入到 `stock_scan_results`：
- 原表字段名不同（如 `latest_rsi` → `rsi14`, `latest_turnover` → `turnover`）
- `macd_gold` 需要根据 `macd_bar > 0` 计算
- `ma5/ma10` 原表没有，可用 `latest_price` 近似
- `change_pct` 原表没有，设为0
