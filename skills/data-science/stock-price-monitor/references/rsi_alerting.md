# RSI主动预警实现指南

## 背景教训（2026-06-23）

用户持仓科安达，RSI达到93.4极度超买，但监控脚本没有预警。用户质问："既然都让你盯盘了，还出现这种情况"。

**核心问题：** 监控脚本只盯价格，没有盯技术指标。

## 解决方案

### 1. 实时RSI计算函数

```python
def calculate_rsi(closes, period=14):
    """实时计算RSI"""
    if len(closes) < period + 1:
        return None
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

### 2. 获取实时RSI

```python
def get_realtime_rsi():
    """获取实时RSI"""
    try:
        from services.kline import get_kline_data
        result = get_kline_data('002972', limit=30)
        if result and 'klines' in result:
            klines = result['klines']
            closes = [k['close'] for k in klines]
            rsi = calculate_rsi(closes)
            if rsi is not None:
                return rsi
    except Exception as e:
        print(f"实时RSI计算失败: {e}")
    
    # 回退到缓存的RSI
    tech = get_tech_indicators()
    return tech.get("rsi", 70)
```

### 3. RSI预警逻辑

```python
# 在main()函数中，整数涨跌幅提醒之后、止盈触发之前
current_rsi = get_realtime_rsi()
if current_rsi is not None:
    # RSI > 90 极度超买
    if current_rsi > 90 and "rsi_extreme_overbought" not in state.get("alerted_types", []):
        msg = f"🔴 【RSI极度超买警告！】\n"
        msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 RSI(14) = {current_rsi:.1f}\n"
        msg += f"⚠️ 极度超买信号！历史上很少见\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🎯 建议立即减仓 {SHARES//2}股\n"
        msg += f"   回调概率极大，落袋为安\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 当前持仓盈亏\n"
        msg += f"   盈利 {(price-AVG_COST)*SHARES:.0f}元（+{(price-AVG_COST)/AVG_COST*100:.1f}%）"
        send_wx(msg)
        state["alerted_types"].append("rsi_extreme_overbought")
        save_state(state)
        return
    
    # RSI > 80 超买警告
    elif current_rsi > 80 and "rsi_overbought" not in state.get("alerted_types", []):
        msg = f"⚠️ 【RSI超买警告】\n"
        msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 RSI(14) = {current_rsi:.1f}\n"
        msg += f"📈 处于超买区间（>80）\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💡 建议：考虑减仓或设置止盈\n"
        msg += f"   当前盈利 {(price-AVG_COST)/AVG_COST*100:+.1f}%"
        send_wx(msg)
        state["alerted_types"].append("rsi_overbought")
        save_state(state)
        return
    
    # RSI < 20 超卖机会
    elif current_rsi < 20 and "rsi_oversold" not in state.get("alerted_types", []):
        msg = f"🟢 【RSI超卖机会】\n"
        msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 RSI(14) = {current_rsi:.1f}\n"
        msg += f"📉 处于超卖区间（<20）\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💡 建议：可考虑补仓或建仓\n"
        msg += f"   当前盈利 {(price-AVG_COST)/AVG_COST*100:+.1f}%"
        send_wx(msg)
        state["alerted_types"].append("rsi_oversold")
        save_state(state)
        return
```

### 4. 每日状态重置

```python
# 每天9:30重置状态时，加入rsi_alerts
if now.hour == 9 and now.minute >= 25 and now.minute <= 30:
    state = {
        "alerted_types": [], "last_hourly": None, "last_price": price,
        "open_sent": False, "close_sent": False, "pct_alerts": [],
        "rsi_alerts": [],  # RSI预警每日重置
    }
```

## 推送消息示例

### RSI > 90 极度超买
```
🔴 【RSI极度超买警告！】
科安达 现价 17.23
━━━━━━━━━━━━━━━━━━━━
📊 RSI(14) = 93.4
⚠️ 极度超买信号！历史上很少见
━━━━━━━━━━━━━━━━━━━━
🎯 建议立即减仓 200股
   回调概率极大，落袋为安
━━━━━━━━━━━━━━━━━━━━
📊 当前持仓盈亏
   盈利 +315元（+4.8%）
```

### RSI > 80 超买警告
```
⚠️ 【RSI超买警告】
科安达 现价 17.23
━━━━━━━━━━━━━━━━━━━━
📊 RSI(14) = 85.2
📈 处于超买区间（>80）
━━━━━━━━━━━━━━━━━━━━
💡 建议：考虑减仓或设置止盈
   当前盈利 +4.8%
```

### RSI < 20 超卖机会
```
🟢 【RSI超卖机会】
科安达 现价 15.50
━━━━━━━━━━━━━━━━━━━━
📊 RSI(14) = 18.5
📉 处于超卖区间（<20）
━━━━━━━━━━━━━━━━━━━━
💡 建议：可考虑补仓或建仓
   当前盈利 -5.7%
```

## 关键原则

1. **主动推送，不要被动等待** — RSI>90必须立即推送
2. **极端信号优先于一般规则** — RSI>90时，"持仓5天"等规则可以忽略
3. **用户依赖你盯盘** — 既然让用户信任你的监控，就要做好预警工作
4. **每日重置状态** — 确保第二天可以重新提醒

## 相关文件

- 主脚本：`scripts/price_monitor.py`
- 技能文档：`stock-price-monitor` skill
- 交易系统：`stock-trading-system` skill
