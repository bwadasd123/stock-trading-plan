# 未知股票代码查找流程

当用户提供代码但东财API返回空数据时（如588170），按以下步骤查找：

## 步骤

### 1. 用搜索API确认代码
```python
url = 'http://searchapi.eastmoney.com/api/suggest/get?input=588170&type=14&token=D43BF722C8E33BDC906FB84D85E326E8&count=5'
```
返回：`科创半导体ETF华夏 588170`

### 2. 确定secid前缀
| 市场 | 代码范围 | secid前缀 |
|------|----------|-----------|
| 深交所 | 000xxx, 002xxx, 003xxx, 159xxx | 0. |
| 上交所 | 513xxx, 588xxx, 600xxx, 603xxx | 1. |
| 创业板 | 300xxx, 399xxx | 0. |
| 科创板ETF（上证） | 588xxx | **1.** |

### 3. 验证secid
```python
# 尝试两种前缀，取有数据的那个
for secid in ['1.588170', '0.588170']:
    url = f'http://push2delay.eastmoney.com/api/qt/stock/get?secid={secid}&fltt=2&fields=f43,f58,f170'
    # 检查data是否为None
```

## 本案：588170
- 代码：588170
- 名称：科创半导体ETF华夏
- secid：`1.588170`（上交所）
- 属于ETF → 止盈10%/止损5%
