# 未知代码查找流程

## 问题场景
用户提到一个股票代码（如588170），但用常见secid格式（0.588170）查不到数据。

## 查找步骤

### 第1步：用东财搜索API确认名称
```python
import urllib.request, json, os
os.environ['NO_PROXY'] = '*'

url = 'http://searchapi.eastmoney.com/api/suggest/get?input=588170&type=14&token=D43BF722C8E33BDC906FB84D85E326E8&count=5'
resp = urllib.request.urlopen(url, timeout=5)
data = json.loads(resp.read())
if data.get('QuotationCodeTable', {}).get('Data'):
    for item in data['QuotationCodeTable']['Data']:
        print(item.get('Name'), item.get('Code'), item.get('Market'))
```
输出示例：`科创半导体ETF华夏 588170 None`

### 第2步：判断交易所前缀
| 代码开头 | 交易所 | secid前缀 |
|----------|--------|-----------|
| 000/001/002/003 | 深圳主板/中小板 | `0.` |
| 300 | 创业板 | `0.` |
| 600/601/603/605 | 上海主板 | `1.` |
| 688 | 科创板股票 | `1.` |
| 159xxx/16xxxx | 深圳ETF | `0.` |
| 51xxxx/58xxxx | 上海ETF | `1.` |
| 8开头 | 北交所 | 屏蔽 |

### 第3步：逐个尝试可能的secid
```python
for secid in ['1.588170', '0.588170']:  # 先试1（上海），再试0（深圳）
    url = 'http://push2delay.eastmoney.com/api/qt/stock/get?secid={}&fltt=2&fields=f43,f57,f58'.format(secid)
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        d = json.loads(resp.read()).get('data')
        if d and d.get('f58'):
            print('找到: secid={} name={}'.format(secid, d['f58']))
            break
    except:
        continue
```

### 2026-07-01案例
588170（科创半导体ETF华夏）用`0.588170`返回None，用`1.588170`成功：
- 现价: 4.118, 昨收: 4.132, RSI: 81.0（超买！）
- 提醒用户不要追高RSI>80的ETF
