# 做T目标价监控实现

## 原理

补仓后设置T卖出目标价，cronjob每分钟检查，价格到了自动推企微。

## State文件 (`.monitor_state.json`)

```json
{
  "t_targets": {
    "159599": {"target": 3.12, "shares": 200, "buy_price": 2.974, "note": "做T卖出：补200@2.974→卖200@3.12"},
    "600114": {"target": 28.55, "shares": 300, "buy_price": 27.19, "note": "做T卖出：补300@27.19→卖300@28.55"},
    "600888": {"target": 10.06, "shares": 200, "buy_price": 9.58, "note": "做T卖出：补200@9.58→卖200@10.06"}
  }
}
```

## price_monitor.py 检查逻辑

在 `main()` 的股票循环中，持仓天数检查之后、target_buy检查之前：

```python
t_targets = state.get("t_targets", {})
if key in t_targets and stock.get("cost"):
    t_info = t_targets[key]
    t_target_price = t_info["target"]
    alert_key = f"t_sell_{t_target_price}"
    if price >= t_target_price and alert_key not in state["alerted"].get(key, []):
        send_wx(f"🎯 【{stock['name']} 做T目标到达！】\n..."
```

## T目标价设置规则

- **目标价 = 补仓价 × 1.05**（反弹5%为最低目标）
## 做T完成后清理

- 做T卖出后，从state中清除该股的t_targets条目
- 如果只卖了部分（如计划300股只卖了200），保留t_targets继续监控剩余100股
