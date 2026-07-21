# Task Tracking Pattern

Reusable pattern for adding audit history to scanning tasks.

## Database Table

```sql
CREATE TABLE IF NOT EXISTS scan_task_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scan_id VARCHAR(36) NOT NULL COMMENT 'Batch ID (YYYYMMDD_HHMMSS)',
    task_name VARCHAR(100) DEFAULT '' COMMENT 'User-provided name/notes',
    start_time DATETIME NOT NULL,
    end_time DATETIME DEFAULT NULL,
    duration_seconds INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running' COMMENT 'running/completed/failed/cancelled',
    filters_json JSON COMMENT 'Filter conditions used',
    total_stocks INT DEFAULT 0,
    passed_count INT DEFAULT 0,
    failed_count INT DEFAULT 0,
    error_message TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_scan_id (scan_id),
    INDEX idx_start_time (start_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## Helper Functions

```python
def save_task_start(conn, scan_id, start_time, filters, task_name=""):
    """Record task beginning"""
    sql = """INSERT INTO scan_task_history
             (scan_id, task_name, start_time, status, filters_json)
             VALUES (%s, %s, %s, 'running', %s)
             ON DUPLICATE KEY UPDATE
              start_time=VALUES(start_time), status='running',
              filters_json=VALUES(filters_json), error_message=NULL"""
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (scan_id, task_name, start_time, 
                            json.dumps(filters, ensure_ascii=False)))
        conn.commit()
    except Exception as e:
        logger.error(f"Save task start error: {e}")


def save_task_end(conn, scan_id, end_time, status, total, passed, failed, error_msg=None):
    """Record task completion"""
    sql = """UPDATE scan_task_history SET
             end_time=%s, status=%s, total_stocks=%s, passed_count=%s,
             failed_count=%s, error_message=%s,
             duration_seconds=TIMESTAMPDIFF(SECOND, start_time, %s)
             WHERE scan_id=%s"""
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (end_time, status, total, passed, 
                            failed, error_msg, end_time, scan_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Save task end error: {e}")
```

## ⚠️ Pitfall: save_task_end 必须在 finally 块中

Flask进程可能随时被kill（用户重启、代码更新等）。如果 `save_task_end` 不在 `finally` 块中，任务会永远停在 `running` 状态。

```python
def run_scan(filters, task_name=""):
    scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    start_time = datetime.now()
    
    conn = get_db()
    if conn:
        save_task_start(conn, scan_id, start_time, filters, task_name)
    
    try:
        # ... scanning logic ...
    except Exception as e:
        logger.error(f"扫描异常: {e}")
    finally:
        end_time = datetime.now()
        status = "completed" if SCAN_STATE["running"] else "cancelled"
        
        # ⚠️ 重新获取连接！不要复用 try 块的 conn
        try:
            conn_end = get_db()
            if conn_end:
                save_task_end(conn_end, scan_id, end_time, status, total, passed, failed)
                conn_end.close()
                logger.info(f"📝 任务状态已更新为 {status}: {scan_id}")
            else:
                logger.error("无法获取数据库连接来更新任务状态!")
        except Exception as ex:
            logger.error(f"记录任务完成失败: {ex}", exc_info=True)
        
        # 关闭原始连接
        if conn:
            try:
                conn.close()
            except:
                pass
```

## ⚠️ Pitfall: finally 块中复用 conn 导致任务永远 running（2026-06-16）

**症状**：扫描完成后，任务历史仍然显示 `running` 状态。

**根因**：`finally` 块中复用了 `try` 块开头获取的 `conn` 对象。扫描过程耗时数分钟，期间 MySQL 连接可能因 `wait_timeout`（默认8小时）或网络波动断开。`save_task_end(conn, ...)` 静默失败（被 `except` 吞掉），任务状态永远不更新。

**修复**：在 `finally` 块中 **重新获取数据库连接**，不复用 `try` 块的 `conn`：

```python
# ❌ 错误：复用可能已断开的连接
finally:
    if conn:
        save_task_end(conn, scan_id, ...)  # conn 可能已断开！
        conn.close()

# ✅ 正确：重新获取连接
finally:
    try:
        conn_end = get_db()  # 新鲜连接
        if conn_end:
            save_task_end(conn_end, scan_id, ...)
            conn_end.close()
    except Exception as ex:
        logger.error(f"记录任务完成失败: {ex}", exc_info=True)
    
    if conn:
        try:
            conn.close()
        except:
            pass
```

**为什么 save_task_end 静默失败**：函数内部有 `try/except` 捕获异常并 `logger.error()`，但不会 re-raise。如果 logger 本身也有问题（如日志缓冲未刷新），错误可能完全看不到。

**诊断**：检查日志中是否有 `"记录任务完成失败"` 或 `"Save task end error"` 字样。

## 双版本扫描的任务记录

双版本扫描需要记录两条任务（`_old` 和 `_new`）：
```python
save_task_start(conn, scan_id_old, start_time, filters, f"{task_name}(老版本)")
save_task_start(conn, scan_id_new, start_time, filters, f"{task_name}(新版本)")

# finally块中
save_task_end(conn, scan_id_old, datetime.now(), "completed", total, passed_old, 0)
save_task_end(conn, scan_id_new, datetime.now(), "completed", total, passed_new, 0)
```

## API Endpoint Pattern

```python
@app.route("/api/task_history")
def api_task_history():
    days = int(request.args.get("days", 30))
    limit = int(request.args.get("limit", 50))
    status = request.args.get("status", "")
    
    if status:
        cur.execute("""SELECT * FROM scan_task_history 
                      WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                        AND status = %s
                      ORDER BY start_time DESC LIMIT %s""", (days, status, limit))
    else:
        cur.execute("""SELECT * FROM scan_task_history 
                      WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                      ORDER BY start_time DESC LIMIT %s""", (days, limit))
```

## Status Values

- `running` - Scan in progress
- `completed` - Finished successfully
- `failed` - Error occurred (check error_message)
- `cancelled` - User stopped scan
- `timeout` - Auto-marked by stale task cleanup (>30min with no progress)

## ⚠️ Pitfall: Stale Tasks After Flask Restart

Even with `finally` blocks, tasks can get stuck as `running` forever if:
- Flask process is killed externally (SIGKILL, OOM, `kill -9`)
- Server crashes or reboots unexpectedly
- Process is terminated during code deployment

**Symptoms**: `scan_task_history` shows tasks with `status='running'` for hours/days, but `total_stocks=0` and `passed_count=0`.

**Fix**: Add `_cleanup_stale_tasks()` that runs **before** starting any new scan:

```python
def _cleanup_stale_tasks():
    """Clean up tasks stuck in 'running' for >30 minutes"""
    try:
        conn = get_db()
        if conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE scan_task_history 
                    SET status = 'timeout', 
                        error_message = '任务超时自动标记',
                        end_time = NOW()
                    WHERE status = 'running' 
                    AND TIMESTAMPDIFF(MINUTE, created_at, NOW()) > 30
                """)
                affected = cur.rowcount
                conn.commit()
                if affected > 0:
                    logger.info(f"🧹 清理了 {affected} 个超时任务")
            conn.close()
    except Exception as e:
        logger.warning(f"清理超时任务失败: {e}")

def run_scan(filters, task_name=""):
    # Always clean stale tasks first
    _cleanup_stale_tasks()
    # ... rest of scan logic
```

**Manual cleanup** (if needed):
```sql
UPDATE scan_task_history 
SET status = 'timeout', error_message = '手动清理', end_time = NOW()
WHERE status = 'running' 
AND TIMESTAMPDIFF(MINUTE, created_at, NOW()) > 30;
```

## Database Query Gotchas

When querying `scan_task_history` directly:
- **Column name**: `total_stocks` (NOT `total_analyzed`)
- **DB config key**: `MYSQL_CONFIG` (NOT `DB_CONFIG`)
- **MySQL driver**: Use `pymysql` (not `mysql.connector`)
  ```python
  import pymysql
  from config import MYSQL_CONFIG
  conn = pymysql.connect(**MYSQL_CONFIG)
  cursor = conn.cursor(pymysql.cursors.DictCursor)
  ```
