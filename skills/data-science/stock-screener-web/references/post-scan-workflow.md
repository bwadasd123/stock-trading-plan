# Post-Scan Workflow: Interpreting Results & Making Decisions

## Overview
After scanner produces results, there's a structured workflow for validating signals and executing trades. This is for the boss's investment decision-making support.

## Scanner Output Structure
Each result in `stock_scan_results` contains:
- **Stock info**: ts_code, stock_name, latest_price, change_pct
- **Technical indicators**: rsi14, cci20, macd_gold, ma5/10/20
- **Volume metrics**: volume_ratio, turnover
- **Market cap**: circ_market_cap (in 亿)
- **Timing**: data_date, scan_time

## Post-Scan Validation Checklist

### Step 1: Confirm Signal Quality
1. **Check sector fund flow** — Is the stock's sector seeing net inflow?
2. **Check main capital direction** — Are institutions buying?
3. **Check technical breakout** — Is price above key resistance?
4. **Check volume confirmation** — Is the move supported by volume?

### Step 2: Risk Assessment
| Factor | Low Risk | Medium Risk | High Risk |
|--------|----------|-------------|-----------|
| RSI | 70-75 | 75-80 | >80 |
| Volume ratio | 1.5-3x | 3-5x | >5x (可能异常) |
| Market cap | >100亿 | 50-100亿 | <50亿 |
| Sector trend | 资金流入 | 平稳 | 资金流出 |

### Step 3: Position Sizing (for 3万本金)
- **Single stock max**: 20% of capital (6000元)
- **Total positions**: 2-3 stocks max
- **Cash reserve**: Keep 30% cash (9000元)
- **Test amount**: Start with 1万 to validate strategy

**⚠️ Detailed single-stock strategy**: See `scanner-trading-plan` skill for complete 3万本金单股操作方案，包括RSI与持仓时间对照表、每日操作流程、收益预期等。

### Step 4: Entry Strategy
1. **Don't chase** — If stock already up >5% on scan day, wait for pullback
2. **Split entry** — Buy in 2-3 batches, not all at once
3. **Set alerts** — Monitor key price levels before entering
4. **Confirm volume** — Rising price + rising volume = more reliable

### Step 5: Exit Strategy
- **Stop loss**: -8% from entry price
- **Take profit 1**: +15% (sell half)
- **Take profit 2**: +30% (sell remaining)
- **Trailing stop**: After +10%, move stop to breakeven

## Querying Scan Results for Analysis

```sql
-- Latest scan results with all indicators
SELECT ts_code, stock_name, latest_price, change_pct, 
       volume_ratio, rsi14, cci20, macd_gold, circ_market_cap, data_date
FROM stock_scan_results 
WHERE data_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
ORDER BY data_date DESC, change_pct DESC;

-- Check scan task history for scan frequency
SELECT scan_id, task_name, status, start_time, total_stocks, 
       passed_count, filters_json
FROM scan_task_history 
WHERE status = 'completed'
ORDER BY start_time DESC 
LIMIT 10;

-- Track a specific stock across scans
SELECT s.ts_code, s.stock_name, s.latest_price, s.change_pct, 
       s.rsi14, s.macd_gold, t.start_time
FROM stock_scan_results s
JOIN scan_task_history t ON s.scan_id = t.scan_id
WHERE s.ts_code = '600162'
ORDER BY t.start_time DESC;
```

## Common Patterns in Scan Results

### 扫描行为特征
- **每天通常只有1只股票通过筛选**（筛选条件严格）
- 香江控股(600162)多次出现 = 强势信号
- 单次出现的股票需要更多验证

### 香江控股 (600162) Pattern
- Repeatedly appears in scans (multiple dates)
- High RSI (73-83) consistently
- High volume ratio (12-18x)
- MACD金叉 maintained
- **Lesson**: Persistent signals across multiple scans = stronger conviction

### 山东玻纤 (605006) Pattern
- Single scan appearance
- Moderate RSI (70.80)
- Normal volume ratio (2.57)
- **Lesson**: Single-scan signals need more validation

## Risk Warnings
1. **High RSI stocks** (>75) may face pullback — don't chase
2. **Systemic risk** — Scanner can't predict market-wide crashes
3. **Liquidity risk** — Small-cap stocks may have wide bid-ask spreads
4. **Overfitting** — Past scan success doesn't guarantee future results

## Integration with Web Dashboard
The web dashboard at `http://localhost:8080` provides:
- Real-time scan progress (SSE)
- Scan history with version filtering
- Individual stock analysis page
- Sector fund flow analysis
- All 7 indicators displayed on detail page
