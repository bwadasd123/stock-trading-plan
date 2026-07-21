# Stock Detail Page Pattern

## Overview
Individual stock analysis page with comprehensive technical analysis and scoring system.

## Layout Structure

### 1. Header Section
- Large stock name and code display
- Price with change amount and percentage (color-coded: red=up, green=down)
- Meta info: high, low, open, previous close

### 2. Trading Data Cards
4-column grid showing:
- 成交量 (Volume) - in 万手
- 成交额 (Amount) - in 亿
- 换手率 (Turnover) - percentage
- 量比 (Volume Ratio) - ratio value

### 3. Technical Indicators Panel
3-column layout:
- **动量指标**: RSI(14), CCI(20)
- **MACD指标**: DIF, DEA, MACD柱, 金叉
- **均线系统**: MA5, MA10, MA20

Each indicator shows:
- Name
- Value (color-coded)
- Description (e.g., "超买", "超卖", "正常")

### 4. Comprehensive Scoring System
Score calculation based on:
- RSI: 超卖 +20, 正常 +10, 超买 +0
- MACD金叉: +25
- CCI>0: +15
- 量比≥1.5: +15
- 均线多头: +15

Score levels:
- 80+: 强势 (strong) - green
- 60-79: 中等 (medium) - blue
- 40-59: 中性 (neutral) - orange
- <40: 弱势 (weak) - red

### 5. K-Line Chart
- Candlestick chart with MA lines
- Volume bars
- MACD indicator (DIF, DEA, MACD bar)

### 6. Historical Data Table
- Last 30 K-lines
- Columns: Date, Open, High, Low, Close, Change%, Turnover%

## CSS Classes

```css
.stock-header { background, border-radius, padding }
.stock-title { display: flex, justify-content: space-between }
.stock-code { font-size: 14px, color: var(--text-secondary) }
.price-main { font-size: 28px, font-weight: 700 }
.price-change { font-size: 16px }
.stock-meta { display: flex, gap: 24px }

.detail-cards { display: grid; grid-template-columns: repeat(4, 1fr) }
.detail-card { background, border-radius, padding, text-align: center }
.card-value { font-size: 20px, font-weight: 600 }
.card-label { font-size: 12px, color: var(--text-secondary) }

.indicators-panel { display: grid; grid-template-columns: repeat(3, 1fr) }
.indicator-group { background, border-radius, padding }
.indicator-row { display: flex, justify-content: space-between }

.score-panel { background, border-radius, padding }
.score-header { display: flex, justify-content: space-between }
.score-badge { font-size: 24px, font-weight: 700, padding: 8px 20px }
.score-details { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) }
.score-item { display: flex, align-items: center, gap: 8px }
.score-item.pass { border-left: 3px solid var(--accent-green) }
.score-item.fail { border-left: 3px solid var(--accent-red) }
```

## API Endpoint

```
GET /api/analyze?code=CODE&period=PERIOD&limit=LIMIT
```

### ⚠️ 流通市值获取陷阱

`/api/analyze` 获取流通市值（circ_cap）时**必须使用 `safe_get` 走代理**，不能直连：
- 东财 `push2.eastmoney.com` 屏蔽了服务器直连IP
- 直连会返回 `RemoteDisconnected` 错误，导致 `circ_cap=0`
- 前端 `calculateScore` 中 `if (circCap && circCap <= 200)` 会把0判定为失败

**正确写法**:
```python
from anti_crawl import safe_get as _safe_get, get_kline_headers
resp = _safe_get(url, headers=get_kline_headers(code), params=params, timeout=10)
```

**错误写法**（会导致circ_cap永远为0）:
```python
import requests as _req
sess = _req.Session()
sess.trust_env = False
resp = sess.get(url, headers=headers, params=params, timeout=5)  # 直连被拒
```

同时注意该接口返回**纯JSON**（非JSONP），解析时需兼容（见 eastmoney-api-quirks.md）。

Response:
```json
{
  "name": "Stock Name",
  "code": "Stock Code",
  "klines": [...],
  "indicators": {
    "ma5": 10.5,
    "ma10": 10.2,
    "ma20": 10.0,
    "rsi": 65.5,
    "dif": 0.05,
    "dea": 0.03,
    "bar": 0.04,
    "macd_gold": false,
    "cci": 50.2,
    "vol_ratio": 1.2
  },
  "quote": {
    "name": "Stock Name",
    "price": 10.5,
    "pre_close": 10.2,
    "high": 10.8,
    "low": 10.1,
    "open": 10.3,
    "volume": 1000000,
    "amount": 10500000
  }
}
```

## ⚠️ K线图 ECharts Sizing（2026-06-16）

3-panel echarts (K线 + 成交量 + MACD) 需要足够高度，480px 太窄导致蜡烛图挤在一起。

**推荐配置：**
- 容器高度：**700px**（`#chart{width:100%;height:700px}`）
- K线主图：**52%**（`{left:'8%',right:'3%',top:'8%',height:'52%'}`）
- 成交量：**12%**（`{left:'8%',right:'3%',top:'65%',height:'12%'}`）
- MACD：**12%**（`{left:'8%',right:'3%',top:'82%',height:'12%'}`）

**为什么不能更矮：** 三个子图（K线+成交量+MACD）各需要最小高度才能看清蜡烛和指标线。700px 是三图并存的最低实用高度。

## Helper Functions

```javascript
// Create metric card
function createCard(label, value, cls) {
  return `<div class="detail-card">
    <div class="card-value ${cls || ''}">${value}</div>
    <div class="card-label">${label}</div>
  </div>`;
}

// Create indicator row
function createIndicator(name, value, desc, cls) {
  return `<div class="indicator-row">
    <span class="ind-name">${name}</span>
    <span class="ind-value ${cls || ''}">${value !== undefined && value !== null ? value : '-'}</span>
    ${desc ? `<span class="ind-desc ${cls || ''}">${desc}</span>` : ''}
  </div>`;
}

// Calculate comprehensive score
function calculateScore(ind, price) {
  // See SKILL.md for full implementation
  return { total, level, items };
}
```
