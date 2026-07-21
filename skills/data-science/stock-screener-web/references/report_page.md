# 市场日报页面 (/report)

## 概述
用于论坛截图的独立报告页面，展示大盘指数、板块资金流向、历史信号详情。

## 文件结构
- `api/report.py` - 报告API，聚合数据
- `templates/report.html` - 报告页面模板

## 数据源
- 大盘指数：新浪API (`get_market_indices()`)
- 板块资金流向：**必须使用 `fetch_sector_flow()` 函数**（和今日看点一样）
- 历史信号：`v_scan_results_with_change` 视图

### ⚠️ 报表页面缓存优化（重要）
报表页面 `/report` 应优先从 `daily_digest_cache` 表读取已保存的今日看点数据，而不是每次都调用东财API。

**问题**：报表页面每次加载都调用 `fetch_sector_flow()` 实时获取，导致加载缓慢。

**正确做法**：
```python
# 优先从已保存的今日看点读取
if not force:
    cached = load_daily_digest(date_str)
    if cached and cached.get("inflow_sectors"):
        # 直接使用缓存数据，秒加载
        result["from_cache"] = True
        # ... 转换缓存数据格式
        return jsonify(result)

# 没有缓存才实时获取
inflow_sectors = fetch_sector_flow("industry", "f62", 5, ascending=False)
```

**关键点**：
- 今日看点保存后，报表页面应该秒加载
- 支持 `?force=true` 参数强制实时获取
- 返回 `from_cache: true` 标记数据来源

### ⚠️ 板块资金流向数据源（关键）
**不要**直接查询 `sector_flow` 表！数据可能不完整或格式不对。

正确做法（和 `api/daily.py` 一致）：
```python
from services.sector_flow import fetch_sector_flow

# 流入 TOP5（降序）
inflow_sectors = fetch_sector_flow("industry", "f62", 5, ascending=False)

# 流出 TOP5（升序，负值最大的在前）
outflow_sectors = fetch_sector_flow("industry", "f62", 5, ascending=True)
```

这是两次独立的API调用，不要合并成一次然后拆分！
- `ascending=False` → 返回正值最大的（流入最多）
- `ascending=True` → 返回负值最大的（流出最多）

## 信号列表设计（卡片式布局 2026-06-25）

信号列表用CSS grid卡片式布局，不用`<table>`。卡片布局更清晰、hover效果好、NEW标签不会撑破布局。

### HTML结构
```html
<div class="signal-list">
  <div class="signal-row latest">
    <div class="sr-code">
      <span class="new-tag">NEW</span>
      <div>
        <div class="code">600162</div>
        <div class="name">香江控股</div>
      </div>
    </div>
    <div class="sr-info">
      <span class="version new">新版本</span>
      <span class="dates">2026-06-03</span>
    </div>
    <div class="sr-price"><div class="label">发现价</div><div class="value fp">2.92</div></div>
    <div class="sr-price"><div class="label">数据价</div><div class="value dp">3.50</div></div>
    <div class="sr-change">↑ +19.86%</div>
    <div class="sr-gain up">+19.86%</div>
  </div>
</div>
```

### CSS Grid布局
```css
.signal-list { display: flex; flex-direction: column; gap: 8px; }
.signal-row {
  display: grid;
  grid-template-columns: 90px 1fr 70px 80px 80px 80px;
  align-items: center;
  background: #0f172a;
  border-radius: 8px;
  padding: 10px 14px;
  border: 1px solid #1e293b;
  transition: all 0.2s;
  gap: 8px;
}
.signal-row:hover { border-color: #3b82f6; background: #131c2e; }
.signal-row.latest {
  background: linear-gradient(90deg, rgba(59,130,246,0.12) 0%, #0f172a 100%);
  border-color: #3b82f6;
  border-left: 3px solid #3b82f6;
}
```

### 亮色主题覆盖
```css
body.light .signal-row { background: #ffffff; border-color: #e2e8f0; }
body.light .signal-row:hover { border-color: #3b82f6; background: #f8fafc; }
body.light .signal-row.latest { background: linear-gradient(90deg, rgba(59,130,246,0.08) 0%, #ffffff 100%); border-color: #93c5fd; border-left-color: #3b82f6; }
body.light .signal-row .sr-code .code { color: #2563eb; }
body.light .signal-row .sr-code .name { color: #475569; }
body.light .signal-row.latest .sr-code .code { color: #1d4ed8; }
body.light .signal-row.latest .sr-code .name { color: #1e293b; }
body.light .signal-row .sr-now .value { color: #1e293b; }
body.light .signal-row .sr-gain.up { color: #dc2626; }
body.light .signal-row .sr-gain.down { color: #16a34a; }
```

## 信号表格列设计（用户最终确认）
| 列名 | 数据字段 | 说明 |
|------|----------|------|
| 代码 | ts_code | 股票代码 |
| 名称 | stock_name | 股票名称 |
| 数据日期 | data_date | 扫描日期（紫色高亮） |
| 数据价格 | data_price | 扫描时的价格（紫色高亮） |
| 首次发现 | first_discovery_date | 入库日期 |
| 首次价格 | first_price | 入库时的价格（黄色高亮） |
| 距离首期 | change_pct | 本期数据价格 vs 首期数据价格 |
| 现价 | latest_snap_price | 最新快照价 |
| 累计涨跌(据首次) | gain_since | 首次发现价格 vs 当日快照价格 |

**列顺序说明**：
- 数据日期/数据价格 在 首次发现/首次价格 前面（用户偏好：近期数据优先展示）
- 距离首期 在 现价 前面（先看涨跌幅，再看绝对价格）

## 涨跌计算逻辑
```python
# 距离首期 = 本期数据价格 vs 首期数据价格（NOT 现价！）
data_price = signal["data_price"]
if first_price > 0 and data_price > 0:
    signal["change_pct"] = round((data_price - first_price) / first_price * 100, 2)
else:
    signal["change_pct"] = 0

# 累计涨跌(据首次) = 首次发现价格 vs 当日快照价格
snap_price = signal["latest_snap_price"]
if first_price > 0 and snap_price > 0:
    signal["gain_since"] = round((snap_price - first_price) / first_price * 100, 2)
```

### ⚠️ 距离首期计算陷阱（重要）
**错误理解**：距离首期 = 现价 vs 首次发现价格
**正确理解**：距离首期 = 本期数据价格 vs 首期数据价格

- `data_price` 是扫描时的价格（本期数据）
- `first_price` 是首次入库时的价格（首期数据）
- `latest_snap_price` 是最新快照价（现价）

用户原话："距离首期的意思是这期的数据价格和首期的数据价格"

## 排序规则
- 净流入TOP5：按 `main_net_inflow DESC`
- 净流出TOP5：按 `main_net_inflow ASC`（取负值最大的5个）
- 信号表格：按 `data_date DESC`，只显示最新10条

## 板块领涨/领跌股显示
参考今日看点页面，每个板块需要显示领涨/领跌股信息：

### API返回数据结构
`fetch_sector_flow()` 返回的每个板块包含：
```python
{
    "sector_code": "BK1201",
    "sector_name": "电子",
    "main_net_inflow": 994317.1072,  # 万元
    "change_pct": 1.35,
    "lead_stock": "000725",
    "lead_stock_name": "京东方Ａ",
    "lead_stock_pct": 10.02,
    "lag_stock": "002866",
    "lag_stock_name": "传艺科技",
    "lag_stock_pct": -10.0
}
```

### report.py 需要返回的字段
```python
# 流入板块
result["sector_flow"]["top_inflow"].append({
    "name": s["sector_name"],
    "net_inflow": round(float(s["main_net_inflow"]) / 10000, 2),
    "change_pct": round(float(s.get("change_pct", 0)), 2),
    "lead_stock_name": s.get("lead_stock_name", ""),
    "lead_stock_pct": round(float(s.get("lead_stock_pct", 0)), 2),
})

# 流出板块
result["sector_flow"]["top_outflow"].append({
    "name": s["sector_name"],
    "net_inflow": round(float(s["main_net_inflow"]) / 10000, 2),
    "change_pct": round(float(s.get("change_pct", 0)), 2),
    "lag_stock_name": s.get("lag_stock_name", ""),
    "lag_stock_pct": round(float(s.get("lag_stock_pct", 0)), 2),
})
```

### 前端显示格式
```javascript
// 流入板块
`领涨: ${s.lead_stock_name || '-'} <span class="${s.lead_stock_pct > 0 ? 'up' : 'down'}">${s.lead_stock_pct > 0 ? '+' : ''}${s.lead_stock_pct}%</span>`

// 流出板块
`领跌: ${s.lag_stock_name || '-'} <span class="${s.lag_stock_pct > 0 ? 'up' : 'down'}">${s.lag_stock_pct > 0 ? '+' : ''}${s.lag_stock_pct}%</span>`
```

## 视觉规范
- 信号列表用卡片式布局（CSS grid `.signal-row`），不是table
- 最新一行：蓝色渐变背景 + 左侧蓝色边框 + 内联`NEW`标签 + 字体加粗高亮
- 首次价格：黄色 (`#fbbf24`)
- 数据价格：紫色 (`#a78bfa`)
- 不显示金叉标签（用户明确要求去掉）
- 涨跌列标题用 `<small>` 标签标注说明

### 最新一行高亮样式（旧版table方案，已被卡片布局替代）
⚠️ **此样式用于旧版`<table>`方案**。当前信号列表已改用卡片式布局（见上方"信号列表设计"章节）。此段保留供盈利统计表参考。

```css
.signal-table tr.latest {
  background: linear-gradient(90deg, rgba(59,130,246,0.15) 0%, rgba(59,130,246,0.05) 100%);
}
.signal-table tr.latest td {
  border-bottom: 2px solid #3b82f6;
  font-weight: 600;
}
.signal-table tr.latest .code { color: #93c5fd; }
.signal-table tr.latest .name { color: #fff; }
.signal-table .new-tag {
  display: inline-block;
  font-size: 9px;
  background: #3b82f6;
  color: #fff;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 700;
  margin-right: 4px;
  vertical-align: middle;
}

/* 亮色主题 */
body.light .signal-table tr.latest {
  background: linear-gradient(90deg, rgba(59,130,246,0.12) 0%, rgba(59,130,246,0.03) 100%);
}
body.light .signal-table tr.latest .code { color: #2563eb; }
body.light .signal-table tr.latest .name { color: #1e40af; font-weight: 700; }
body.light .signal-table .new-tag { background: #3b82f6; color: #fff; }
```

JS渲染（在代码列内嵌入NEW标签）：
```javascript
<td class="code">${isLatest ? '<span class="new-tag">NEW</span>' : ''}${s.ts_code}</td>
```

## 字体规范（截图清晰度优化）
用户要求字体够大以确保截图清晰（用于论坛分享）。以下为确认的字号：

| 区域 | 元素 | 字号 |
|------|------|------|
| 指数卡片 | 名称 | 13px |
| 指数卡片 | 价格 | 18px |
| 指数卡片 | 涨跌幅 | 14px |
| 板块区域 | 标题（净流入/流出TOP5） | 14px |
| 板块列表 | 名称/金额 | 14px |
| 板块列表 | 排名数字 | 13px |
| 信号表格 | 表头 | 13px |
| 信号表格 | 内容 | 14px |
| 信号表格 | 日期列 | 12px |
| 页脚 | 版权/水印 | 13px |

**原则**：宁大勿小，用户截图发论坛需要清晰可读。

## 用户偏好
- 只显示10条信号记录
- 列要精简，不要太多
- 数据日期只要日期，不要时间
- 净流出按绝对值排序（绝对值大的排第一）
- 最新一行要有颜色提醒（NEW标签+渐变背景+加粗）
- 金叉字符不要显示
- 水印：枫月的大论坛1022949553（全屏铺满，半透明）
- 信号列表用卡片式布局（CSS grid），不用table
- NEW标签用内联span，不用::before伪元素（会撑破表格）
- 截图时保留水印，只隐藏按钮
- 计算逻辑说明框必须跟随亮暗主题切换

## 盈利统计模块（扫描系统本月战绩）

### 位置
在板块资金流向和历史信号之间。

### API
`/api/scan/monthly-profit`（`api/scan_profit.py`）

### 前端结构
```html
<div class="section-title">📊 扫描系统本月战绩</div>
<div class="profit-summary" id="profit-summary"></div>
<div style="padding: 0 20px 4px;">
  <div id="profit-calc-logic" style="..."></div>
</div>
<div id="profit-table-wrap"></div>
```

### 汇总卡片（4列grid）
- 本月信号：蓝色数字
- 胜率：>=50%绿色，<50%红色
- 平均涨幅：正绿负红
- 盈利/亏损：X胜Y负

### 计算逻辑说明框
```css
/* 暗色 */
background: #0f172a; border: 1px solid #1e293b; color: #475569;
/* 亮色 */
body.light #profit-calc-logic { background: #f8fafc !important; border-color: #e2e8f0 !important; color: #475569 !important; }
```

### ⚠️ 新增元素必须同步添加亮色覆盖
用户会主动切换主题检查，漏掉任何元素都会被发现。包括：
- 盈利统计卡片 `.profit-card`
- 盈利明细表格 `.profit-table`
- 计算逻辑说明框 `#profit-calc-logic`

```css
body.light .profit-card { background: #ffffff; border-color: #e2e8f0; }
body.light .profit-card .label { color: #64748b; }
body.light .profit-table { background: #ffffff; }
body.light .profit-table th { background: #f1f5f9; color: #475569; }
body.light .profit-table td { border-color: #e2e8f0; color: #334155; }
body.light .profit-table .name { color: #1e293b; }
body.light .profit-table .code { color: #3b82f6; }
body.light #profit-calc-logic { background: #f8fafc !important; border-color: #e2e8f0 !important; color: #475569 !important; }
```

### ⚠️ 板块资金流向必须用 fetch_sector_flow()
**错误做法**：直接查 `sector_flow` 表
```python
# ❌ 错误
cur.execute("SELECT * FROM sector_flow WHERE sector_type='industry' ORDER BY main_net_inflow DESC LIMIT 5")
```

**正确做法**：用 `fetch_sector_flow()` 函数
```python
# ✅ 正确
from services.sector_flow import fetch_sector_flow
inflow_sectors = fetch_sector_flow("industry", "f62", 5, ascending=False)
outflow_sectors = fetch_sector_flow("industry", "f62", 5, ascending=True)
```

原因：
1. `sector_flow` 表可能没有负值数据（流出数据）
2. `fetch_sector_flow()` 直接调用东财API，数据最准确
3. 和"今日看点"页面保持一致

### ⚠️ 前端显示 vs 后端查询分离
用户明确要求：**前端显示改动不要改后端数据查询逻辑**。
比如"净流出按绝对值排序"应该在前端JS做 `outflow.sort((a,b) => Math.abs(b.net_inflow) - Math.abs(a.net_inflow))`
后端保持 `fetch_sector_flow("industry", "f62", 5, ascending=True)`
错误做法：在SQL里加 `WHERE main_net_inflow < 0` 或改 `ORDER BY ABS(...)` 会导致数据丢失

### ⚠️ 信号数据分组计算
计算涨跌时必须按股票分组，不能直接对所有记录排序：
1. 先 `ORDER BY ts_code, data_date ASC` 获取所有记录
2. 按 `ts_code` 分组到 `stock_map`
3. 每只股票内计算 `change_pct`（当前data_date价格 vs 上一个data_date价格）
4. 最后取最新的10条

### ⚠️ 现价数据源：用 stock_snapshot，不要造新表（2026-06-29 血泪教训）
**走过的弯路**：发现历史信号"现价"不准→先尝试实时调东财API→性能差→建 signal_price_history 表+定时同步→用户指出 stock_snapshot 早已存了所有股票价格→删掉新表直接用 stock_snapshot。

**正确做法**：
```python
# ✅ 从 stock_snapshot 取今日价格（扫描时已存，3198条）
cur.execute("""
    SELECT ts_code, latest_price, change_pct
    FROM stock_snapshot
    WHERE ts_code IN ({placeholders})
    AND DATE(scan_time) = CURDATE()
""")
```

**原因**：双版本对比扫描每页都会调用 `save_snapshot_batch()` 存所有股票价格（在第一轮筛选之前），stock_snapshot 天然有当天所有扫描股的价格。不需要额外建表或调API。

### ⚠️ Flask应用重启
修改 `api/report.py` 或 `templates/report.html` 后需要重启Flask：
```bash
pkill -f "python.*app.py"
cd /home/jmy/stock-screener && python app.py &
```
浏览器可能有缓存，需要强制刷新。

### ⚠️ 前端缓存标志陷阱（重要）
**问题**：使用 `from_cache` 作为缓存有效性判断条件会导致缓存失效。

```javascript
// ❌ 错误：from_cache=true 的数据被认为是"无效缓存"
if (!forceRefresh && tabDataCache['daily'] && !tabDataCache['daily'].from_cache) {
    // 永远不会执行，因为从DB加载的数据 from_cache=true
}

// ✅ 正确：只检查缓存是否存在
if (!forceRefresh && tabDataCache['daily']) {
    dailyData = tabDataCache['daily'];
    renderDailyDigest(dailyData);
    return;
}
```

**原因**：
- `from_cache` 只是标记数据来源（缓存 vs 实时），不应影响缓存有效性
- 从 MySQL 加载的数据 `from_cache=true`，但仍是有效数据
- 正确逻辑：只要缓存存在且不强制刷新，就使用缓存

### ⚠️ 全屏铺满水印实现（JavaScript动态生成）
用户要求水印**铺满整个屏幕**，不是只有一两个居中的水印。用JS动态生成多个水印元素。

```css
.watermark-overlay {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;  /* 关键：不阻挡点击 */
    z-index: 9999;
    overflow: hidden;
    display: flex;
    flex-wrap: wrap;
    align-content: flex-start;
}
.watermark-item {
    width: 300px;
    height: 150px;
    display: flex;
    align-items: center;
    justify-content: center;
    transform: rotate(-35deg);
    flex-shrink: 0;
}
.watermark-item span {
    font-size: 16px;
    color: rgba(30, 64, 175, 0.1);  /* 半透明 */
    font-weight: 600;
    white-space: nowrap;
    letter-spacing: 2px;
    user-select: none;
}
```

```html
<div class="watermark-overlay" id="watermark"></div>
<script>
function generateWatermarks() {
  const overlay = document.getElementById('watermark');
  const text = '水印文字';
  const itemWidth = 300;
  const itemHeight = 150;
  const cols = Math.ceil(window.innerWidth / itemWidth) + 2;
  const rows = Math.ceil(window.innerHeight / itemHeight) + 2;
  const total = cols * rows;
  let html = '';
  for (let i = 0; i < total; i++) {
    html += `<div class="watermark-item"><span>${text}</span></div>`;
  }
  overlay.innerHTML = html;
}
generateWatermarks();
window.addEventListener('resize', generateWatermarks);
</script>
```

**关键点**：
- `pointer-events: none` - 不阻挡页面交互
- JS动态计算屏幕尺寸，生成足够多的水印元素铺满
- `flex-wrap: wrap` + `align-content: flex-start` 让元素自然排列
- `user-select: none` - 防止选中水印文字
- 监听 `resize` 事件，窗口缩放时重新生成
- 不要用 `::before/::after` 伪元素（只能放1-2个，无法铺满）

### ⚠️ 水印颜色调整
用户反馈水印颜色太浅看不清，已加深：
```css
/* 暗色模式 */
.watermark-item span {
    color: rgba(30, 64, 175, 0.25);  /* 从0.1加深到0.25 */
}
/* 亮色模式 */
body.light .watermark-item span {
    color: rgba(59, 130, 246, 0.15);
}
```

## 亮暗主题切换功能

### 实现方案
右上角固定按钮，点击切换亮暗模式，自动保存到localStorage。

### HTML结构
```html
<button class="theme-toggle" onclick="toggleTheme()">🌙 暗色</button>
```

### CSS实现
```css
/* 切换按钮 */
.theme-toggle {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    color: #fff;
    padding: 8px 16px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 14px;
    backdrop-filter: blur(10px);
    transition: all 0.3s;
}
.theme-toggle:hover { background: rgba(255,255,255,0.25); }
body.light .theme-toggle {
    background: rgba(0,0,0,0.1);
    border-color: rgba(0,0,0,0.15);
    color: #333;
}
```

### 亮色主题完整样式
```css
/* 基础 */
body.light { background: #f0f2f5; color: #1a1a2e; }
body.light .report-container { background: #ffffff; box-shadow: 0 4px 24px rgba(0,0,0,0.1); }
body.light .report-header { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); }

/* 日期/星期 */
body.light .report-header .date { color: #bfdbfe; }
body.light .report-header .brand { color: #93c5fd; }

/* 表格 */
body.light .index-table th { background: #f1f5f9; color: #475569; }
body.light .index-table td { color: #334155; border-color: #e2e8f0; }
body.light .index-table .up { color: #dc2626; }
body.light .index-table .down { color: #16a34a; }

/* 板块卡片 */
body.light .flow-card { background: #f8fafc; border-color: #e2e8f0; }
body.light .flow-card .sector-name { color: #1e293b; }
body.light .flow-card .amount { color: #475569; }

/* 信号表格 */
body.light .signal-table th { background: #f1f5f9; color: #475569; }
body.light .signal-table td { color: #334155; border-color: #e2e8f0; }
body.light .signal-table .name { color: #1e293b; }
body.light .signal-table .code { color: #3b82f6; }
body.light .signal-table .date { color: #94a3b8; }
body.light .signal-table .first-price { color: #d97706; }
body.light .signal-table .data-price { color: #7c3aed; }
body.light .signal-table tr.latest { background: rgba(59, 130, 246, 0.1); }

/* 页脚 */
body.light .report-footer { border-top-color: #e2e8f0; color: #94a3b8; }
body.light .report-footer .watermark { color: #3b82f6; }
```

### JavaScript实现
```javascript
function toggleTheme() {
    const body = document.body;
    const btn = document.querySelector('.theme-toggle');
    body.classList.toggle('light');
    
    if (body.classList.contains('light')) {
        btn.textContent = '☀️ 亮色';
        localStorage.setItem('theme', 'light');
    } else {
        btn.textContent = '🌙 暗色';
        localStorage.setItem('theme', 'dark');
    }
    generateWatermarks(); // 重新生成水印（颜色会随主题变化）
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const btn = document.querySelector('.theme-toggle');
    if (savedTheme === 'light') {
        document.body.classList.add('light');
        btn.textContent = '☀️ 亮色';
    }
}
initTheme();
```

### ⚠️ 亮色主题CSS覆盖陷阱（重要）
**问题**：添加亮色主题时，只改了主容器背景，但子元素（index-card、sector-box、flow-card）的背景色没有覆盖，导致切换后表格仍然是黑色。

**原因**：暗色主题下子元素有独立的 `background: #0f172a`，亮色主题必须显式覆盖这些子元素。

**必须覆盖的元素清单**：
```css
/* 指数卡片 */
body.light .index-card { background: #ffffff; border-color: #e2e8f0; }
body.light .index-card .name { color: #64748b; }
body.light .index-card .price { color: #1e293b; }

/* 板块卡片 */
body.light .sector-box { background: #ffffff; border-color: #e2e8f0; }
body.light .sector-box h3 { color: #475569; }
body.light .sector-item { border-bottom-color: #e2e8f0; }
body.light .sector-item .rank { color: #64748b; }
body.light .sector-item .name { color: #334155; }

/* 资金流向卡片 */
body.light .flow-card { background: #ffffff; border-color: #e2e8f0; }

/* 分隔线 */
body.light .section-title::after { background: linear-gradient(to right, #3b82f6, transparent); }
```

**调试方法**：用浏览器开发者工具检查元素，查看暗色主题下哪些元素有独立的background/border-color，确保亮色主题都覆盖到。

### 用户偏好
- 用户要求report页面有亮暗切换功能
- 水印颜色要加深，太浅看不清
- 切换时所有元素（表格、卡片、水印）都要同步变色
- 保存用户偏好到localStorage

## 截图功能（html2canvas）

/report是独立页面，没有侧边栏，截图按钮需要放在页面右上角（与主题切换按钮并排）。

### 实现要点
1. **CDN引入html2canvas**：`<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>`
2. **按钮定位**：`position: fixed; top: 20px; right: 140px;`（在主题切换按钮左边）
3. **截图时隐藏干扰元素**：全屏水印overlay、主题切换按钮、截图按钮本身
4. **截图后恢复**：无论成功失败都要恢复`display`
5. **文件名**：`JMY_A股日报_YYYY-MM-DD.png`
6. **2倍清晰度**：`scale: 2`参数
7. **背景色跟随主题**：暗色`#0a0e17`，亮色`#f0f2f5`

### 按钮样式
```css
.screenshot-btn {
    position: fixed;
    top: 20px;
    right: 140px;
    z-index: 1000;
    background: linear-gradient(135deg, #059669, #10b981);
    border: none;
    color: #fff;
    padding: 8px 20px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    box-shadow: 0 2px 12px rgba(16,185,129,0.4);
    transition: all 0.3s;
}
.screenshot-btn:hover { transform: scale(1.05); }
.screenshot-btn.loading { opacity: 0.7; pointer-events: none; }
```

### JS实现
```javascript
async function takeScreenshot() {
  const btn = document.getElementById('screenshot-btn');
  btn.textContent = '⏳ 截图中...';
  btn.classList.add('loading');
  try {
    // 只隐藏按钮，保留水印
    const themeBtn = document.querySelector('.theme-toggle');
    const screenshotBtnEl = document.getElementById('screenshot-btn');
    themeBtn.style.display = 'none';
    screenshotBtnEl.style.display = 'none';
    
    const container = document.querySelector('.report-container');
    const canvas = await html2canvas(container, {
      backgroundColor: document.body.classList.contains('light') ? '#f0f2f5' : '#0a0e17',
      scale: 2, useCORS: true, logging: false
    });
    
    // 恢复显示
    themeBtn.style.display = '';
    screenshotBtnEl.style.display = '';
    
    // 下载
    const link = document.createElement('a');
    link.download = `JMY_A股日报_${new Date().toISOString().slice(0,10)}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    btn.textContent = '✅ 已保存';
    setTimeout(() => { btn.textContent = '📸 截图'; btn.classList.remove('loading'); }, 2000);
  } catch(e) {
    // 恢复显示（失败也要恢复）
    document.querySelector('.theme-toggle').style.display = '';
    document.getElementById('screenshot-btn').style.display = '';
    btn.textContent = '❌ 失败';
    setTimeout(() => { btn.textContent = '📸 截图'; btn.classList.remove('loading'); }, 2000);
  }
}
```

### ⚠️ 截图必须保留水印overlay（用户明确要求）
用户截图发社群/论坛，需要水印作为品牌标识。**截图时只隐藏按钮，保留水印**。
- 隐藏：主题切换按钮 `.theme-toggle`、截图按钮 `#screenshot-btn`
- 保留：全屏水印 `#watermark`、页脚 `@一棵小韭菜`
- 用户原话："截图后的图片怎么水印没有了"

```javascript
// 只隐藏按钮，保留水印
const themeBtn = document.querySelector('.theme-toggle');
const screenshotBtnEl = document.getElementById('screenshot-btn');
themeBtn.style.display = 'none';
screenshotBtnEl.style.display = 'none';
// 注意：不要隐藏 watermark！
```

### ⚠️ html2canvas不能渲染`position: fixed`元素（重要）
**问题**：水印用`position: fixed`定位时，html2canvas截图中完全不显示。

**原因**：html2canvas对`position: fixed`的元素支持不好，fixed元素不在容器的渲染范围内。

**解决方案**：水印overlay必须放在`report-container`内部，用`position: absolute`：
```css
/* 容器需要 relative 定位 */
.report-container { position: relative; }

/* 水印用 absolute 不用 fixed */
.watermark-overlay {
    position: absolute;  /* ← 关键：不能用 fixed */
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
    z-index: 99;
    overflow: hidden;
    display: flex;
    flex-wrap: wrap;
    align-content: flex-start;
}
```

**HTML结构**：水印必须在report-container内部
```html
<div class="report-container">
  <div class="watermark-overlay" id="watermark"></div>  <!-- ← 在容器内部 -->
  <div class="report-header">...</div>
  ...
</div>
```

### ⚠️ 水印生成函数必须用容器尺寸+延迟生成
水印移到容器内部后，`generateWatermarks()`不能再用`window.innerWidth/Height`计算水印数量，必须用容器的`scrollWidth/scrollHeight`。

```javascript
function generateWatermarks() {
  const overlay = document.getElementById('watermark');
  const container = document.querySelector('.report-container');  // ← 获取容器
  const text = '枫月的大论坛1022949553';
  const itemWidth = 300;
  const itemHeight = 150;
  
  // ✅ 用容器尺寸，不用 window.innerWidth/Height
  const containerWidth = container.scrollWidth;
  const containerHeight = container.scrollHeight;
  const cols = Math.ceil(containerWidth / itemWidth) + 1;
  const rows = Math.ceil(containerHeight / itemHeight) + 1;
  const total = cols * rows;
  // ...
}
```

另外，页面内容是动态加载的（fetch API），容器高度在JS执行时可能还没确定。必须在`window.load`事件后再次生成水印。

### ⚠️ 脚本执行顺序：DOMContentLoaded 是必须的（血泪教训 2026-06-25）
**问题**：`<script>`标签在`<div id="watermark">`之前，直接调用`generateWatermarks()`时`getElementById`返回null→函数抛错→后面的`addEventListener`也执行不到→水印永远不生成。

**错误写法**（会导致水印永远不出现）：
```javascript
// <script> 在 <div id="watermark"> 之前
generateWatermarks();  // ← 抛错！getElementById返回null
window.addEventListener('load', generateWatermarks);  // ← 永远执行不到
window.addEventListener('resize', generateWatermarks);  // ← 永远执行不到
```

**正确写法**：
```javascript
function generateWatermarks() {
  const overlay = document.getElementById('watermark');
  const container = document.querySelector('.report-container');
  if (!overlay || !container) return;  // ← 防御性检查
  // ...
}
// 用DOMContentLoaded确保DOM元素已创建
document.addEventListener('DOMContentLoaded', function() {
  generateWatermarks();
  window.addEventListener('resize', generateWatermarks);
});
```

**关键点**：
- `DOMContentLoaded`在HTML解析完成后触发，此时所有DOM元素已创建
- 即使`<script>`在页面中间（DOM元素之前），也能正确执行
- 函数内加null检查是防御性编程，防止极端情况

### ⚠️ html2canvas不能渲染渐变文字（background-clip: text）
**问题**：亮色主题下section-title用渐变文字效果，截图中变成实色背景块。

```css
/* ❌ html2canvas不支持 */
body.light .section-title {
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
```

**解决方案**：亮色主题下用纯色
```css
/* ✅ 截图兼容 */
body.light .section-title {
    color: #1e40af;
    background: none;
    -webkit-background-clip: unset;
    -webkit-text-fill-color: unset;
}
```

### ⚠️ 卡片式信号列表每列必须有label
用户说"标题都没了 这样用户不知道具体值是什么意思"。每列必须有小标签说明含义。

**必须有label的列**：
- `sr-price` — "发现价"、"数据价"
- `sr-change` — "距离首期"
- `sr-gain` — "累计涨跌"

```html
<div class="sr-change">
  <div class="label">距离首期</div>
  <div class="value up">↑ +12.53%</div>
</div>
<div class="sr-gain">
  <div class="label">累计涨跌</div>
  <div class="value up">+19.86%</div>
</div>
```

对应CSS：
```css
.signal-row .sr-change .label { font-size: 10px; color: #64748b; }
.signal-row .sr-change .value { font-weight: 600; }
.signal-row .sr-gain .label { font-size: 10px; color: #64748b; }
.signal-row .sr-gain .value { font-size: 15px; font-weight: 700; }
```
