# 次日操作分析流程

## 触发条件
用户问"现在该怎么操作"或"今天做什么"时，按此流程分析。

## 分析步骤

### 1. 获取昨日扫描结果
```python
# 从备份文件读取（SCAN_STATE可能不可用）
import json, glob
files = sorted(glob.glob('/home/jmy/stock-screener/backup_*.json'))
if files:
    data = json.load(open(files[-1]))
    # ⚠️ 必须用 stock_scan_results，不是 stock_snapshot！
    # stock_snapshot 是全量扫描（几百只），stock_scan_results 是筛选推荐（1只）
    stocks = data.get('stock_scan_results', [])
```

**关键区别：**
- `stock_snapshot` — 全量扫描结果（几百只），未筛选的原始数据
- `stock_scan_results` — **筛选后推荐股票**（通常1只），这才是你要操作的

### 2. 检查今日开盘情况
对扫描结果中的股票，获取实时行情：
```bash
curl -s "http://push2delay.eastmoney.com/api/qt/stock/get?secid={市场}.{代码}&fields=f43,f46,f170,f57,f58"
```
- f43: 当前价（/100）
- f46: 开盘价（/100）
- f170: 涨跌幅（/100%）

### 3. 判断买入条件
**必须同时满足：**
- [ ] 高开幅度 < 3%：`(开盘价 - 昨收) / 昨收 < 0.03`
- [ ] 未涨停：当前价 < 涨停价
- [ ] RSI < 80（非严重超买）

### 4. 计算RSI（简化版）
```python
# 从K线数据提取收盘价
closes = [...]  # 最近5-6个交易日
gains = [max(0, closes[i]-closes[i-1]) for i in range(1, len(closes))]
losses = [max(0, closes[i-1]-closes[i]) for i in range(1, len(closes))]
avg_gain = sum(gains) / len(gains)
avg_loss = sum(losses) / len(losses)
rsi = 100 if avg_loss == 0 else 100 - (100 / (1 + avg_gain/avg_loss))
```

**RSI判断：**
- RSI=100: 连续上涨无回调，极度超买，禁止买入
- RSI>80: 超买区，持仓1-2天，目标8%，止损-5%
- RSI 70-80: 正常区间，持仓3-5天，目标15%，止损-8%

### 5. 综合判断
- **大盘环境**：先查上证指数涨跌幅
- **个股筛选**：从扫描结果中找符合条件的股票
- **风险评估**：RSI过高、高开过多、大盘弱势都应观望

### 6. 板块资金流向分析
用户关注板块概念，需要检查相关板块资金流入：
```bash
# 获取概念板块资金流向
curl -s "http://push2delay.eastmoney.com/api/qt/clist/get?fid=f62&po=1&pz=500&pn=1&np=1&fltt=2&invt=2&fs=m:90+t:3&fields=f12,f14,f62"
# 搜索相关概念
concepts = ['铁路', '磁悬浮', '储能', '信创', '人工智能', '一带一路', '网络安全', '数据安全']
```

## 输出格式
```
📊 今日操作建议
- 大盘：上证指数 XXXX.XX (±X.XX%)
- 昨日扫描：X只股票
- 符合条件：X只
- 建议：买入XXX / 观望
- 原因：[简要说明]
- 板块资金：[相关概念资金流入情况]
```

## 常见陷阱
1. **读错数据源**：必须用`stock_scan_results`，不是`stock_snapshot`
2. **RSI=100不是好消息**：表示连续上涨无回调，随时可能回调
3. **高开≠强势**：高开超过3%追入风险大
4. **涨停股不能买**：已涨停无法成交
5. **大盘弱势要谨慎**：个股难独善其身
6. **板块好≠个股一定涨**：板块资金流入是加分项，但不是决定因素
