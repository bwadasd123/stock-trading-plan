# 手工计算RSI（API限流时兜底）

当 `push2his` K线API返回空或超时时，从已有的K线数据手工计算RSI。

## 快速计算（Python一行）

```python
# 前提：已有近14+根K线的收盘价列表 closes = [42.58, 41.47, ...]

closes = [42.58, 41.47, 39.91, 36.99, 38.0, 35.91, 37.64, 37.55, 36.17, 35.42, 33.38, 34.3, 32.66, 30.99]
deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
gains = [d for d in deltas if d>0]
losses = [-d for d in deltas if d<0]
avg_gain = sum(gains)/14
avg_loss = sum(losses)/14
rsi = 100 - 100/(1 + avg_gain/avg_loss) if avg_loss > 0 else 100
print(f"RSI={rsi:.1f}")
```

## 数据来源

东财push2his K线响应格式：
```
"klines": ["2026-07-09,33.38,34.29,34.38,31.90,235771,...", ...]
# 字段: 日期,开盘,收盘,最高,最低,成交量,成交额
```

提取收盘价：`close = float(kline.split(',')[2])`

## 补充指标

```python
# 布林下轨（近似）
ma20 = sum(closes)/len(closes)
std = (sum((c-ma20)**2 for c in closes)/len(closes))**0.5
bb_low = ma20 - 2*std

# 回调幅度
high = max(closes)
low = min(closes)
pullback_pct = (high-low)/high*100
```
