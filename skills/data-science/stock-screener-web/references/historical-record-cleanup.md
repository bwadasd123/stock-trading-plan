## 历史扫描记录清理 (2026-06-09)

### 问题
6月之前的扫描记录（共199条）都是基于 `smplmt=460` 的采样数据计算的，指标值不准确。

### 处理方式
用户要求删除当天（6月9日）修复前的扫描记录：
```sql
-- 删除指定扫描批次的结果
DELETE FROM stock_scan_results WHERE scan_id = '20260609_204815';
DELETE FROM scan_task_history WHERE scan_id = '20260609_204815';
```

### 注意事项
- 6月之前的历史记录保留（用户未要求删除）
- 修复后的扫描结果基于完整日线数据，指标更准确
- 新旧扫描结果不可直接对比（数据源不同）

---

## de3.py 完整指标公式参考

用户提供的参考实现位于：`/mnt/c/Users/Administrator/Downloads/Telegram Desktop/de3.py`

### RSI(14) - SMA方式
```python
def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

### MACD(12,26,9) - 标准EMA
```python
def calculate_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    bar = 2 * (dif - dea)
    return dif, dea, bar
```

### CCI(20) - 标准公式
```python
def calculate_cci(high, low, close, window=20):
    tp = (high + low + close) / 3
    ma = tp.rolling(window=window).mean()
    md = tp.rolling(window=window).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    cci = (tp - ma) / (0.015 * md)
    return cci
```

### MACD金叉判断
```python
def judge_macd_gold_cross(dif, dea):
    if len(dif) < 2 or len(dea) < 2:
        return False
    return (dif.iloc[-1] > dea.iloc[-1]) and (dif.iloc[-2] <= dea.iloc[-2])
```

### 量比（今日/昨日）
```python
vol_ratio = float(v.iloc[-1] / v.iloc[-2]) if v.iloc[-2] > 0 else 0
```

### 7个筛选条件（de3.py定义）
```python
conditions = [
    ("流通市值≤200亿", circ_market_cap <= 200),
    ("MACD金叉", is_macd_gold_cross),
    ("股价在20日均线上方", price_ma20_diff > 0),
    ("成交量放大≥1.5倍", volume_ratio >= 1.5),
    ("换手率>10%", latest_turnover > 10.0),
    ("CCI>0", latest_cci > 0),
    ("RSI>70", latest_rsi > 70)
]
```
