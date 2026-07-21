# 数据库表结构参考

## stock_scan_results (扫描结果)
使用 **DictCursor**，字段名为 key：
- `id`, `scan_id`, `ts_code`, `stock_name`
- `latest_price`, `change_pct`, `turnover`, `volume_ratio`
- `rsi14`, `cci20`, `macd_dif`, `macd_dea`, `macd_bar`, `macd_gold`
- `ma5`, `ma10`, `ma20`, `circ_market_cap`, `data_date`, `scan_time`

## scan_task_history (扫描任务)
- `id` (bigint PK), `scan_id`, `task_name`, `start_time`, `end_time`, `duration_seconds`
- `status` ('running'|'completed'|'cancelled'|'timeout')
- `filters_json` (JSON), `total_stocks`, `passed_count`, `failed_count`, `error_message`, `created_at`

**⚠️ 字段名陷阱**: 代码中常用 `passed_stocks` 但实际列名是 `passed_count`。同样 `filters` 实际是 `filters_json`。直接SQL查询时必须用正确列名。

## sector_flow (板块资金流向)
- `fetch_time`, `sector_type` ('industry'|'concept')
- `sector_code`, `sector_name`, `change_pct`
- `main_net_inflow` (**单位：万**，需 /10000 转亿)
- `super_large_inflow`, `large_inflow`, `medium_inflow`, `small_inflow`
- `main_net_pct`
- `lead_stock`, `lead_stock_name`, `lead_stock_pct`
- `lag_stock`, `lag_stock_name`, `lag_stock_pct`

**注意**：main_net_inflow 为正=净流入，为负=净流出。查询流出需 `WHERE main_net_inflow < 0`。

## 常用查询模式

```python
# DictCursor 访问方式 (app.py 内部)
cur = conn.cursor()  # 已配置 DictCursor
row = cur.fetchone()
row["ts_code"]  # ✓ 字典key访问
row[0]          # ✗ 不能用元组索引！
```

**⚠️ 终端查询陷阱**: 从终端用 `python3 -c "..."` 直接查询时，如果没指定 `cursorclass=pymysql.cursors.DictCursor`，默认返回**元组**，必须用 `row[0]` 索引访问，不能用 `row["key"]`。两种方式的访问方式相反：
- App内部 (DictCursor): `row["ts_code"]`, `row["stock_name"]`
- 终端默认 (TupleCursor): `row[0]`, `row[1]`

```sql
-- 首次发现日期（避免 MIN() + 非聚合列的 GROUP BY 错误）
SELECT t.start_time, s2.latest_price
FROM stock_scan_results s2
JOIN scan_task_history t ON s2.scan_id = t.scan_id
WHERE s2.ts_code = %s AND t.status = 'completed'
ORDER BY t.start_time ASC
LIMIT 1

-- 板块流入/流出分别查询
SELECT ... FROM sector_flow WHERE sector_type='industry' AND main_net_inflow > 0
ORDER BY fetch_time DESC, main_net_inflow DESC LIMIT 5

SELECT ... FROM sector_flow WHERE sector_type='industry' AND main_net_inflow < 0
ORDER BY fetch_time DESC, main_net_inflow ASC LIMIT 5
```
