# target_buy 增强推送格式 (2026-07-16)

## 触发条件

用户要求 target_buy 推送不能只报价格，必须包含：
1. 为什么现在买入？（买入理由）
2. 买入区间是否合理？（技术面验证）
3. 买入后 T+1 能否盈利？（T+1 判断）

## 推送消息格式

```
🎯 【{name} 触发买入信号！】

💰 现价 {price:.3f}  ≤  目标 {target:.2f}
   今日 {change_pct:+.2f}%  |  最高 {high:.3f}  最低 {low:.3f}

📈 技术面
   RSI(14) = {rsi:.1f}  {label}
   MA5={ma5:.3f}  MA10={ma10:.3f}  MA20={ma20:.3f}
   距MA20: {dist_ma20:+.1f}%
   10日区间: {low_10d:.3f} ~ {high_10d:.3f}
   近5日: {week_chg:+.1f}%

💵 买入计划
   仓位: {shares}股 × {price:.3f} = {amount:.0f}元
   止盈: {tp_price:.3f} (+{tp_pct}%)  |  止损: {sl_price:.3f} (-{sl_pct}%)
   🔁 回本价: {breakeven:.2f} (需涨{be_pct:.1f}%，累计亏{loss}元)  ← 仅亏损股

📅 T+1: 今天{weekday}，{next_day}即可卖出
   或 ⚠️ T+1: 今天是周五，买入后下周一才能卖出（锁仓3天），注意周末风险！

💡 买入理由: RSI极度超卖 + 跌破MA20达{ma20_gap}% + 近5日跌{week_chg}%，技术性反弹概率大
━━━━━━━━━━━━━━━━━━━━
```

## 技术实现

### get_kline_analysis(code) 函数
汇聚 K 线技术分析数据，一次 API 调用返回所有指标：

```python
def get_kline_analysis(code):
    """返回 {rsi, ma5, ma10, ma20, low_10d, high_10d, low_20d, week_chg}"""
    # 调用 push2his API 获取近30日K线
    # 从 closes/highs/lows 计算各项指标
    # 返回 dict，失败返回 None
```

### LOSS_HISTORY 字典
脚本顶部维护历史累计亏损，用于推送时自动计算回本价：

```python
LOSS_HISTORY = {
    "600114": {"loss": 626, "name": "东睦股份"},
    "518880": {"loss": 273, "name": "黄金ETF"},
}
```

每笔清仓后更新此字典，买入后清除对应条目。

### 推送节流
- 首次触发：立即推送
- 后续触发：距上次推送 ≥ 5 分钟才重推
- 状态 key 格式：`target_buy_HH:MM`（带时间戳）
- 每日重置后重新开始

### RSI 标签
```python
rsi_label = "🔴极度超卖" if rsi < 30 else ("🟡偏低" if rsi < 40 else ("✅正常" if rsi < 70 else "⚠️偏高"))
```

### 买入理由自动生成
```python
reasons = []
if rsi and rsi < 30: reasons.append("RSI极度超卖")
if ma20 and price < ma20 and dist > 10: reasons.append(f"跌破MA20达{dist:.0f}%")
if week_chg and week_chg < -5: reasons.append(f"近5日跌{abs(week_chg):.0f}%")
# 拼接: "💡 买入理由: {reasons}，技术性反弹概率大"
```

## 注意事项
- get_kline_analysis 在 cronjob 每轮都调用，K线 API 有频率限制但 4 只股票 1 分钟一次可接受
- 失败时静默降级：rsi/ma 字段为 None 时跳过对应行
- 板块资金（rc=102）和新闻（反爬）在 cronjob 中不可用，忽略
