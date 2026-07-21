# Database Operations Reference

## Connection

```python
from models.database import get_db

db = get_db()  # Returns pymysql connection with DictCursor
cursor = db.cursor()

# Use DictCursor access pattern
cursor.execute("SELECT COUNT(*) as cnt FROM stock_snapshot")
count = cursor.fetchone()['cnt']  # NOT cursor.fetchone()[0]

cursor.close()
db.close()
```

**⚠️ Common Import Errors:**
- ❌ `from db_pool import get_conn` — Module doesn't exist
- ❌ `from models.database import get_conn` — Function doesn't exist
- ✅ `from models.database import get_db` — Correct

## Table Schemas (as of 2026-06-16)

### stock_snapshot
| Column | Type | Notes |
|--------|------|-------|
| id | bigint | |
| scan_id | varchar(36) | |
| ts_code | varchar(20) | |
| stock_name | varchar(50) | |
| latest_price | decimal(10,2) | |
| change_pct | decimal(10,2) | |
| turnover | decimal(10,2) | |
| amount | decimal(20,2) | |
| pe | decimal(10,2) | |
| circ_market_cap | decimal(10,2) | |
| scan_time | datetime | **Use for date filtering** |

### stock_scan_results
| Column | Type | Notes |
|--------|------|-------|
| id | bigint | |
| scan_id | varchar(36) | |
| ts_code | varchar(20) | |
| stock_name | varchar(50) | |
| latest_price | decimal(10,2) | |
| change_pct | decimal(10,2) | |
| turnover | decimal(10,2) | |
| volume_ratio | decimal(10,2) | |
| rsi14 | decimal(10,2) | |
| cci20 | decimal(10,2) | |
| macd_dif | decimal(10,4) | |
| macd_dea | decimal(10,4) | |
| macd_bar | decimal(10,4) | |
| macd_gold | tinyint | |
| ma5 | decimal(10,2) | |
| ma10 | decimal(10,2) | |
| ma20 | decimal(10,2) | |
| circ_market_cap | decimal(10,2) | |
| data_date | date | |
| scan_time | datetime | **Use for date filtering** |

### scan_task_history
| Column | Type | Notes |
|--------|------|-------|
| id | bigint | |
| scan_id | varchar(36) | |
| task_name | varchar(100) | |
| start_time | datetime | |
| end_time | datetime | |
| duration_seconds | int | |
| status | varchar(20) | |
| filters_json | json | |
| total_stocks | int | |
| passed_count | int | |
| failed_count | int | |
| error_message | text | |
| created_at | datetime | **Use for date filtering** |

## Data Cleanup

```python
from models.database import get_db
from datetime import date

db = get_db()
cursor = db.cursor()
today = date.today().isoformat()

# Check data volume first
cursor.execute(f"SELECT COUNT(*) as cnt FROM stock_snapshot WHERE DATE(scan_time)='{today}'")
print(f"stock_snapshot: {cursor.fetchone()['cnt']}条")

cursor.execute(f"SELECT COUNT(*) as cnt FROM stock_scan_results WHERE DATE(scan_time)='{today}'")
print(f"stock_scan_results: {cursor.fetchone()['cnt']}条")

cursor.execute(f"SELECT COUNT(*) as cnt FROM scan_task_history WHERE DATE(created_at)='{today}'")
print(f"scan_task_history: {cursor.fetchone()['cnt']}条")

# Delete
cursor.execute(f"DELETE FROM stock_snapshot WHERE DATE(scan_time)='{today}'")
cursor.execute(f"DELETE FROM stock_scan_results WHERE DATE(scan_time)='{today}'")
cursor.execute(f"DELETE FROM scan_task_history WHERE DATE(created_at)='{today}'")

db.commit()
cursor.close()
db.close()
```

**⚠️ Date Column Differences:**
- `stock_snapshot` and `stock_scan_results` use `scan_time`
- `scan_task_history` uses `created_at`
