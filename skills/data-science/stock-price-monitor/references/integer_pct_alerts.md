# 整数涨跌幅提醒 — 穿越即推（2026-07-20重构）

## 机制

不再用alerted去重。改用`prev_pct_{code}`追踪上一次round值，每当round值变化时，遍历中间所有整数逐个推送。

```python
current_pct_int = round(change_pct)
prev_key = f"prev_pct_{key}"
prev_pct = state.get(prev_key)

if prev_pct is not None and current_pct_int != prev_pct:
    step = 1 if current_pct_int > prev_pct else -1
    for p in range(prev_pct + step, current_pct_int + step, step):
        if -10 <= p <= 10:
            send_wx(f"📈/📉 【{stock_name} {p:+d}%】\n现价 {price:.3f}...")
    state[prev_key] = current_pct_int
elif prev_pct is None:
    state[prev_key] = current_pct_int  # 首次记录，不推送
```

`prev_pct_*` 存在state顶层（非alerted内），每日重置时自然清空。

## 行为示例

- prev=+2% → +5%: 📈+3% 📈+4% 📈+5%（中间不漏）
- prev=+5% → +2%: 📉+4% 📉+3% 📉+2%
- prev=+2% → 再涨到+5%: 📈+3% 📈+4% 📈+5%（再次触发！）

## 教训

- ❌ 旧方案：alert_key去重 → 同一关口离开再回来不推
- ❌ 旧方案：只推当前值 → 跳涨时中间整数丢失
- ✅ 新方案：prev_pct追踪+遍历中间整数 → 全覆盖
