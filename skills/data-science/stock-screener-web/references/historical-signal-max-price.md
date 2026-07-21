# 历史信号最高价修复

## ⚠️ 三个独立代码路径都显示历史信号（重要！）

**用户术语映射**：
| 用户说的 | 实际系统 | 代码位置 | API端点 | 前端 |
|---------|---------|---------|---------|------|
| "主系统" | 分析平台 | `/home/jmy/.hermes/profiles/eastmoney-bot/` | `api/history.py` → `/api/history/report` | `static/js/app.js` |
| "看板的报告页" | 股票筛选器-报告 | `/home/jmy/stock-screener/` | `api/report.py` → `/api/report_data` | `templates/report.html` |
| "看板的历史信号页签" | 股票筛选器-历史 | `/home/jmy/stock-screener/` | `api/history.py` → `/api/history` | `templates/index.html` (history tab) |

**⚠️ 看板内部有两个独立页面显示历史信号**：
1. 报告页 `/report` → `api/report.py` 的 `_load_signals()` → `/api/report_data`
2. 主页侧边栏"📜 历史信号" → `api/history.py` 的 `api_history()` → `/api/history`

**三者共用同一个MySQL数据库，但代码完全独立。改了一个另一个不会自动生效。**

### 2026-06-26 教训
用户说"看板的"时，指的是看板侧边栏的"📜 历史信号"页签（用`/api/history`），不是`/report`报告页（用`/api/report_data`）。我只改了report页面，用户暴怒"你不要再气我了"。正确做法：不确定时两个都改。

## 问题描述

历史信号中，"最高价"显示的是**成交额最大**那天的价格，而不是**价格最高**那天的价格。

**⚠️ 三个代码路径都要改**：
1. 主系统"历史信号"页签 → `api/history.py` 的 `api_history()`
2. 看板 `/report` 报告页 → `/home/jmy/stock-screener/api/report.py` 的 `_load_signals()`
3. 看板主页"📜 历史信号"tab → `/home/jmy/stock-screener/api/history.py` 的 `api_history()`

### 示例（东方锆业002167）

| 日期 | latest_price | amount（成交额） |
|------|-------------|------------------|
| 06-24 | 21.46 | 61.79亿（最大）|
| 06-25 | 22.77 | 48.87亿 |
| 06-26 | 21.56 | 36.05亿 |

**错误显示**：最高价 = 21.46（成交额最大的价格）
**正确显示**：最高价 = 22.77（价格最高的日期）

## 根因

数据库视图 `v_scan_results_with_change` 中的 `max_amount_price` 字段是按成交额排序取的价格，不是价格最高的记录。

## 修复方案（两处都要改）

### 1. 主系统: api/history.py - api_history()

在查询rows后，额外查询stock_snapshot表获取历史最高价：

```python
# 获取所有股票代码
codes = list(set(row["ts_code"] for row in rows))

# 查询每只股票的历史最高价
max_price_map = {}
max_price_date_map = {}
if codes:
    with conn.cursor() as cur2:
        placeholders = ','.join(['%s'] * len(codes))
        cur2.execute(f"""
            SELECT ts_code, MAX(latest_price) as max_price
            FROM stock_snapshot
            WHERE ts_code IN ({placeholders})
            GROUP BY ts_code
        """, codes)
        for row in cur2.fetchall():
            max_price_map[row["ts_code"]] = float(row["max_price"])
        
        cur2.execute(f"""
            SELECT s.ts_code, s.latest_price, s.scan_time
            FROM stock_snapshot s
            INNER JOIN (
                SELECT ts_code, MAX(latest_price) as max_price
                FROM stock_snapshot
                WHERE ts_code IN ({placeholders})
                GROUP BY ts_code
            ) m ON s.ts_code = m.ts_code AND s.latest_price = m.max_price
        """, codes)
        for row in cur2.fetchall():
            code = row["ts_code"]
            if code not in max_price_date_map:
                max_price_date_map[code] = row["scan_time"].strftime("%Y-%m-%d") if row["scan_time"] else ""

# 在rows循环中添加字段
for row in rows:
    code = row.get("ts_code")
    first_price = float(row.get("latest_price", 0) or 0)
    max_price = max_price_map.get(code, 0)
    row["max_price"] = max_price
    row["max_price_date"] = max_price_date_map.get(code, "")
    if first_price > 0 and max_price > 0:
        row["max_gain"] = round((max_price - first_price) / first_price * 100, 2)
    else:
        row["max_gain"] = 0
```

### 2. 看板: /home/jmy/stock-screener/api/report.py - _load_signals()

同样的查询逻辑，代码几乎一样。

### 3. 主系统前端: static/js/app.js - loadHistory()

```javascript
const maxPriceDisplay = s.max_price ? '¥' + s.max_price : (s.max_amount_price ? '¥' + s.max_amount_price : '-');
const maxPriceDate = s.max_price_date || s.max_amount_date || '-';
const maxGainCls = (s.max_gain || 0) >= 0 ? 'up' : 'down';
const maxGainDisplay = s.max_gain !== null && s.max_gain !== undefined ? s.max_gain + '%' : maxAmountChangeDisplay;
```

### 4. 看板前端: templates/report.html

```javascript
<div class="sr-max">
  <div class="label">最高价</div>
  <div class="value">${parseFloat(s.max_price || 0).toFixed(2)}</div>
  <div class="date">${s.max_price_date || ''}</div>
</div>
<div class="sr-max-gain">
  <div class="label">最高涨幅</div>
  <div class="value ${maxGainCls}">${maxGainSign}${maxGain.toFixed(2)}%</div>
</div>
```

## ⚠️ 教训

1. **三个代码路径都要改** — 主系统、看板报告页、看板历史信号tab是完全独立的代码路径
2. **用户说"看板的"不一定是report页面** — 看板有两个页面显示历史信号，用户可能指的是侧边栏的"📜 历史信号"tab（用`/api/history`），不是`/report`报告页（用`/api/report_data`）。不确定时两个都改
3. **`max_amount_price` ≠ 最高价** — 视图字段按成交额取，不是按价格取
4. **改完必须重启Flask** — 模板和静态文件在启动时加载
5. **用户术语** — "主系统"=分析平台(eastmoney-bot)，"看板"=stock-screener，看板内有两个历史信号页面
