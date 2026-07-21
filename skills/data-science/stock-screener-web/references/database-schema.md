# Database Schema Reference

## Overview
Database: `store` (MySQL via pymysql)
Connection: `pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)`

## Scanner Tables

### scan_task_history
Tracks each scan run.

| Column | Type | Notes |
|--------|------|-------|
| id | bigint PK | auto_increment |
| scan_id | varchar(36) UNIQUE | Format: `YYYYMMDD_HHMMSS` |
| task_name | varchar(100) | Optional user label |
| start_time | datetime | |
| end_time | datetime | |
| duration_seconds | int | |
| status | varchar(20) | `running`, `completed`, `cancelled` |
| filters_json | json | Filter params used |
| total_stocks | int | Total stocks scanned |
| passed_count | int | Stocks passing all filters |
| failed_count | int | |
| error_message | text | |
| created_at | datetime | AUTO |

### stock_scan_results
Individual stock results (only PASSED stocks saved).

| Column | Type | Scanner.py key | Notes |
|--------|------|----------------|-------|
| id | bigint PK | | auto_increment |
| scan_id | varchar(36) | scan_id | FK to scan_task_history |
| ts_code | varchar(20) | code | Stock code |
| stock_name | varchar(50) | name | |
| latest_price | decimal(10,2) | price | |
| change_pct | decimal(10,2) | change_pct | |
| turnover | decimal(10,2) | turnover | |
| volume_ratio | decimal(10,2) | vol_ratio | |
| rsi14 | decimal(10,2) | rsi | |
| cci20 | decimal(10,2) | cci | |
| macd_dif | decimal(10,4) | dif | |
| macd_dea | decimal(10,4) | dea | |
| macd_bar | decimal(10,4) | bar | |
| macd_gold | tinyint | macd_gold | 1=yes, 0=no |
| ma5 | decimal(10,2) | ma5 | |
| ma10 | decimal(10,2) | ma10 | |
| ma20 | decimal(10,2) | ma20 | |
| circ_market_cap | decimal(10,2) | circ_cap | In 亿 |
| data_date | date | data_date | |
| scan_time | datetime | | AUTO |

### stock_snapshot
Raw snapshot data from each page of sector list API.
Columns: scan_id, ts_code, stock_name, latest_price, change_pct, turnover, amount, pe, circ_market_cap, snapshot_time

## Other Tables (Not Scanner)

| Table | Purpose |
|-------|---------|
| sector_flow | 板块资金流向 data |
| daily_digest_cache | 今日看点 JSON cache |
| dragon_tiger | 龙虎榜 data |
| historical_data | 历史信号 |
| v_scan_results_with_change | VIEW for scan results with price change |

## Pitfalls
1. **Only passed stocks saved**: `save_scan_result()` is called inside `if ok:` block in scanner.py, so DB only contains passing records. To debug why a stock was filtered, check scanner.py logs, not DB.
2. **Column name mismatch**: scanner.py uses `code`, `name`, `rsi`, `cci`, `vol_ratio` but DB columns are `ts_code`, `stock_name`, `rsi14`, `cci20`, `volume_ratio`. The `save_scan_result()` function in database.py handles the mapping.
3. **Table name mismatch**: Code references `scan_task_history` and `stock_scan_results` (correct), NOT `scan_tasks` / `scan_results` (wrong).
4. **DictCursor returns dicts, NOT tuples**: `get_db()` uses `cursorclass=pymysql.cursors.DictCursor`. Always access columns by name (`r["sector_name"]`), never by index (`r[0]`). This applies to ALL queries.

## sector_flow Table Schema

| Column | Type | Notes |
|--------|------|-------|
| id | bigint PK | auto_increment |
| fetch_time | datetime | When data was fetched |
| sector_type | varchar(20) | 'industry' or 'concept' |
| sector_code | varchar(20) | e.g. 'BK0475' |
| sector_name | varchar(50) | e.g. '通信' |
| change_pct | decimal(10,2) | Sector change % |
| main_net_inflow | decimal(20,2) | 主力净流入, **单位: 万元** (需÷10000转亿) |
| lead_stock | varchar(20) | 领涨股代码 |
| lead_stock_name | varchar(50) | 领涨股名称 |
| lead_stock_pct | decimal(10,2) | 领涨股涨幅% |
| lag_stock | varchar(20) | 领跌股代码 |
| lag_stock_name | varchar(50) | 领跌股名称 |
| lag_stock_pct | decimal(10,2) | 领跌股跌幅% |
