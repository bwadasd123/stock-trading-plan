# 东财API字段映射

## push2delay 实时行情
URL: `http://push2delay.eastmoney.com/api/qt/stock/get`

### 关键字段（⚠️ 有陷阱！）
| 字段 | 含义 | 说明 |
|------|------|------|
| f43 | 现价 | 需要 /100 |
| f44 | 最高 | 需要 /100 |
| f45 | 最低 | 需要 /100 |
| f46 | 开盘 | 需要 /100 |
| f47 | 成交量 | 直接使用 |
| f48 | 成交额 | |
| **f49** | **外盘** | ⚠️ 不是f162！ |
| f60 | 昨收 | 需要 /100 |
| **f161** | **内盘** | |
| f170 | 涨跌幅 | 需要 /100 |
| f85 | 流通股本 | |

### 手动计算字段
```python
# 振幅 = (最高 - 最低) / 昨收 * 100
amplitude = (high - low) / yesterday * 100

# 换手率 = 成交量 * 100 / 流通股本 * 100
turnover = volume * 100 / circ_shares * 100

# 外盘比例
outer_ratio = outer / (outer + inner) * 100
```

## push2his K线数据
URL: `http://push2his.eastmoney.com/api/qt/stock/kline/get`

### 参数
- secid: 证券代码（如 0.002972）
- klt: K线周期（101=日线）
- fqt: 复权类型（1=前复权）
- lmt: 返回数量

### 返回字段
klines数组中每个元素格式：
```
日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
```

## RSI计算
```python
def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```
