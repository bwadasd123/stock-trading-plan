# signal_price_history — 全市场股票价格存储（2026-06-29）

## 背景

report页面历史信号需要显示"现价"和"距入选"，之前用的是扫描时存储的旧价格（`stock_scan_results.latest_price`），股票不再被扫描后价格永远不变。

用户方案：不要在report请求时实时调API，而是在每天盘后双版本对比扫描时，每页拉取的所有股票价格都存储到`signal_price_history`表。

## 数据库表

```sql
CREATE TABLE signal_price_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    price DECIMAL(10,3) NOT NULL,
    change_pct DECIMAL(10,3),
    snap_date DATE NOT NULL,
    snap_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_date (ts_code, snap_date),
    INDEX idx_ts_code (ts_code),
    INDEX idx_snap_date (snap_date)
);
```

## 数据写入

`models/database.py` → `save_signal_prices_batch(conn, stocks)`:

```python
def save_signal_prices_batch(conn, stocks):
    """批量保存每页所有股票价格，不只是过第一轮的"""
    today = date.today()
    sql = """INSERT INTO signal_price_history (ts_code, price, change_pct, snap_date)
             VALUES (%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE price=VALUES(price), change_pct=VALUES(change_pct),
              snap_time=CURRENT_TIMESTAMP"""
    batch = [(s["code"], s["price"], s["change_pct"], today) for s in stocks]
    cur.executemany(sql, batch)
    conn.commit()
```

`services/scanner_dual.py` 在 `save_snapshot_batch()` 之后调用：

```python
save_snapshot_batch(conn, scan_id_old, stocks)       # 原有：存快照
save_signal_prices_batch(conn, stocks)               # 新增：存价格供report用
```

## 数据读取

`api/report.py` → `_load_signals()`:

```python
# 从signal_price_history取今天的最新价格
cur.execute("""
    SELECT ts_code, price, change_pct
    FROM signal_price_history
    WHERE ts_code IN (...)
    AND snap_date = CURDATE()
""")
today_prices = {row["ts_code"]: {"price": row["price"], ...}}

# 优先用今日存储价，没有则回退到扫描价
tp = today_prices.get(code)
display_price = tp["price"] if tp else db_price
```

## 关键设计

- **不额外定时任务**：扫描时顺带存入，不需要独立cronjob
- **存全量**：每页所有股票都存，不限于过第一轮筛选的
- **upsert**：ON DUPLICATE KEY UPDATE，同一天多次扫描自动更新
