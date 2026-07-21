# target_buy 推送增强 — 技术实现参考

## 设计原则

1. **首次立即推 + 每5分钟重复** — 防止V反错过窗口
2. **推送必须含完整分析** — RSI/MA/布林/回本价/T+1/买入理由
3. **所有观察股必须设target_buy** — 用户明确要求

## get_kline_analysis() 函数

一次K线API请求返回综合技术指标，避免多次请求触达限流：

```python
def get_kline_analysis(code):
    """获取K线技术分析：RSI + MA + 近期高低点"""
    try:
        secid_map = {"0.002167": "0.002167", "0.159599": "0.159599", 
                     "1.518880": "1.518880", "1.600114": "1.600114", 
                     "1.600888": "1.600888"}
        secid = secid_map.get(code, code)
        url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?..."
        # ... 返回 dict:
        # {"rsi": float, "ma5": float, "ma10": float, "ma20": float,
        #  "low_10d": float, "high_10d": float, "week_chg": float}
    except:
        return None
```

## LOSS_HISTORY 亏损记录

```python
LOSS_HISTORY = {
    "600114": {"loss": 626, "name": "东睦股份"},
    "518880": {"loss": 273, "name": "黄金ETF"},
}
```

回本价计算：`breakeven = price + loss / shares`

## target_buy 设置规则

| 规则 | 说明 |
|------|------|
| 不设整数关口 | 3.30 → 改用3.33，留缓冲 |
| 支撑位上留余地 | 前低10.37 → target设10.45 |
| target_shares必填 | 不能用公式兜底，可能算出错误股数 |
| 每5分钟重复推 | 直到用户买入，手动关闭 |

## 推送消息模板

```
🎯 【{name} 触发买入信号！】

💰 现价 {price} ≤ 目标 {target}
   今日 {change_pct}% | 最高 {high} 最低 {low}

📈 技术面
   RSI(14) = {rsi}  {rsi_label}
   MA5={ma5} MA10={ma10} MA20={ma20}
   距MA20: {dist_ma20}%
   10日区间: {low_10d} ~ {high_10d}
   近5日: {week_chg}%

💵 买入计划
   仓位: {shares}股 × {price} = {amount}元
   止盈: {tp} (+{tp_pct}%) | 止损: {sl} (-{sl_pct}%)
   🔁 回本价: {breakeven} (需涨{be_pct}%，累计亏{loss}元)

📅 T+1: {today} → {unlock_day}
   {weekend_warning}

💡 买入理由: {reasons}
━━━━━━━━━━━━━━━━━━━━
```
