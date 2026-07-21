# 实时价格获取

## 获取单只股票最新价格

```bash
curl -s "http://push2delay.eastmoney.com/api/qt/stock/get?secid=0.{代码}&fields=f43,f44,f45,f46,f57,f58,f60,f170" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print(f\"{d['f58']}({d['f57']}): 现价{d['f43']/100} 涨跌{d['f170']/100}% 最高{d['f44']/100} 最低{d['f45']/100} 昨收{d['f60']/100}\")
"
```

## 字段说明
- f43: 最新价（需/100）
- f44: 最高价
- f45: 最低价
- f46: 开盘价
- f57: 股票代码
- f58: 股票名称
- f60: 昨收价
- f170: 涨跌幅（%）

## 使用时机
- **每次分析前必须调用**，不能用缓存数据
- 用户会直接对比你的数据和实际行情
- 数据延迟约3-5秒，可接受

## 计算回调位置
```python
current = 16.49
pullback_2pct = current * 0.98  # 回调2%
pullback_3pct = current * 0.97  # 回调3%
```
