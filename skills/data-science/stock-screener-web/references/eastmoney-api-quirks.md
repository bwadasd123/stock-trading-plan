# 东方财富 API 字段陷阱

## `fltt` 参数决定返回值格式

**关键**: `fltt=1` 返回整数值（需除以100），`fltt=2` 返回小数值（已是正确格式）。

| 字段 | fltt=1 示例 | fltt=2 示例 | 含义 |
|------|------------|------------|------|
| f2 (价格) | 8060 | 80.6 | 需/100 vs 直接用 |
| f3 (涨跌幅) | 3000 | 30.0 | 需/100 vs 直接用 |
| f8 (换手率) | 2276 | 22.76 | 需/100 vs 直接用 |
| f9 (PE) | 36286 | 362.86 | 需/100 vs 直接用 |
| f6 (成交额) | 1357000000 | 13.57亿 | 原始值(元) |
| f20 (流通市值) | 16056000000 | 160.56 | 原始值(元) |

**scanner.py 使用 `fltt=1`**，所以 f2/f3/f8/f9 都需要 `/100`。

## ⚠️ 常犯错误

**不要假设 f8 已经是百分比值！** 
- `fltt=1` 时 f8=2276 表示 22.76%，必须 `/100`
- `fltt=2` 时 f8=22.76 才是直接的百分比值

## 北交所股票代码

需要屏蔽的代码段（需要50万门槛）：
- `8xxxxx` — 830xxx~839xxx, 870xxx~879xxx
- `920xxxx` — 新股申购代码段

```python
if code.startswith("8") or code.startswith("920"):
    continue
```

## 板块资金流向字段映射

| 字段 | 含义 | 单位 |
|------|------|------|
| f62 | 主力净流入 | 元 |
| f184 | 主力净占比 | % |
| f66 | 超大单净流入 | 元 |
| f69 | 超大单净占比 | % |
| f72 | 大单净流入 | 元 |
| f75 | 大单净占比 | % |
| f78 | 中单净流入 | 元 |
| f81 | 中单净占比 | % |
| f84 | 小单净流入 | 元 |
| f87 | 小单净占比 | % |
| f204 | 领涨股代码 | - |
| f205 | 领涨股名称 | - |
| f206 | 领涨股涨跌幅 | % (需/100) |
| f207 | 领跌股代码 | - |
| f208 | 领跌股名称 | - |
| f209 | 领跌股跌幅 | % (需/100) |

## JSON vs JSONP 响应格式

**关键陷阱**: 东财不同接口返回格式不一致！

| 接口 | 格式 | 示例 |
|------|------|------|
| `push2his.eastmoney.com` (K线) | JSONP | `jQuery123_456({"rc":0,...})` |
| `push2.eastmoney.com` (行情/板块) | 纯JSON | `{"rc":0,...}` |
| `datacenter-web.eastmoney.com` (龙虎榜) | JSONP | `jQuery123_456({"rc":0,...})` |

**正确解析方式**（兼容两种格式）:
```python
text = resp.text
m = re.search(r'\((\{.*\})\)', text)  # 尝试JSONP
if m:
    text = m.group(1)
data = json.loads(text)  # JSONP取括号内容，纯JSON直接解析
```

**错误写法**（会导致纯JSON接口返回None）:
```python
m = re.search(r'\((\{.*\})\)', resp.text)
if m:  # 纯JSON时m为None，数据丢失！
    data = json.loads(m.group(1))
```

**已知纯JSON接口**: `push2.eastmoney.com/api/qt/stock/get`（获取个股详情/f84流通股本等）

## ⚠️ K线 API `smplmt` 参数陷阱 (2026-06-09 发现)

**问题**: `push2his.eastmoney.com` K线接口的 `smplmt` 参数会导致返回**采样后的稀疏数据**，而非连续日线！

| 参数设置 | 返回结果 | K线间隔 |
|----------|---------|---------|
| `smplmt=460` | 460根采样数据 | ~20天/根（月线级别） |
| 去掉`smplmt` | 5936根完整数据 | 每日连续 ✅ |

**影响范围**:
- 个股详情页面K线图显示错误
- MA5/MA10/MA20均线计算错误（基于稀疏数据）
- RSI、MACD、CCI等技术指标全部错误
- 扫描器7指标校验结果不可靠

**正确写法** (`services/kline.py`):
```python
params = {
    "secid": secid,
    "klt": period,    # 101=日线
    "fqt": 1,         # 前复权
    "beg": 0,
    "end": 20500101,
    # ❌ "smplmt": 460,  — 导致采样！
    "lmt": limit,     # 控制返回数量
}
```

**验证方法**:
```bash
# 检查K线是否连续（应返回每日日期）
curl -s "http://localhost:8080/api/analyze?code=600519&period=101&limit=5" | python3 -c "
import sys, json; d = json.load(sys.stdin)
for k in d['klines'][-5:]: print(k['date'])
"
# 正确: 6/3, 6/4, 6/5, 6/8, 6/9 (连续)
# 错误: 3/25, 4/14, 5/6, 5/25, 6/9 (稀疏)
```

## 龙虎榜 API

- API: `datacenter-web.eastmoney.com/api/data/v1/get`
- 报表: `RPT_DAILYBILLBOARD_DETAILSNEW`
- **今日无数据是正常的**（盘中/非交易日），需自动往前找最近有数据的日期
- 滤镜格式: `(TRADE_DATE>='2026-06-01')(TRADE_DATE<='2026-06-01')`
