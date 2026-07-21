# 状态文件格式规范

## 正确格式（v2，嵌套结构）

```json
{
  "alerted": {
    "159599": ["pct_3", "cost_5.0", "rsi_overbought"],
    "002167": ["pct_2", "pct_5"]
  },
  "prev_limit_up": {"002167": false},
  "prev_limit_down": {"002167": false},
  "open_sent": false,
  "close_sent": false,
  "last_hourly": null,
  "today": "2026-06-25"
}
```

### 字段说明
- `alerted`: **嵌套字典**，key是股票代码（ts_code），value是已触发的提醒类型列表
- `prev_limit_up`: **嵌套字典**，记录上一次是否涨停（支持多次涨停/打开提醒）
- `prev_limit_down`: **嵌套字典**，记录上一次是否跌停（支持多次跌停/打开提醒）
- `open_sent`: 今日开盘播报是否已发送
- `close_sent`: 今日收盘播报是否已发送
- `last_hourly`: 上次整点播报的时间（如"10:00"）
- `today`: 今日日期（YYYY-MM-DD），用于每日状态重置

## 错误格式（v1，扁平结构，已废弃）

```json
{
  "alerted_types": ["warn_high", "hold_5days"],
  "last_price": 17.25,
  "open_sent": false,
  "close_sent": false,
  "pct_alerts": [1, 2, 3],
  "cost_pct_alerts": [0.5, 1.0],
  "last_hourly": "15:00"
}
```

### 为什么这个格式有问题
1. `alerted_types` 是扁平列表，无法区分不同股票的提醒状态
2. 脚本用 `state["alerted"][key]` 访问，但旧格式没有 `alerted` 字段
3. 多股票监控时，提醒状态会互相干扰

## 每日状态重置

脚本必须在 `main()` 开头检查日期，新的一天自动清空：

```python
today_str = now.strftime("%Y-%m-%d")
if state.get("today") != today_str:
    state = {
        "alerted": {},
        "prev_limit_up": {},
        "prev_limit_down": {},
        "open_sent": False,
        "close_sent": False,
        "last_hourly": None,
        "today": today_str
    }
    save_state(state)
```

### 没有重置逻辑的后果
- 旧的 `alerted` 记录一直保留
- 当天的提醒被跳过（因为 key 已存在）
- 用户看不到任何推送，以为系统挂了

## 调试命令

```bash
# 查看当前状态
cat /home/jmy/.hermes/profiles/eastmoney-bot/.monitor_state.json | python3 -m json.tool
```bash
# 重置状态（紧急修复）
cat > /home/jmy/.hermes/profiles/eastmoney-bot/.monitor_state.json << 'EOF'
{
  "alerted": {},
  "prev_limit_up": {},
  "prev_limit_down": {},
  "open_sent": false,
  "close_sent": false,
  "last_hourly": null,
  "today": null
}
EOF
```
