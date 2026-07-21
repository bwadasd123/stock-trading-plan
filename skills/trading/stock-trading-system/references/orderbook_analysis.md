# 盘口深度分析

## 核心指标

### 1. 外盘/内盘
- **外盘（f49）**：主动性买盘，以卖方报价成交
- **内盘（f161）**：主动性卖盘，以买方报价成交
- **判断**：外盘>内盘=买方强势，内盘>外盘=卖方强势

```python
outer_ratio = outer / (outer + inner) * 100
if outer_ratio > 60:
    判断 = "买方强势 ✅"
elif outer_ratio < 40:
    判断 = "卖方强势 ⚠️"
else:
    判断 = "买卖均衡"
```

### 2. 振幅
```python
amplitude = (high - low) / yesterday * 100
```
- <2%：窄幅震荡
- 2-5%：正常波动
- >5%：大幅波动

### 3. 换手率
```python
turnover = volume * 100 / circ_shares * 100
```
- <3%：低迷
- 3-7%：正常
- 7-15%：活跃
- >15%：异常活跃

### 4. 量比
- 需要从K线历史数据计算
- API不直接返回
- 量比>3：放量
- 量比<0.7：缩量

## API字段映射（关键！）

```python
# 正确的字段映射
price = data["f43"] / 100      # 现价
high = data["f44"] / 100       # 最高
low = data["f45"] / 100        # 最低
yesterday = data["f60"] / 100  # 昨收
outer = data["f49"]            # 外盘（不是f162！）
inner = data["f161"]           # 内盘
volume = data["f47"]           # 成交量
circ_shares = data["f85"]      # 流通股本
change_pct = data["f170"] / 100  # 涨跌幅
```

## ⚠️ 常见错误

| 错误 | 正确 |
|------|------|
| f162 = 外盘 | f49 = 外盘 |
| f50/10 = 换手率 | volume*100/circ_shares |
| f52/100 = 振幅 | (high-low)/yesterday |
| f51 = 量比 | 需从K线计算 |
