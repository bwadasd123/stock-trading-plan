# 东方财富API坑点记录

## JSON vs JSONP 响应格式

**问题**：不同端点返回格式不同
- `push2his.eastmoney.com` (K线) → JSONP格式 `jQuery123({...})`
- `push2.eastmoney.com/api/qt/stock/get` (个股详情) → **纯JSON** `{...}`

**错误写法**（只匹配JSONP）：
```python
m = re.search(r'\((\{.*\})\)', resp.text)
if m:
    d = json.loads(m.group(1))
```

**正确写法**（兼容两种）：
```python
text = resp.text
m = re.search(r'\((\{.*\})\)', text)
if m:
    text = m.group(1)  # JSONP: 提取括号内JSON
d = json.loads(text)   # 纯JSON: 直接解析
```

## fltt 参数
- `fltt=1` → 整数（需 /100 转实际值）
- `fltt=2` → 小数（直接使用）
- Scanner 用 fltt=1

## 流通市值获取
`/api/qt/stock/get` 端点：
- `f84` = 流通股本
- `f116` = 流通市值（元）
- `f117` = 总市值（元）
- 计算: `circ_cap = f84 * price / 1e8` 或 `f116 / 1e8`

## 代理使用
- **直连会被封**，必须走代理池
- `safe_get()` 会自动从代理池取代理
- 代理池为空时会阻塞尝试补充（可能超时）
- 代理池初始化已改为非阻塞（后台线程）

## 请求头
`get_kline_headers(code)` 生成标准请求头，包含：
- User-Agent (Chrome)
- Referer (quote.eastmoney.com)
- Cookie (Playwright获取或fallback)

## ⚠️ smplmt 参数陷阱 (2026-06-09 发现)

**问题**：`push2his.eastmoney.com` 的 `smplmt` 参数会导致返回**采样后的稀疏数据**，而非完整日线。

**表现**：
- 请求日线(KLT=101)，返回的K线间隔约20天（月度采样）
- 每只股票采样密度不同（茅台~20天，宁德时代~5天）
- 直接影响MA、RSI、MACD、CCI等所有技术指标计算

**错误写法**：
```python
params = {
    "klt": "101",      # 日线
    "smplmt": 460,     # ❌ 这个参数导致采样！
    "lmt": 1000000,
}
```

**正确写法**：
```python
params = {
    "klt": "101",      # 日线
    # 不能使用smplmt参数
    "lmt": 250,        # 用lmt控制返回数量
}
```

**验证方法**：
```python
# 检查返回的K线是否连续
klines = data['data']['klines']
dates = [k.split(',')[0] for k in klines[-5:]]
# 如果日期间隔>2天，说明被采样了
```

**影响范围**：
- `services/kline.py` 的 `get_kline_data()` 函数
- 扫描器的7个技术指标计算
- 个股详情页面的K线显示

## 量比计算标准定义

**标准定义**：`量比 = 当日成交量 / 过去5日平均成交量`

**错误写法**：
```python
vol_ratio = v.iloc[-1] / v.iloc[-2]  # 今日/昨日 ❌
```

**正确写法**：
```python
vol_avg_5 = v.iloc[-6:-1].mean()  # 过去5日均量
vol_ratio = v.iloc[-1] / vol_avg_5  # 今日/5日均量 ✅
```

**差异示例**（贵州茅台）：
- 今日/昨日 = 0.90
- 今日/5日均量 = 0.76
- 差异约18%，会影响筛选结果

## RSI计算方式差异

**系统实现**：SMA(简单移动平均)
```python
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
```

**通达信实现**：EMA(指数移动平均)
```python
gain_ema = delta.where(delta > 0, 0).ewm(span=14, adjust=False).mean()
loss_ema = (-delta.where(delta < 0, 0)).ewm(span=14, adjust=False).mean()
```

**差异**：约6点（如系统37.1 vs 通达信30.7），趋势方向一致，可接受。
