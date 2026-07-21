# 买卖交易更新工作流

> 2026-06-30 制定：用户要求买卖交易必须推送到企微，且清仓/建仓后更新所有配置。
> 用户质问："企业微信的卖出和买入你还是没推送啊"

## ⚠️ 触发时机

用户说出以下任何一句时，执行对应流程：
- 卖出："清仓了XX"、"卖出了XX"、"涨停价清仓了XX"
- 买入："XX买入了X股"、"又买入了X股"（加仓）
- 批量：一次消息中报告多笔交易 → 参见 `references/same-day-batch-update.md`

---

## 📤 卖出流程（6步）

### 第1步：获取实时价格验证交易
```python
import urllib.request, json, os
os.environ['NO_PROXY'] = '*'

code = "0.002167"  # 东财secid
url = f"http://push2delay.eastmoney.com/api/qt/stock/get?secid={code}&fltt=2&fields=f43,f170,f60"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
data = json.loads(urllib.request.urlopen(req, timeout=10).read())['data']
price = data['f43']

# 计算盈亏
profit = (price - cost) * shares
new_total = TOTAL_CAPITAL + int(round(profit))
```

### 第2步：更新 price_monitor.py
- STOCKS: cost=None, shares=0, buy_date=None, type="观察"
- 注释加入清仓日期+盈亏
- TOTAL_CAPITAL += 盈利

### 第2.5步：🔁 计算回本买入价（2026-07-08新增，必须执行）

**用户要求**：每次卖出后必须自动计算"回本买入价"并告知用户。

公式：`回本买入价 = 卖出均价 - (已实现亏损 / 目标持股数)`

```python
# 计算回本买入价（目标持股数取决于用户想接回多少）
avg_sell = sum(shares_i * price_i for i in sells) / total_sold
loss = (avg_sell - old_cost) * total_sold  # 已实现亏损
target_shares = total_sold  # 默认目标=卖出数，用户可调整
break_even_buy = avg_sell - (loss / target_shares)

# ⚠️ 注意区分两个概念（2026-07-08用户纠正）：
# 1. 买入回本价：买入价≤X 能让新持仓成本回到原成本 — 公式见上
# 2. 涨到回本价：买入后涨到Y 才能填平历史亏损 — Y = 买入价 + (亏损/股数)
# 用户要的是买入回本价，告知一个价格即可
```

**推送格式**（简洁，一个价格）：
```
🔁 回本买入价: ≤ 3.67（2600股）
```
加到清仓通知末尾即可，不要额外分析。

### 第3步：清理 .monitor_state.json
```python
import json
state_file = '/home/jmy/.hermes/profiles/eastmoney-bot/.monitor_state.json'
with open(state_file) as f:
    state = json.load(f)

code = "002167"

# 清除涨停状态
if 'prev_limit_up' in state:
    state['prev_limit_up'][code] = False

# 清除止损止盈相关alert
if code in state.get('alerted', {}):
    remove_keys = ['sl', 'near_sl', 'near_tp', 'tp', 'near_limit_up']
    state['alerted'][code] = [a for a in state['alerted'][code] if a not in remove_keys]

with open(state_file, 'w') as f:
    json.dump(state, f, ensure_ascii=False)
```

### 第4步：推送企微通知（直接发，不用pending_trades）
```python
# 获取key + 发送
result = subprocess.run(['grep', 'WX_WEBHOOK', '.env'], capture_output=True, text=True)
key = result.stdout.strip().split('key=')[1]
url = f'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}'

msg = f"""🔴 【{stock_name} {code} 清仓】

📊 交易详情
━━━━━━━━━━━━━━━━━━━━
买入: {shares}股 × {cost} = {cost*shares:.0f}元
卖出: {shares}股 × {price} = {price*shares:.0f}元
盈利: {profit:+.0f}元（{profit_pct:+.1f}%）
━━━━━━━━━━━━━━━━━━━━
💰 总资金: {new_total}元
📊 累计盈利: +{new_total-30000}元"""

data = json.dumps({'msgtype':'text','text':{'content':msg}}).encode()
urllib.request.urlopen(urllib.request.Request(url, data=data, 
    headers={'Content-Type':'application/json'}), timeout=5)
```

### 第5步：更新 docs/system-logic.md
- 交易记录表：新增一行（日期/股票/操作/价格/数量/盈亏）
- 合计：更新累计盈利
- 持仓表：移除该股或移到观察列表
- 资金状态：总资金、持仓市值、可用资金

### 第6步：语法验证 + Git提交
```bash
python3 -c "import ast; ast.parse(open('scripts/price_monitor.py').read())"
cd /home/jmy/.hermes/profiles/eastmoney-bot
git add scripts/price_monitor.py docs/system-logic.md .monitor_state.json
git commit -m "交易: {股票名} 清仓 {盈亏} — 改为观察，总资金{new_total}"
git push
```

---

## 📤➖ 减仓流程（Partial Sell，4步）

> 2026-07-15 新增：用户纠正减仓后成本必须摊薄，不能保留原成本。

减仓比清仓简单。不需要清理状态文件，但**成本必须摊薄**。

### 减仓成本公式（🔴 用户纠正过）
```python
# ❌ 错误：保留原成本
new_cost = old_cost  # 10.99 → 错！

# ✅ 正确：摊薄成本
new_cost = (old_cost * old_shares - sell_price * sell_shares) / remain_shares
# 例: (10.99*1200 - 11.32*600) / 600 = 10.66
```

### 减仓陷阱：TOTAL_CAPITAL double-count
分两笔清仓时，第二笔的"盈利"若用摊薄成本计算会double-count第一笔利润：
```python
# ❌ 第二笔用摊薄成本10.66算 → (11.14-10.66)*600=288 → 但198已计入第一笔
# ✅ 两笔统一从原始成本算总盈利 = 13476 - 13188 = 288
# 第二笔增量 = (11.14-10.99)*600 = 90
```

**规则**：清仓时总盈利从原始买入价统一算，不从摊薄成本累加。

### 减仓4步清单
1. 更新 cost = 摊薄成本，shares = 剩余
2. TOTAL_CAPITAL += 卖出盈亏（仅本次增量，非摊薄后的虚假利润）
3. pending_trades 写入减仓通知
4. Git提交（不需要更新docs/system-logic.md除非全清）

### 场景1：新股票建仓（监控列表中不存在）

**2026-06-30 蔚蓝锂芯 002245 为例：**
1. 先查东财API获取股票名称和现价
2. 在STOCKS列表**末尾**追加配置块（用patch工具）
3. 在.monitor_state.json中初始化该股的alerted、prev_limit_up/down
4. 推送买入通知到企微
5. 更新docs
6. 语法验证 + Git提交

```python
# 步骤2: 在STOCKS中插入新股票
old = """    {
        "code": "0.002141",
        "name": "贤丰控股","""

new = """    {
        "code": "0.002245",
        "name": "蔚蓝锂芯",
        "ts_code": "002245",
        "cost": 18.585,
        "shares": 200,
        "buy_date": "2026-06-30",
        "tp_pct": 15,
        "sl_pct": 8,
        "type": "持仓"
    },
    {
        "code": "0.002141",
        "name": "贤丰控股","""

patch('scripts/price_monitor.py', old, new)

# 步骤3: 初始化状态
with open(state_file) as f:
    state = json.load(f)
state.setdefault("alerted", {})["002245"] = []
state.setdefault("prev_limit_up", {})["002245"] = False
state.setdefault("prev_limit_down", {})["002245"] = False
with open(state_file, 'w') as f:
    json.dump(state, f, ensure_ascii=False)
```

### 场景2：加仓（已有持仓，均价重新计算）

**2026-06-30 蔚蓝锂芯加仓200股@18.38为例：**
- 第一笔: 200股 × 18.585 = 3,717元
- 第二笔: 200股 × 18.380 = 3,676元
- 均价: (3,717 + 3,676) / 400 = 18.483

```python
# 重新计算均价
new_avg = (old_cost * old_shares + new_price * new_shares) / (old_shares + new_shares)

# 更新STOCKS
old = """        "cost": 18.585,
        "shares": 200,"""

new = """        "cost": 18.483,
        "shares": 400,"""

patch('scripts/price_monitor.py', old, new)

# ⚠️ 均价改变后需清理止盈止损告警（避免旧数据误导）
if code in state.get('alerted', {}):
    remove_keys = ['near_sl', 'near_tp', 'sl', 'tp']
    state['alerted'][code] = [a for a in state['alerted'][code] if a not in remove_keys]
```

### 加仓注意事项
- **检查仓位上限**：单股不超过TOTAL_CAPITAL × 20%
- **均价四舍五入到3位小数**
- **推送通知标注⚠️超仓** if 仓位 > 20%

### 买入通知模板
```python
msg = f"""🟢 【{stock_name} {code} 买入】

📊 交易详情
━━━━━━━━━━━━━━━━━━━━
买入: {shares}股 × {cost} = {total}元
━━━━━━━━━━━━━━━━━━━━
🎯 止盈: {tp}（+{tp_pct}%）
🚨 止损: {sl}（-{sl_pct}%）
📅 买入日: {buy_date}
━━━━━━━━━━━━━━━━━━━━
💼 仓位: {total}元（{pct}%）
💰 总资金: {total_capital}元
📊 可用: ~{available}元
━━━━━━━━━━━━━━━━━━━━
⚠️ T+1: {next_trading_day}可卖出"""

# 加仓时用"加仓"而非"买入"
msg = msg.replace("买入", "加仓")
```

### T+1在买入通知中必须提醒
```
⚠️ T+1: 明天(7/1)可卖出
```
周一买入→周二可卖，周五买入→锁仓2天下周可卖

---

## 📊 完整状态文件结构（v14，2026-06-30）
```json
{
  "alerted": {
    "002167": ["pct_-3", "cost_-8.0", "pct_10"],
    "002141": ["pct_1", "cost_0.5"],
    "002245": []
  },
  "open_sent": false,
  "close_sent": false,
  "last_hourly": "11:00",
  "today": "2026-06-30",
  "prev_limit_up": {"002167": false, "002245": false, "002141": false},
  "prev_limit_down": {"002167": false, "002245": false, "002141": false},
  "market_warned": false,
  "pending_trades": []
}
```

**⚠️ 每日重置时保留 `pending_trades`**（跨日未发送的通知），其余全部清空。
