# Scanner Filter Logic (7-Indicator System)

## User Requirement (2026-06-03)
Scanner must follow **exactly 7 indicators**, NO additional filters.
User: "严格按照我7个指标的逻辑"

## The 7 Indicators (from de3.py)
1. 流通市值≤200亿 (circ_market_cap)
2. MACD金叉 (macd_gold)
3. 股价>MA20 (price > ma20)
4. 量比≥1.5 (vol_ratio)
5. 换手率>10% (turnover)
6. CCI>0 (cci)
7. RSI>70 (rsi)

## First Round (Basic Filter) — scanner.py
Only TWO conditions:
1. **换手率 > 10%** (turnover threshold, configurable)
2. **流通市值 ≤ 200亿** (market cap threshold, configurable)

**DO NOT add** these filters (user explicitly removed):
- ~~涨幅 > 0~~ (change_pct > 0)
- ~~成交额 > 0.5亿~~ (amount threshold)
- ~~PE > 0~~ (exclude loss-making stocks)

## Second Round (Technical Indicators) — scanner.py
All 7 conditions checked here.

## Detail Page Scoring — scanner.js calculateScore()
Must use SAME 7 conditions as scanner:
- Display as "X/7 通过" (not scores)
- RSI>70 = "强势" (NOT "超买")
- CCI>0 = "多头" (NOT "超买")
- Returns `{ total, level, items, passCount }`

## Why this matters
- PE filter blocked 600162 (香江控股, PE=-124.36) despite passing all 7 technical conditions
- User's de3.py script has exactly these 7 conditions, no PE/amount/change filters
- Scanner must match de3.py logic precisely
- Detail page must match scanner logic precisely

## ⚠️ circ_cap=0 Bug (2026-06-04)

**Symptom**: 个股详情页分析600162时，显示"6/7 通过"，流通市值显示"不通过"。

**Root cause**: `/api/analyze` endpoint fetches `circ_cap` via direct `requests.get` to `push2.eastmoney.com/api/qt/stock/get`. In WSL/server environments, eastmoney blocks direct connections (returns connection reset/502). Result: `circ_cap=0`.

**JavaScript falsy bug**: `calculateScore()` in scanner.js:
```javascript
if (circCap && circCap <= 200)  // circCap=0 is falsy → fails!
```

**Fix**: 
1. `/api/analyze` must use `safe_get` from `anti_crawl` module (with proxy), same as kline data
2. Must import `from anti_crawl import safe_get as _safe_get, get_kline_headers`
3. Must have `import re` and `logger = logging.getLogger(__name__)` in api/scan.py

**Key pattern**: ALL eastmoney API requests (push2.eastmoney.com, push2his.eastmoney.com) require proxy in this environment. Direct connections fail silently.

## Files Modified (2026-06-03)
1. `services/scanner.py` - Removed PE>0, 涨幅>0, 成交额 filters from first round
2. `templates/index.html` - Removed UI elements for PE, 涨幅, 成交额
3. `static/js/scanner.js` - Hardcoded `r1_change_gt0: false`, `r1_pe_gt0: false`, `r1_amount: 0`
4. `static/js/scanner.js` - Updated `calculateScore()` to use 7 conditions
5. `api/scan.py` - Added `circ_cap` to `/api/analyze` response

## de3.py Reference
- **Windows路径**: `C:\Users\Administrator\Downloads\Telegram Desktop\de3.py`
- **WSL路径**: `/mnt/c/Users/Administrator/Downloads/Telegram Desktop/de3.py`
- Standalone test script for 7-indicator logic
- Uses same东方财富API endpoints
- Can be used to verify scanner results
- **重要**：所有指标计算必须与 de3.py 保持一致