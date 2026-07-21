# 成本线涨跌幅提醒实现

## 核心概念

**两个涨幅指标**：
- 今日涨幅 = (现价 - 昨收) / 昨收 — 反映当天波动
- 成本涨幅 = (现价 - 成本价) / 成本价 — 反映实际盈亏

用户更关心成本涨幅，因为这是实际的盈亏情况。

## 提醒配置

```python
# 0.5%间隔的提醒点位（从-5%到+10%）
COST_ALERTS = [-5.0, -4.5, -4.0, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 
               0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 
               6.0, 7.0, 8.0, 9.0, 10.0]
```

## 计算逻辑

```python
# 计算成本涨幅（保留1位小数）
cost_pct = (price - AVG_COST) / AVG_COST * 100

# 四舍五入到0.5%（关键！不要用round(cost_pct)会变成整数）
cost_pct_rounded = round(cost_pct * 2) / 2

# 检查是否触发提醒
if cost_pct_rounded not in state.get("cost_pct_alerts", []):
    for alert_pct in COST_ALERTS:
        if abs(cost_pct_rounded - alert_pct) < 0.25:  # 允许0.25%误差
            # 触发提醒
            profit_amount = (price - AVG_COST) * SHARES
            
            if alert_pct == 0:
                emoji = "➡️"
                msg_title = "回到成本线"
            elif alert_pct > 0:
                emoji = "💰"
                msg_title = f"盈利{alert_pct:.1f}%"
            else:
                emoji = "⚠️"
                msg_title = f"亏损{abs(alert_pct):.1f}%"
            
            msg = f"{emoji} 【成本线提醒 - {msg_title}】\n"
            msg += f"{STOCK_NAME} 现价 {price:.3f}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"📊 成本价 {AVG_COST:.3f}\n"
            msg += f"📊 成本涨幅 {cost_pct:+.1f}%\n"
            msg += f"💼 盈亏 {'+' if profit_amount >= 0 else ''}{profit_amount:.0f}元\n"
            
            send_wx(msg)
            state.setdefault("cost_pct_alerts", []).append(cost_pct_rounded)
            save_state(state)
            return
```

## 状态管理

```python
# 状态文件中需要记录已触发的成本涨幅提醒
state = {
    "alerted_types": [],
    "pct_alerts": [],        # 今日涨幅提醒
    "cost_pct_alerts": [],   # 成本涨幅提醒（新增）
    # ...
}

# 每天9:30重置时清空
if now.hour == 9 and now.minute >= 25 and now.minute <= 30:
    state = {
        # ...
        "cost_pct_alerts": [],  # 重置
    }
```

## 显示格式

```
📈 芯片ETF 159599

💰 现价 3.570  |  今日 +1.52%
━━━━━━━━━━━━━━━━━━━━
📊 成本分析
   成本价 3.528
   成本涨幅 +1.2%
   [▓░░░░░░░░░] 盈利
   距止盈 3.881（8.8%）
━━━━━━━━━━━━━━━━━━━━
💼 持仓盈亏
   持仓 8500股  市值 30345元
   盈亏 +357元
   持仓天数 1天
```

## 进度条实现

```python
# 成本线进度条
if cost_pct >= 0:
    progress = min(cost_pct / TAKE_PROFIT_PCT * 100, 100)
    bar = "▓" * int(progress / 10) + "░" * (10 - int(progress / 10))
    target_info = f"距止盈 {COST_TP:.3f}（{TAKE_PROFIT_PCT-cost_pct:.1f}%）"
else:
    progress = min(abs(cost_pct) / STOP_LOSS_PCT * 100, 100)
    bar = "▓" * int(progress / 10) + "░" * (10 - int(progress / 10))
    target_info = f"距止损 {COST_SL:.3f}（{STOP_LOSS_PCT-abs(cost_pct):.1f}%）"
```

## 常见错误

1. **❌ 用整数%提醒**：`round(cost_pct)` 会把0.5%变成0%或1%
2. **❌ 只显示今日涨幅**：用户需要同时看到成本涨幅
3. **❌ 不显示进度条**：可视化很重要，让用户一目了然

## 测试用例

成本3.528，现价3.546：
- 成本涨幅 = (3.546 - 3.528) / 3.528 * 100 = 0.51%
- 四舍五入到0.5% = 0.5
- 触发 +0.5% 提醒 ✅

成本3.528，现价3.563：
- 成本涨幅 = (3.563 - 3.528) / 3.528 * 100 = 0.99%
- 四舍五入到0.5% = 1.0
- 触发 +1.0% 提醒 ✅
