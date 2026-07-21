# 基金015690盘中推送 — 多时段cronjob + 偏差追踪 + 持仓盈亏

## 基金信息

- 代码: 015690
- 名称: 富国中小盘精选混合C
- 数据源: 天天基金 `fundgz.1234567.com.cn/js/015690.js`

## ⚠️ 关键修复：NO_PROXY 必须设置

天天基金API同样需要 `os.environ['NO_PROXY'] = '*'`，否则cronjob环境走HTTP_PROXY代理会导致超时。

```python
os.environ['NO_PROXY'] = '*'
url = "https://fundgz.1234567.com.cn/js/015690.js"
```

**症状**：cronjob显示ok但无推送，手动运行正常。根因和东财API一样——代理超时。

## 持仓盈亏配置

在脚本中硬编码持仓参数（份额不会变）：

```python
TOTAL_INVEST = 15000        # 累计投入
FUND_SHARES = 1847.8804     # 份额
COST_NAV = 8.1174           # 成本净值
```

### 份额计算方法

当用户只知道「投入金额」和「按某日净值算的累计亏损」时：

```python
# 已知: 投入15000, 按昨日dwjz=7.5390算亏损-1068.83
# 份额 = (投入 + 亏损) / dwjz
shares = (15000 + (-1068.83)) / 7.5390  # = 1847.8804
# 成本净值 = 投入 / 份额
cost_nav = 15000 / shares  # = 8.1174
```

### 盈亏计算

每次推送实时计算：

```python
today_value = FUND_SHARES * gsz_val       # 今日市值
yesterday_value = FUND_SHARES * dwjz_val   # 昨日市值
today_pnl = today_value - yesterday_value  # 今日盈亏
total_pnl = today_value - TOTAL_INVEST     # 累计盈亏
```

## Cronjob配置（4个）

| 时间 | 名称 | 用途 |
|------|------|------|
| 11:30 | 基金015690-午间休市 | 上午收盘快照 |
| 13:00 | 基金015690-下午开盘 | 下午开盘净值 |
| 14:30 | 基金015690-尾盘30分钟 | 收盘前最后估值 |
| 15:05 | 基金015690-盘后推送 | 收盘确认+保存偏差数据 |

创建命令:
```bash
hermes cron create --name "基金015690-午间休市" --schedule "30 11 * * 1-5" --script fund_015690.py --no-agent
hermes cron create --name "基金015690-下午开盘" --schedule "0 13 * * 1-5" --script fund_015690.py --no-agent
hermes cron create --name "基金015690-尾盘30分钟" --schedule "30 14 * * 1-5" --script fund_015690.py --no-agent
```

## 偏差追踪机制

收盘时(15:05)保存当日`gsz`(估算净值)到`.fund_state.json`。
次日运行时对比`dwjz`(实际净值)与昨日保存的`gsz`，计算偏差。

```json
{
  "prev_estimate": {"gsz": "7.5366", "gszzl": "-1.52", "time": "2026-07-16 15:00"},
  "prev_estimate_date": "2026-07-16"
}
```

偏差公式: `deviation = prev_gsz - actual_dwjz`
偏差百分比: `dev_pct = (prev_gsz / actual_dwjz - 1) * 100`

## 推送消息格式

```
📊 收盘确认 — 富国中小盘精选混合C 015690

📅 净值日期: 2026-07-16
📌 昨日净值: 7.5390
📈 今日估算: 7.0864  (-6.00%)
⏰ 估值时间: 2026-07-17 11:30

💰 持仓 1848份 × 成本8.1174
   今日市值: 13,094.82
   今日盈亏: -836.35
   累计亏损: -1,905.18

⚠️ 昨日预测偏差: +0.0123 (+0.16%)
   估算 7.6653 → 实际 7.6530
```

## 注意事项

- 首次运行时没有历史数据，不显示偏差
- 偏差来自基金持仓披露滞后（基于上季度持仓估算）
- 非交易日不运行（cronjob schedule 包含 `1-5`）
- 脚本静默运行（无print），只有企微收到消息
- **份额固定不变**，用户追加投资需手动更新 FUND_SHARES 和 TOTAL_INVEST
- API 返回的 `gszzl` 是估算涨跌幅（相对昨日净值），`gsz` 是估算净值
