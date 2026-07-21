# ETF Price Scaling from East Money API

## Problem
ETFs (like 513100 纳指ETF, 518880 黄金ETF) return prices that need different scaling than stocks.

## Solution
Use `fltt=1` and divide by **1000** (not 100).

```python
params = {
    'secid': '1.513100',
    'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60,f170',
    'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
    'fltt': 1,
}
# ...
price = d.get('f43', 0) / 1000      # e.g. 2118 → 2.118
pre_close = d.get('f60', 0) / 1000  # e.g. 2205 → 2.205
chg_pct = d.get('f170', 0) / 100    # e.g. -395 → -3.95%
```

## Verified Examples
- 513100 纳指ETF: f43=2118 → 2.118 元
- 518880 黄金ETF: f43=8949 → 8.949 元

## Note
Stocks use fltt=1 ÷ 100, but ETFs use fltt=1 ÷ 1000. The difference is because ETF prices are in the 1-12 元 range while stocks are in the 5-500 元 range. Always verify with a known price.
