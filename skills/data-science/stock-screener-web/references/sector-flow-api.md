# Sector Fund Flow Implementation

## Eastmoney Sector Flow API

### Endpoint
```
http://push2delay.eastmoney.com/api/qt/clist/get
```
⚠️ **必须用 `push2delay`**，不能用 `push2`（返回502）或 `push2his`（该端点用于K线）。

### Parameters
- `fs`: Sector type filter
  - `m:90+t:2` = Industry sectors (行业板块)
  - `m:90+t:3` = Concept sectors (概念板块)
- `fid`: Sort field (e.g., `f62` for main net inflow)
- `pz`: Page size (max 50 recommended)
- `fltt`: 1=整数(需/100), 2=小数(直接用)。**代码用fltt=1**
- `fields`: Comma-separated field codes
- `cb`: jQuery callback (JSONP wrapping)
- `ut`: Anti-crawl token (from `random_choose_ut()`)

### Response Format
**JSONP** (not pure JSON). Code must strip jQuery wrapper:
```python
text = resp.text
m = re.search(r'\((\{.*\})\)', text)
if m:
    text = m.group(1)
data = json.loads(text)
```

### Field Mapping (CRITICAL - verified 2026-05-29, updated 2026-06-12)

| Field | Description | Raw (fltt=1) | After service processing |
|-------|-------------|-------------|--------------------------|
| f12 | Sector code | e.g., BK0475 | `sector_code` |
| f14 | Sector name | e.g., 通信 | `sector_name` |
| f3 | Change % | Integer, /100 needed | `change_pct` (already /100) |
| f62 | Main net inflow | In yuan (元) | `main_net_inflow` (in 万元, /10000) |
| f184 | Main net inflow % | Integer, /100 needed | `main_net_inflow_pct` |
| f204 | Lead stock name | | `lead_stock_name` |
| f205 | Lead stock code | | `lead_stock_code` |
| f206 | Lead stock change % | Integer, /100 needed | `lead_stock_pct` |
| f207 | Lag stock name | | `lag_stock_name` |
| f208 | Lag stock code | | `lag_stock_code` |
| f209 | Lag stock change % | Integer, /100 needed | `lag_stock_pct` |

### Key Implementation Details

1. **fltt=1 returns integers** - all percentage fields need /100
2. **f62 is in yuan** - service divides by 10000 to store as 万元
3. **Response is JSONP** - must strip jQuery callback wrapper before JSON.parse
4. **sort_outflow parameter** was renamed to `ascending` in the unified API
5. **Database stores in 万元** - `main_net_inflow` column is in 万元, divide by 10000 to get 亿
6. **Lead stock codes may be empty** - `f205`/`f208` sometimes return empty string

## 实时数据函数

```python
from services.sector_flow import fetch_sector_flow

items = fetch_sector_flow(sector_type="industry", sort_field="f62", page_size=50, ascending=False)
```
- `sector_type`: "industry" (行业) 或 "concept" (概念)
- `sort_field`: "f62"=主力净流入, "f184"=主力净占比
- `ascending`: True=升序（流出最大在前）, False=降序（流入最大在前）
- 返回: list of dicts with keys: `sector_code`, `sector_name`, `change_pct`, `main_net_inflow`(万元), `lead_stock_name`, `lead_stock_code`, etc.

**注意**: 函数名是 `fetch_sector_flow`，不是 `get_sector_flow`、`get_sector_flow_data` 或其他变体。

### Usage Example (command line)
```bash
cd /home/jmy/stock-screener
/home/jmy/.hermes/hermes-agent/venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from services.sector_flow import fetch_sector_flow
items = fetch_sector_flow('industry', sort_field='f62', page_size=10, ascending=False)
for i, item in enumerate(items[:10], 1):
    print(f\"{i}. {item['sector_name']}: {item['main_net_inflow']/10000:.2f}亿 ({item['change_pct']:.2f}%)\")
"
```

### Proxy Note
代理池可能返回407认证失败，`safe_get` 会自动降级到直连。板块列表数据直连可用，不影响结果。

---

## Database Caching

Sector flow data is saved to `sector_flow` table after each fetch.
For report pages, prefer reading from DB cache instead of live API (faster, avoids proxy timeout).

```python
# 读取缓存（推荐用于报告页面）
cur.execute("""
    SELECT sector_name, sector_code, main_net_inflow, change_pct
    FROM sector_flow 
    WHERE sector_type = 'industry' 
    ORDER BY fetch_time DESC, main_net_inflow DESC
    LIMIT 50
""")
# main_net_inflow 单位是万元，需要 /10000 转亿
```

## 板块历史趋势图 (ECharts Modal)

Added 2026-06-08. Shows sector fund flow history as line charts in a modal.

### API Endpoint
```
GET /api/sector/flow/history?type=industry&days=3&limit=500
```
Returns `{ type, flows: [{sector_name, fetch_time, main_net_inflow, ...}], count }`.

### Frontend Implementation (`sector.js`)

Functions: `showSectorHistory()` → opens modal, `loadSectorHistory()` → fetches data + renders ECharts.

Key pattern:
- Modal renders into `#modal-container` (shared modal container)
- Uses `echarts.init(container)` (ECharts already loaded via CDN in index.html)
- Supports filtering by days (1/3/7) and individual sector selection
- Multi-line chart: top 8 sectors by default, or single sector if selected
- Y-axis uses `formatWan()` for 万/亿 display
- `connectNulls: true` for sparse data points

### Trigger Button
Added to sector page controls: `<button class="btn btn-secondary" onclick="showSectorHistory()">📈 历史趋势</button>`

### Pitfall
- ECharts must be disposed on modal close: `sectorChart.dispose()` to prevent memory leaks
- `window.addEventListener('resize', ...)` for responsive chart — but only add once per modal open

---

## Frontend Display Rules

### 板块资金流向显示规范（用户确认 2026-05-29）

**流出显示格式**: `↓ 249.59亿`（正数+箭头），NEVER `-249.59亿` 或 `249.59亿流出`

```javascript
// ✅ 正确
`↓ ${Math.abs(amount).toFixed(2)}亿`
`+${amount.toFixed(2)}亿`  // 流入

// ❌ 错误
`-${amount.toFixed(2)}亿`  // 不要负号
`${amount.toFixed(2)}亿流出`  // 不要"流出"后缀
```

### TOP10 排序显示

- 用户选择"流入"时：只显示 TOP10 流入板块
- 用户选择"流出"时：只显示 TOP10 流出板块
- **不要同时显示两个方向**（简化UX）

### 数据来源标记

板块流向页面显示的是**实时数据**（每次刷新从API获取）
报告页面显示的是**缓存数据**（从数据库读取，避免超时）
