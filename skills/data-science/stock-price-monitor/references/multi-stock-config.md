# 多股票监控配置

## v13配置格式（含仓位管理）

```python
# 仓位管理配置
TOTAL_CAPITAL = 30000  # 总资金3万
SINGLE_POSITION_PCT = 20  # 单只股票仓位比例20%
SINGLE_POSITION_AMOUNT = TOTAL_CAPITAL * SINGLE_POSITION_PCT / 100  # 单只股票金额6000元
MAX_HOLD_DAYS = 5  # 持仓天数上限

STOCKS = [
    {
        "code": "0.002167",       # 东财secid格式（0=深市，1=沪市）
        "name": "东方锆业",
        "ts_code": "002167",      # 纯数字代码（数据库用）
        "cost": None,             # 成本价（None=未买入）
        "shares": 0,              # 股数（0=未买入）
        "buy_date": None,         # 买入日期 "YYYY-MM-DD"（仅持仓需要）
        "tp_pct": 10,             # 止盈百分比
        "sl_pct": 7,              # 止损百分比
        "type": "观察"            # "持仓" 或 "观察"
    },
    # 可添加更多股票...
]
```

## 字段说明

| 字段 | 含义 | 示例 |
|------|------|------|
| code | 东财secid格式 | "0.159599" (ETF), "0.002167" (深市), "1.600519" (沪市) |
| name | 股票名称 | "芯片ETF" |
| ts_code | 纯数字代码 | "159599" |
| cost | 买入成本价，None表示未买入 | 3.528 |
| shares | 持仓数量，0表示未买入 | 8500 |
| buy_date | 买入日期（v13新增） | "2026-06-26" |
| tp_pct | 止盈百分比 | 10 |
| sl_pct | 止损百分比 | 5 |
| type | "持仓"或"观察" | "持仓" |

## 买入后配置变更

```python
# 用户买入后，更新对应股票配置
{
    "code": "0.002167",
    "name": "东方锆业",
    "ts_code": "002167",
    "cost": 22.50,           # ← 填入买入价
    "shares": 200,           # ← 填入股数
    "buy_date": "2026-06-26", # ← 填入买入日期
    "tp_pct": 10,
    "sl_pct": 7,
    "type": "持仓"            # ← 改为持仓
}
```

## 清仓后配置变更

```python
# 清仓后，从"持仓"改为"观察"
{
    "code": "0.159599",
    "name": "芯片ETF",
    "cost": None,      # ← 清空成本
    "shares": 0,       # ← 清空股数
    "buy_date": None,  # ← 清空买入日期
    "type": "观察"     # ← 改为观察
}
```

## 持仓天数计算（交易日）

```python
def get_trading_days(buy_date_str):
    """计算从买入日期到今天的交易日数（排除周末和节假日）"""
    buy_date = datetime.datetime.strptime(buy_date_str, "%Y-%m-%d").date()
    today = date.today()
    if buy_date >= today:
        return 0
    
    holidays = {
        "2026-01-01", "2026-01-02", "2026-01-03",
        "2026-02-15", "2026-02-16", "2026-02-17", "2026-02-18",
        "2026-04-05", "2026-04-06", "2026-04-07",
        "2026-05-01", "2026-05-02", "2026-05-03",
        "2026-06-14", "2026-06-15", "2026-06-16",
        "2026-09-21", "2026-09-22", "2026-09-23",
        "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07",
    }
    
    trading_days = 0
    current = buy_date + timedelta(days=1)
    while current <= today:
        if current.weekday() < 5 and current.isoformat() not in holidays:
            trading_days += 1
        current += timedelta(days=1)
    return trading_days
```

## format_stock() 完整实现

```python
def format_stock(stock, price_data):
    price = price_data["price"]
    change_pct = price_data["change_pct"]
    
    msg = f"📈 {stock['name']} {stock['ts_code']}\n"
    msg += f"💰 现价 {price:.3f}  |  今日 {change_pct:+.2f}%\n"
    
    if stock["cost"]:
        cost_pct = (price - stock["cost"]) / stock["cost"] * 100
        profit = (price - stock["cost"]) * stock["shares"]
        tp = stock["cost"] * (1 + stock["tp_pct"] / 100)
        sl = stock["cost"] * (1 - stock["sl_pct"] / 100)
        
        msg += f"📊 成本 {stock['cost']:.3f}  |  涨幅 {cost_pct:+.1f}%\n"
        msg += f"💼 盈亏 {'+' if profit >= 0 else ''}{profit:.0f}元\n"
        msg += f"🎯 止盈 {tp:.3f}  |  🚨 止损 {sl:.3f}\n"
        
        # 持仓天数（v13）
        if stock.get("buy_date"):
            holding_days = get_trading_days(stock["buy_date"])
            msg += f"📅 持仓 {holding_days}天"
            if holding_days >= MAX_HOLD_DAYS:
                msg += f" ⚠️已超{MAX_HOLD_DAYS}天上限！"
            msg += "\n"
        
        # 仓位占比（v13）
        position_value = stock["cost"] * stock["shares"]
        position_pct = position_value / TOTAL_CAPITAL * 100
        msg += f"💼 仓位 {position_value:.0f}元({position_pct:.0f}%)"
        if position_value > SINGLE_POSITION_AMOUNT:
            msg += f" ⚠️超仓"
        msg += "\n"
        
        # 预警
        if price >= tp:
            msg += f"⚠️ 【已到止盈位！】\n"
        elif price <= sl:
            msg += f"🔴 【已到止损位！】\n"
        elif cost_pct >= 5:
            msg += f"💰 成本涨幅+5%以上\n"
        elif cost_pct <= -3:
            msg += f"⚠️ 成本跌幅-3%以上\n"
    else:
        # 观察股票
        tp = price * 1.10
        sl = price * 0.93
        msg += f"👀 观察中  |  止盈 {tp:.3f}  |  止损 {sl:.3f}\n"
        
        # 仓位建议（v13）
        if price > 0:
            suggested_shares = int(SINGLE_POSITION_AMOUNT / price / 100) * 100
            if suggested_shares > 0:
                msg += f"💡 建议仓位 {suggested_shares}股({suggested_shares * price:.0f}元)\n"
        
        if change_pct >= 9.9:
            msg += f"🚀 涨停！\n"
        elif change_pct >= 5:
            msg += f"📈 大涨5%+\n"
        elif change_pct <= -5:
            msg += f"📉 大跌5%+\n"
    
    msg += f"━━━━━━━━━━━━━━━━━━━━"
    return msg, price, change_pct
```

## generate_advice() 完整实现

```python
def generate_advice():
    """生成持仓分析和操作建议"""
    # 获取大盘数据
    try:
        url = 'http://push2delay.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f14&secids=1.000001,0.399001,0.399006'
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            indices = data.get('data', {}).get('diff', [])
            market_trend = "偏暖" if any(i.get('f3', 0) > 1 for i in indices) else "震荡"
    except:
        market_trend = "未知"
    
    msg = "\n📊 【持仓分析与建议】\n"
    msg += f"市场情绪: {market_trend}\n"
    msg += f"总资金: {TOTAL_CAPITAL}元 | 单股上限: {SINGLE_POSITION_AMOUNT:.0f}元\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    
    has_position = False
    for stock in STOCKS:
        price_data = get_price(stock['code'])
        if not price_data:
            continue
        
        price = price_data['price']
        change_pct = price_data['change_pct']
        
        if stock['type'] == '持仓' and stock['cost']:
            has_position = True
            cost = stock['cost']
            shares = stock['shares']
            profit_pct = (price - cost) / cost * 100
            profit_amount = (price - cost) * shares
            tp = cost * (1 + stock['tp_pct'] / 100)
            sl = cost * (1 - stock['sl_pct'] / 100)
            dist_tp = (tp / price - 1) * 100
            dist_sl = (1 - sl / price) * 100
            
            holding_days = 0
            if stock.get('buy_date'):
                holding_days = get_trading_days(stock['buy_date'])
            
            position_value = cost * shares
            position_pct = position_value / TOTAL_CAPITAL * 100
            
            msg += f"\n🎯 {stock['name']} 分析:\n"
            msg += f"现价 {price:.3f} | 盈利 +{profit_amount:.0f}元 (+{profit_pct:.1f}%)\n"
            msg += f"距止盈 {dist_tp:.1f}% | 距止损 {dist_sl:.1f}%\n"
            msg += f"持仓 {holding_days}天 | 仓位 {position_value:.0f}元({position_pct:.0f}%)\n"
            
            # 建议优先级：止盈 > 止损 > 超天数 > 超仓 > 浮盈
            if price >= tp:
                msg += "🚨 【已到止盈位！建议立即减仓】\n"
            elif price <= sl:
                msg += "🔴 【已到止损位！建议清仓】\n"
            elif holding_days >= MAX_HOLD_DAYS:
                msg += f"⏰ 【持仓超{MAX_HOLD_DAYS}天！建议减仓或清仓】\n"
            elif position_value > SINGLE_POSITION_AMOUNT:
                msg += f"💼 【超仓！当前{position_pct:.0f}%，建议减到{SINGLE_POSITION_PCT}%】\n"
            elif dist_tp <= 3:
                msg += "🎯 逼近止盈！冲高减半仓\n"
            elif profit_pct >= 6:
                msg += "💰 浮盈6%+，可考虑减仓锁定利润\n"
            elif profit_pct >= 5:
                msg += "💰 浮盈5%+，继续持有等止盈\n"
            elif profit_pct >= 3:
                msg += "✅ 浮盈3%+，趋势向好\n"
            elif profit_pct <= -3:
                msg += "⚠️ 浮亏3%+，注意风险\n"
            else:
                msg += "📊 持有中，观望\n"
        else:
            msg += f"\n👀 {stock['name']} 观察:\n"
            msg += f"现价 {price:.3f} | 今日 {change_pct:+.2f}%\n"
            
            if price > 0:
                suggested_shares = int(SINGLE_POSITION_AMOUNT / price / 100) * 100
                if suggested_shares > 0:
                    msg += f"💡 建议仓位 {suggested_shares}股({suggested_shares * price:.0f}元)\n"
            
            if change_pct >= 5:
                msg += "🚀 大涨中，不追高\n"
            elif change_pct <= -3:
                msg += "📉 大跌中，可关注建仓机会\n"
            else:
                msg += "📊 等待回调建仓\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
    
    if not has_position:
        msg += "\n💼 当前全部空仓，等待信号\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
    
    return msg
```

## main() 中持仓天数提醒

```python
# 在止盈止损提醒之后，观察股票提醒之前
if stock.get("buy_date"):
    holding_days = get_trading_days(stock["buy_date"])
    if holding_days >= MAX_HOLD_DAYS and "hold_days" not in state["alerted"][key]:
        profit = (price - stock["cost"]) * stock["shares"]
        msg = f"⏰ 【{stock['name']} 持仓超{MAX_HOLD_DAYS}天！】\n"
        msg += f"现价 {price:.3f}  |  盈利 {'+' if profit >= 0 else ''}{profit:.0f}元\n"
        msg += f"持仓 {holding_days}天  |  建议减仓或清仓"
        send_wx(msg)
        state["alerted"][key].append("hold_days")
        save_state(state)
        return
```

## 清仓后动态管理

用户会根据持仓变化动态调整监控列表：

### 场景1：清仓后改为观察
```python
# 芯片ETF卖出后，从"持仓"改为"观察"
{
    "code": "0.159599",
    "name": "芯片ETF",
    "cost": None,      # 清空成本
    "shares": 0,       # 清空股数
    "buy_date": None,  # 清空买入日期
    "type": "观察"     # 改为观察
}
```

### 场景2：从监控列表移除
用户说"ETF就不要观察了，去掉" → 直接从STOCKS列表删除该股票，不要问用户确认。

## 状态文件结构

```json
{
    "alerted": {
        "159599": ["pct_3", "pct_4", "cost_5.0"],
        "002167": ["pct_2"]
    },
    "open_sent": false,
    "close_sent": false,
    "last_hourly": null,
    "today": "2026-06-25"
}
```

每个股票的提醒记录独立存储在`alerted[ts_code]`中。
