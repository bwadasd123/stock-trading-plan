# Daily Digest Caching (今日看点缓存)

## Overview

The daily digest (今日看点) supports caching data to MySQL for offline viewing after market close. User requirement: "盘后数据不会变" (post-market data won't change), so cached data is valid for historical viewing.

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS daily_digest_cache (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    digest_date DATE NOT NULL COMMENT '日期',
    digest_data JSON NOT NULL COMMENT '今日看点完整数据(JSON)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date (digest_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='今日看点缓存'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/daily/digest` | GET | Load today's digest (cached first, then real-time) |
| `/api/daily/digest?force=true` | GET | Force real-time fetch (bypass cache) |
| `/api/daily/digest?date=2026-06-01` | GET | Load specific date's cached data |
| `/api/daily/save` | POST | Save current digest to database |
| `/api/daily/list` | GET | List saved digest dates (returns `["2026-06-01", ...]`) |

## Backend Implementation

### Load Logic (Cache-First with Date Support)

```python
@daily_bp.route("/api/daily/digest")
def api_daily_digest():
    from flask import request
    force_refresh = request.args.get("force", "false").lower() == "true"
    date = request.args.get("date")  # Support specific date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # If specific date requested, load from cache
    if date:
        cached = load_daily_digest(date)
        if cached:
            cached["from_cache"] = True
            return jsonify(cached)
        return jsonify({"error": f"没有 {date} 的缓存数据"})
    
    # If not force refresh, try cache for today
    if not force_refresh:
        cached = load_daily_digest(today)
        if cached:
            cached["from_cache"] = True
            return jsonify(cached)
    
    # Real-time fetch...
```

### Save Endpoint

```python
@daily_bp.route("/api/daily/save", methods=["POST"])
def api_daily_save():
    from flask import request
    data = request.json
    if not data:
        return jsonify({"ok": False, "error": "没有数据"})
    
    result = save_daily_digest(data)
    return jsonify({"ok": result})
```

### List Endpoint

```python
@daily_bp.route("/api/daily/list")
def api_daily_list():
    from models.database import get_db
    conn = get_db()
    if not conn:
        return jsonify([])
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT digest_date FROM daily_digest_cache ORDER BY digest_date DESC LIMIT 30")
            rows = cur.fetchall()
        return jsonify([r["digest_date"].strftime("%Y-%m-%d") if hasattr(r["digest_date"], 'strftime') else str(r["digest_date"]) for r in rows])
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()
```

### Helper Functions (models/database.py)

```python
import json
from datetime import datetime

def save_daily_digest(data):
    """Save daily digest to database"""
    conn = get_db()
    if not conn:
        return False
    
    try:
        digest_date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        with conn.cursor() as cur:
            sql = """INSERT INTO daily_digest_cache (digest_date, digest_data)
                     VALUES (%s, %s)
                     ON DUPLICATE KEY UPDATE digest_data=VALUES(digest_data), updated_at=NOW()"""
            cur.execute(sql, (digest_date, json.dumps(data, ensure_ascii=False)))
        conn.commit()
        logger.info(f"💾 保存今日看点 {digest_date}")
        return True
    except Exception as e:
        logger.error(f"保存今日看点失败: {e}")
        return False
    finally:
        conn.close()


def load_daily_digest(date=None):
    """Load daily digest from database"""
    conn = get_db()
    if not conn:
        return None
    
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        with conn.cursor() as cur:
            cur.execute("SELECT digest_data FROM daily_digest_cache WHERE digest_date = %s", (date,))
            row = cur.fetchone()
        if row:
            return json.loads(row["digest_data"])
        return None
    except Exception as e:
        logger.error(f"加载今日看点失败: {e}")
        return None
    finally:
        conn.close()
```

**CRITICAL**: Both `import json` and `from datetime import datetime` MUST be at the TOP of `models/database.py`, not at the end. Functions reference modules from global scope at call time.

## Frontend Implementation

### Buttons (in renderDailyDigest)

```javascript
html += '<button class="btn-refresh" onclick="loadDailyDigest(true)" style="margin-left:8px">↻ 刷新</button>';
html += '<button class="btn-save" onclick="saveDailyDigest()" style="margin-left:8px;padding:6px 12px;background:#4CAF50;color:white;border:none;border-radius:4px;cursor:pointer">💾 保存</button>';
html += '<button class="btn-history" onclick="toggleDailyHistory()" style="margin-left:8px;padding:6px 12px;background:#2196F3;color:white;border:none;border-radius:4px;cursor:pointer">📋 历史</button>';
```

### History List Container

```javascript
// After buttons, before indices
html += '<div id="daily-history-list" style="display:none;margin:8px 0;padding:8px;background:var(--bg-secondary);border-radius:8px"></div>';
```

### Cache Badge

```javascript
if (data.from_cache) {
  html += '<span style="color:#4CAF50;font-size:12px;margin-left:8px">📦 已缓存</span>';
}
```

### Load Function (Cache-First)

```javascript
async function loadDailyDigest(forceRefresh = false) {
  const container = document.getElementById('daily-content');
  if (!container) return;
  
  // Check in-memory cache first (but skip if it's from DB cache)
  if (!forceRefresh && tabDataCache['daily'] && !tabDataCache['daily'].from_cache) {
    dailyData = tabDataCache['daily'];
    renderDailyDigest(dailyData);
    return;
  }
  
  // Show loading if no data
  if (!dailyData) {
    container.innerHTML = '<div class="loading-state">加载中...</div>';
  }
  
  try {
    const url = forceRefresh ? '/api/daily/digest?force=true' : '/api/daily/digest';
    const r = await fetch(url);
    const data = await r.json();
    dailyData = data;
    tabDataCache['daily'] = data;
    renderDailyDigest(data);
  } catch(e) {
    if (!dailyData) {
      container.innerHTML = '<div class="empty-state">加载失败</div>';
    }
  }
}
```

### Save Function

```javascript
async function saveDailyDigest() {
  if (!dailyData) {
    alert('没有数据可保存，请先刷新今日看点');
    return;
  }
  
  try {
    const r = await fetch('/api/daily/save', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(dailyData)
    });
    const result = await r.json();
    if (result.ok) {
      alert('✅ 今日看点已保存！');
    } else {
      alert('❌ 保存失败: ' + (result.error || '未知错误'));
    }
  } catch(e) {
    alert('❌ 保存失败: ' + e.message);
  }
}
```

### History Toggle Function

```javascript
async function toggleDailyHistory() {
  const container = document.getElementById('daily-history-list');
  if (!container) return;
  
  if (container.style.display === 'none') {
    container.style.display = 'block';
    container.innerHTML = '<div style="color:#888">加载中...</div>';
    
    const dates = await loadDailyHistory();
    if (dates.length === 0) {
      container.innerHTML = '<div style="color:#888">暂无保存记录</div>';
      return;
    }
    
    let html = '<div style="display:flex;flex-wrap:wrap;gap:8px">';
    dates.forEach(d => {
      html += `<button onclick="loadDailyByDate('${d}')" style="padding:6px 12px;background:var(--bg-tertiary);border:1px solid var(--border);border-radius:4px;cursor:pointer;color:var(--text)">${d}</button>`;
    });
    html += '</div>';
    container.innerHTML = html;
  } else {
    container.style.display = 'none';
  }
}
```

### Load by Date Function

```javascript
async function loadDailyByDate(date) {
  const container = document.getElementById('daily-content');
  if (!container) return;
  
  container.innerHTML = '<div class="loading-state">加载中...</div>';
  
  try {
    const r = await fetch(`/api/daily/digest?date=${date}`);
    const data = await r.json();
    if (data.error) {
      container.innerHTML = `<div class="empty-state">${data.error}</div>`;
      return;
    }
    dailyData = data;
    renderDailyDigest(data);
  } catch(e) {
    container.innerHTML = '<div class="empty-state">加载失败</div>';
  }
}
```

## Northbound Flow API Notes

The East Money northbound flow API (`kamt.rtmin/get`) returns zeros after market hours (15:00). This is normal behavior — the API only has data during trading hours. The daily digest will show `0` for northbound flow when viewed after market close.
