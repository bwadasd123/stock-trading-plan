# Scan Filter Mapping: de3.py ↔ scanner.py

## Overview
The standalone `de3.py` script and the stock-screener's `services/scanner.py` implement the same 7-indicator screening logic. This reference maps between them.

## 7-Indicator Mapping

| # | Condition | de3.py config | scanner.py param | Notes |
|---|---|---|---|---|
| 1 | 流通市值≤200亿 | `CIRC_MARKET_CAP_MAX: 200` | `r1_cap_max: 200` | Round 1 filter |
| 2 | MACD金叉 | `judge_macd_gold_cross()` | `r2_macd: true` | Round 2 filter |
| 3 | 股价>MA20 | `price_ma20_diff > 0` | `r2_ma20: true` | Round 2 filter |
| 4 | 量比≥1.5倍 | `VOLUME_RATIO_THRESHOLD: 1.5` | `r2_vol_ratio: 1.5` | Round 2 filter |
| 5 | 换手率>10% | `TURNOVER_THRESHOLD: 10.0` | `r2_turnover: 10` | Round 1 or 2 |
| 6 | CCI>0 | `CCI_UPPER_THRESHOLD: 0` | `r2_cci: true` | Round 2 filter |
| 7 | RSI>70 | `RSI_UPPER_THRESHOLD: 70` | `r2_rsi: 70` | Round 2 filter |

## Key Differences

### ✅ FIXED (2026-06-03): Extra Round 1 Filters REMOVED
Previously scanner.py had extra Round 1 filters (涨幅>0, PE>0, 成交额>0.5亿) that de3.py didn't have. These caused 600162 (PE=-124.36) to be rejected despite passing all 7 technical indicators.

**Current state**: scanner.py now matches de3.py exactly. The extra filters are hardcoded off in scanner.js:
```javascript
r1_change_gt0: false,  // 已移除
r1_amount: 0,          // 已移除
r1_pe_gt0: false,      // 已移除
```

### Current Round 1 Filters (scanner.py)
Only TWO conditions (both configurable via UI):
1. **换手率 > 10%** (`r1_turnover`)
2. **流通市值 ≤ 200亿** (`r1_cap_max`)

### Data Sources
- **de3.py**: Fetches capital data (股本) via separate API call per stock, then K-line data
- **scanner.py**: Gets basic data from sector list API (f2/f3/f8/f20), K-line only for Round 2 stocks

### Calculation
- Both calculate indicators identically: MA20, MACD (DIF/DEA/BAR), RSI(14), CCI(20)
- Both compute volume ratio as `latest_vol / prev_vol`
- Both compute turnover from K-line data (f10 field)

### Round 1 vs Round 2
- **de3.py**: All 7 conditions checked after fetching all data (no Round 1 pre-filter)
- **scanner.py**: Split into two rounds for efficiency:
  - Round 1 (no K-line API calls): turnover threshold, circ_cap threshold
  - Round 2 (K-line API): RSI>70, MACD金叉, CCI>0, price>MA20, vol_ratio≥1.5, turnover>10%

## Usage
When user asks to run a scan with these 7 conditions, use these filter params:
```json
{
  "r1_cap_max": 200,
  "r2_rsi": 70,
  "r2_macd": true,
  "r2_cci": true,
  "r2_ma20": true,
  "r2_vol_ratio": 1.5,
  "r2_turnover": 10
}
```

## ⚠️ Dual Scan API Field Name Mismatch (2026-06-17)

**Problem**: Frontend and backend used different field names for the same filters.

**Frontend sends** (dual_scan.js):
```javascript
{
  r1_turnover: 10,      // 换手率
  r1_cap_max: 200,      // 流通市值
  r2_rsi: 70,           // RSI阈值
  r2_macd: true,        // MACD金叉
  r2_cci: true,         // CCI>0
  r2_ma20: true,        // 股价>MA20
  r2_vol_ratio: 1.5,    // 量比
  r2_turnover: 10       // 换手率(第二轮)
}
```

**Backend expected** (api/dual_scan.py - BEFORE fix):
```python
raw.get("f_turn1")    # ❌ Frontend sends r1_turnover
raw.get("turn1")      # ❌ Frontend sends r1_turnover
raw.get("f_cap")      # ❌ Frontend sends r1_cap_max
raw.get("cap")        # ❌ Frontend sends r1_cap_max
raw.get("f_rsi")      # ❌ Frontend sends r2_rsi
raw.get("rsi")        # ❌ Frontend sends r2_rsi
```

**Fix**: Changed api/dual_scan.py to use the same field names as frontend:
```python
if raw.get("r1_turnover"):
    filters["r1_turnover"] = float(raw["r1_turnover"])
if raw.get("r1_cap_max"):
    filters["r1_cap_max"] = float(raw["r1_cap_max"])
# ... etc
```

**Lesson**: Always verify frontend-backend field name alignment. The scanner expects `r1_*` and `r2_*` prefixed names.
