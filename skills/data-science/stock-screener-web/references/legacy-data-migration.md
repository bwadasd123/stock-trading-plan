# Legacy Database Tables & Migration Guide

## Overview

The MySQL database at `115.190.204.205:7425` (database: `store`) contains legacy tables from a previous stock screening system. Some contain valuable historical data that can be migrated to the new system's tables.

## Legacy Tables (Old System)

### stock_screen_results (199 rows, 2025-12-03 ~ 2026-05-28)
Primary legacy screening results. 78 trading days of data.

| Old Field | New Field (stock_scan_results) | Notes |
|-----------|-------------------------------|-------|
| `ts_code` | `ts_code` | Direct match |
| `stock_name` | `stock_name` | Direct match |
| `latest_price` | `latest_price` | Direct match |
| `latest_turnover` | `turnover` | Renamed |
| `volume_ratio` | `volume_ratio` | Direct match |
| `latest_rsi` | `rsi14` | Renamed |
| `latest_cci` | `cci20` | Renamed |
| `macd_diff` | `macd_dif` | Renamed |
| `macd_dea` | `macd_dea` | Direct match |
| `macd_bar` | `macd_bar` | Direct match |
| `ma20_value` | `ma20` | Renamed |
| `circ_market_cap` | `circ_market_cap` | Direct match |
| `data_date` | `data_date` | Direct match |
| `create_time` | `scan_time` | Renamed |
| — | `scan_id` | Generated: `CONCAT('legacy_', DATE_FORMAT(data_date, '%Y%m%d'))` |
| — | `change_pct` | Not available in old table; set to 0 or NULL |
| — | `ma5`, `ma10` | Not available in old table; set to 0 |
| — | `macd_gold` | Calculated: `CASE WHEN macd_bar > 0 THEN 1 ELSE 0 END` |

Other fields (not migrated): `sector_name`, `sector_code`, `prev_volume`, `latest_volume`, `price_ma20_diff`, `circ_share`, `total_share`, `total_market_cap`, `sector_pct`

### stock_screen_results_share (4989 rows, 2026-01-20 ~ 2026-03-02)
Full market scan snapshots with technical indicators. Most rows have `is_qualified=0` (4691), only 298 are qualified.

Key fields: `ts_code` (format: `600000.SH`), `name`, `trade_date` (format: `20260302`), `close`, `circ_mv`, `turnover_rate`, `volume_ratio`, `ma5/10/20`, `dif/dea/macd`, `rsi14/rsi9`, `cci20/cci14`, `k/d/j`, `is_qualified`, `screen_conditions` (JSON)

### historical_data (825 rows)
Price history with SMA, RSI, volatility. Linked to `config_id`. Appears to be index/futures data, not individual stocks.

### trade_records (48 rows)
Trade records with `order_price`, `future_price`, `prediction`, `result`, `balance`, `profit_loss`. Appears to be from a prediction/trading system.

### Other Legacy Tables
- `hotlog`, `my_hotlog`, `hotlog_copy1` — Hot stock logs (45 rows each)
- `my_log` (1799 rows) — Payment/order logs (not stock data)
- `hzmy_log` (305506 rows) — Large volume of transaction logs
- `announcement` (4559 rows) — Platform announcements (not stock market)
- `jmy_zq` (2827 rows) — Lottery/raffle records
- `v_dfcf`, `v_hotli` — Small view tables

## Migration SQL

### Import stock_screen_results → stock_scan_results

```sql
-- Step 1: Clear target table (user may have fake/test data)
DELETE FROM stock_scan_results;

-- Step 2: Import with field mapping
INSERT INTO stock_scan_results 
(scan_id, ts_code, stock_name, latest_price, change_pct, turnover, 
 volume_ratio, rsi14, cci20, macd_dif, macd_dea, macd_bar, macd_gold,
 ma5, ma10, ma20, circ_market_cap, data_date, scan_time)
SELECT 
    CONCAT('legacy_', DATE_FORMAT(data_date, '%Y%m%d')) as scan_id,
    ts_code, stock_name, latest_price,
    0 as change_pct,           -- Not available in old table
    latest_turnover as turnover,
    volume_ratio,
    latest_rsi as rsi14,
    latest_cci as cci20,
    macd_diff as macd_dif,
    macd_dea, macd_bar,
    CASE WHEN macd_bar > 0 THEN 1 ELSE 0 END as macd_gold,
    0 as ma5,                  -- Not available
    0 as ma10,                 -- Not available
    ma20_value as ma20,
    circ_market_cap, data_date,
    create_time as scan_time
FROM stock_screen_results;

-- Step 3: Verify import
SELECT COUNT(*) as total, MIN(data_date) as earliest, MAX(data_date) as latest
FROM stock_scan_results;
```

### API Code Changes for VIEW

After creating the VIEW, update `api/history.py` to query from the VIEW instead of `stock_scan_results`:

```python
# Change all queries from:
cur.execute("SELECT * FROM stock_scan_results WHERE ...")
# To:
cur.execute("SELECT * FROM v_scan_results_with_change WHERE ...")
```

Endpoints to update:
- `api_task_detail()` - Task detail results
- `api_history()` - Historical scan records
- `api_history_dates()` - Available scan dates
- `api_history_hot()` - Frequently appearing stocks

## Table Purpose Distinction

- **stock_snapshot** — Full market snapshot (所有股票), saved during every scan. Contains ALL stocks, not just filtered ones. Data volume: 5000-11000 rows per day. **No GEM stocks (300xxx/301xxx/302xxx)** — scanner filters them out.
- **stock_scan_results** — Filtered stocks (符合条件的) that passed screening criteria.

## Price Change Calculation

### Preferred: Database VIEW Approach

Create a VIEW that automatically joins `stock_scan_results` with `stock_snapshot` to calculate `change_pct`. Frontend queries the VIEW — no application code changes needed.

**Two VIEW strategies:**

#### Strategy A: Compare with latest snapshot price (recommended for sparse data)

When `stock_snapshot` has limited date coverage (e.g., only 4 days vs 78 days of scan results), use the latest available snapshot price as the baseline. This shows "gain/loss since stock was first flagged":

```sql
CREATE OR REPLACE VIEW v_scan_results_with_change AS
SELECT 
    r.id, r.scan_id, r.ts_code, r.stock_name, r.latest_price,
    r.turnover, r.volume_ratio, r.rsi14, r.cci20,
    r.macd_dif, r.macd_dea, r.macd_bar, r.macd_gold,
    r.ma5, r.ma10, r.ma20, r.circ_market_cap,
    r.data_date, r.scan_time,
    latest_snap.latest_price AS latest_snap_price,
    latest_snap.scan_time AS latest_snap_time,
    CASE 
        WHEN latest_snap.latest_price IS NOT NULL AND latest_snap.latest_price > 0 
        THEN ROUND((latest_snap.latest_price - r.latest_price) / r.latest_price * 100, 2)
        ELSE NULL 
    END AS change_pct,
    first_discovery.first_date AS first_discovery_date
FROM stock_scan_results r
LEFT JOIN (
    SELECT ts_code, latest_price, scan_time,
           ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY scan_time DESC) AS rn
    FROM stock_snapshot
) latest_snap ON r.ts_code = latest_snap.ts_code AND latest_snap.rn = 1
LEFT JOIN (
    SELECT ts_code, MIN(data_date) AS first_date
    FROM stock_scan_results GROUP BY ts_code
) first_discovery ON r.ts_code = first_discovery.ts_code
WHERE r.ts_code NOT LIKE '300%' 
  AND r.ts_code NOT LIKE '301%' 
  AND r.ts_code NOT LIKE '302%';
```

#### Strategy A Extended: Adding max_amount fields

To track the highest trading volume day for each stock, add a `max_amount_info` subquery:

```sql
LEFT JOIN (
    SELECT ts_code, max_amount, max_amount_date, latest_price AS max_amount_price
    FROM (
        SELECT ts_code, amount AS max_amount, DATE(scan_time) AS max_amount_date,
               latest_price,
               ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY amount DESC) AS rn
        FROM stock_snapshot WHERE amount > 0
    ) ranked WHERE rn = 1
) max_amount_info ON r.ts_code = max_amount_info.ts_code
```

Additional columns to SELECT:
```sql
max_amount_info.max_amount,
max_amount_info.max_amount_date,
max_amount_info.max_amount_price,
CASE 
    WHEN max_amount_info.max_amount_price IS NOT NULL AND r.latest_price > 0 
    THEN ROUND((max_amount_info.max_amount_price - r.latest_price) / r.latest_price * 100, 2)
    ELSE NULL 
END AS max_amount_change_pct
```

Display in frontend: `max_amount` → divide by 1e8 to show in 亿.

**Key differences from Strategy B:**
- Uses latest snapshot price (not previous day) — works even with sparse snapshot data
- Filters out GEM stocks (300xxx) since they're never in `stock_snapshot`
- `change_pct` = `(latest_snap_price - entry_price) / entry_price * 100`
- Shows cumulative gain/loss from when stock was first flagged to now
- Includes `first_discovery_date` for dedup support

#### Strategy B: Compare with previous day price (requires full snapshot coverage)

Use this when `stock_snapshot` has complete daily data. Shows "gain/loss from entry day to next day":

```sql
CREATE OR REPLACE VIEW v_scan_results_with_change AS
SELECT 
    r.id, r.scan_id, r.ts_code, r.stock_name, r.latest_price,
    r.turnover, r.volume_ratio, r.rsi14, r.cci20,
    r.macd_dif, r.macd_dea, r.macd_bar, r.macd_gold,
    r.ma5, r.ma10, r.ma20, r.circ_market_cap,
    r.data_date, r.scan_time,
    CASE 
        WHEN prev_price.latest_price IS NOT NULL AND prev_price.latest_price > 0 
        THEN ROUND((r.latest_price - prev_price.latest_price) / prev_price.latest_price * 100, 2)
        ELSE NULL 
    END AS change_pct,
    prev_price.latest_price AS prev_price,
    prev_price.scan_time AS prev_scan_time
FROM stock_scan_results r
LEFT JOIN (
    SELECT ts_code, DATE(scan_time) AS snap_date, latest_price, scan_time,
           ROW_NUMBER() OVER (PARTITION BY ts_code, DATE(scan_time) ORDER BY scan_time DESC) AS rn
    FROM stock_snapshot
) prev_price ON r.ts_code = prev_price.ts_code 
    AND prev_price.snap_date = DATE_SUB(r.data_date, INTERVAL 1 DAY)
    AND prev_price.rn = 1;
```

**When change_pct is NULL**:
- Legacy data from before `stock_snapshot` collection began
- GEM stocks (300xxx/301xxx/302xxx) — no snapshot data exists
- Display as "—" in UI

### Alternative: Application-level Calculation

```python
prev_price = cur.fetchone("""
    SELECT latest_price FROM stock_snapshot 
    WHERE ts_code = %s AND DATE(scan_time) = DATE_SUB(%s, INTERVAL 1 DAY)
    LIMIT 1
""", (ts_code, data_date))
change_pct = (current_price - prev_price) / prev_price * 100 if prev_price else None
```

## Pitfalls

1. **Always clear target table first** — User explicitly requested clearing existing (fake) data before import
2. **scan_id format** — Use `legacy_YYYYMMDD` to distinguish imported records from new scans (format: `YYYYMMDD_HHMMSS`)
3. **Missing fields** — Old table lacks `change_pct`, `ma5`, `ma10`; set to 0 or NULL
4. **macd_gold calculation** — Old table doesn't have boolean flag; derive from `macd_bar > 0`
5. **stock_screen_results_share ts_code format** — Uses `600000.SH` format with market suffix, while `stock_screen_results` uses bare `002686` format
6. **trade_date format** — `stock_screen_results_share` uses `20260302` (no hyphens), while `stock_screen_results` uses proper DATE type
7. **MySQL LIMIT & IN subquery not supported** — Use JOIN instead (see pitfall in main SKILL.md)
8. **User prefers database-level solutions** — User explicitly said "你弄个视图关联一下不就好了吗？这样之前的功能都不需要改了" (just create a view to join, then existing features don't need changes). Prefer VIEWs over modifying application code when adding derived columns.
9. **GEM stocks permanently blocked** — Scanner filters out codes starting with 300/301/302 (创业板). This is a permanent configuration in `services/scanner.py`. stock_snapshot will NEVER contain GEM stocks, so change_pct will always be NULL for legacy GEM stock data.
10. **MySQL `only_full_group_by` mode** — When using MAX() with non-aggregated columns in subqueries, use ROW_NUMBER() window function instead of GROUP BY. Example: getting the row with MAX(amount) AND its associated date/price requires `ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY amount DESC)` in a subquery, then filter `WHERE rn = 1`.

## Statistics Dashboard API Pattern

For system performance analytics (胜率, 盈亏分布, etc.):

```python
@bp.route("/api/history/stats")
def api_history_stats():
    days = int(request.args.get("days", 0))
    dedup = request.args.get("dedup", "0") == "1"
    
    dedup_condition = "AND first_discovery_date = data_date" if dedup else ""
    
    with conn.cursor() as cur:
        # Win/loss stats — separate SQL for days>0 vs days=0 to avoid param binding issues
        if days > 0:
            cur.execute(f"""
                SELECT COUNT(*) as total_signals,
                       COUNT(CASE WHEN change_pct > 0 THEN 1 END) as win_signals,
                       COUNT(CASE WHEN change_pct < 0 THEN 1 END) as lose_signals,
                       AVG(change_pct) as avg_change,
                       MIN(change_pct) as min_change,
                       MAX(change_pct) as max_change
                FROM v_scan_results_with_change
                WHERE change_pct IS NOT NULL {dedup_condition}
                  AND scan_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days,))
        else:
            cur.execute(f"""
                SELECT COUNT(*) as total_signals,
                       COUNT(CASE WHEN change_pct > 0 THEN 1 END) as win_signals,
                       COUNT(CASE WHEN change_pct < 0 THEN 1 END) as lose_signals,
                       AVG(change_pct) as avg_change,
                       MIN(change_pct) as min_change,
                       MAX(change_pct) as max_change
                FROM v_scan_results_with_change
                WHERE change_pct IS NOT NULL {dedup_condition}
            """)
        
        # Distribution buckets, Top/Bottom 5 signals, Monthly stats
    
    win_rate = round(win_signals / total * 100, 2) if total > 0 else 0
    
    return jsonify({
        "overview": { "total_signals", "win_signals", "lose_signals", "win_rate", "avg_change", "min_change", "max_change" },
        "distribution": [...],
        "monthly": [...],
        "top_signals": [...],
        "bottom_signals": [...]
    })
```

Frontend: Stats dashboard with grid cards + distribution bar + top/bottom tables. Refresh when query params change.

### Distribution Query Pattern (avoid % in f-strings)

The distribution query uses CASE WHEN with percentage ranges. The `%` character in string literals like `'大涨50%以上'` conflicts with Python's f-string formatting. Use string concatenation instead:

```python
# WRONG — f-string % conflict
cur.execute(f"""
    SELECT CASE WHEN change_pct >= 50 THEN '大涨50%以上' ... END
    FROM v_scan_results_with_change WHERE ...
""")

# RIGHT — build SQL as regular string
sql = f"""
    SELECT CASE WHEN change_pct >= 50 THEN '大涨50%以上' ... END
    FROM v_scan_results_with_change WHERE change_pct IS NOT NULL {dedup_condition}
"""
cur.execute(sql)

# For DATE_FORMAT, use string concatenation:
sql = "SELECT DATE_FORMAT(data_date, '%s') as month FROM ..." % '%Y-%m'
```

### Distribution Bucket Names

Use Chinese names without parentheses to avoid escaping issues:
```python
'大涨50%以上'    # NOT '大涨(≥50%)'
'大涨20-50%'
'上涨10-20%'
'小涨0-10%'
'小跌0-10%'
'下跌10-20%'
'大跌20-50%'
'暴跌50%以上'
```
