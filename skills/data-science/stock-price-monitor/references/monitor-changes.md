# 监控列表变更通知 — 实现细节

## 触发时机

Cronjob 每分钟运行一次，`check_monitor_changes()` 在 `pending_trades` 处理之后、收盘/交易时间检查之前调用。确保非交易时间的变更也能推送。

## 实现原理

状态文件中维护 `stocks_snapshot` 字段，记录上次运行的 STOCKS 快照：

```json
{
  "stocks_snapshot": {
    "159599": ["芯片ETF", "持仓"],
    "600114": ["东睦股份", "持仓"],
    "000920": ["沃顿科技", "观察"]
  }
}
```

每次运行对比当前 STOCKS (从脚本读取) vs snapshot：
- **新增**: code 在 STOCKS 但不在 snapshot → ➕ 推送
- **移除**: code 在 snapshot 但不在 STOCKS → ➖ 推送
- **type变化**: 同一 code 但 type 不同（观察↔持仓） → 🔄 推送

## 首次运行

首次运行时 snapshot 为空，只保存当前快照，不报警。后续运行才会对比。

## 每日重置时保留

`stocks_snapshot` 跨日保留（在 `main()` 的每日重置逻辑中不删除），否则每天第一次运行都会报"新增"。

## 调用位置

```python
def main():
    # ... 每日重置 ...
    
    # pending_trades 队列
    pending = state.get("pending_trades", [])
    if pending:
        for trade in pending:
            send_wx(trade["msg"])
        state["pending_trades"] = []
        save_state(state)
    
    # ⚠️ 监控变更检测 — 在收盘判断之前，确保非交易时间也推送
    change_msg = check_monitor_changes(state)
    if change_msg:
        send_wx(change_msg)
    
    # 收盘播报...
    # 交易时间检查...
```

## 多股票删除时的陷阱

**问题**: 用 patch 同时删除多只股票时，行号会偏移。如果从上往下删，第二只股票的匹配行号已经变了，patch 可能匹配到错误位置。

**✅ 正确做法**: 从 STOCKS 列表底部往上删。
- 例如删除 A(行120)、B(行180)、C(行240) → 先删 C，再删 B，最后删 A

## 变更后清理

删除股票后还需清理状态文件：
```python
for code in ['002141', '002245', '603078']:
    if code in state.get('alerted', {}):
        del state['alerted'][code]
    if code in state.get('prev_limit_up', {}):
        del state['prev_limit_up'][code]
    if code in state.get('prev_limit_down', {}):
        del state['prev_limit_down'][code]
```
