# 报告页信号去重与日期显示修复（2026-06-26）

## 问题描述

用户反馈两个问题：
1. 同一股票多天扫描显示多条记录（如002167在6/24、6/25、6/26各一条）
2. 日期显示用`first_discovery_date`，用户期望显示`data_date`

## 修复内容

### api/report.py - _load_signals()函数

**修改前**：遍历每只股票的所有记录，每条都加入signals列表
```python
for i, row in enumerate(rows):
    signals.append(signal)
signals = signals[:10]
```

**修改后**：只取每只股票的最新记录
```python
latest_row = rows[-1]  # rows已按data_date ASC排序，最后一条是最新的
signals.append(signal)
# 最终限制为10条（与git历史版本一致，用户说"页面太长了"）
signals = signals[:10]
```

### templates/report.html - renderSignals()函数

**修改1**：日期显示
```javascript
// 修改前
<span class="dates">${s.first_discovery_date || ''}</span>
// 修改后
<span class="dates">${s.data_date || ''}</span>
```

**修改2**：NEW标签判断
```javascript
// 修改前：只有第一条显示NEW
const isLatest = idx === 0;
// 修改后：今天的数据都显示NEW
const isLatest = s.data_date === new Date().toISOString().slice(0,10);
```

## 用户期望

- 每只股票在报告页只显示一条（最新的扫描数据）
- 日期显示最新扫描日期（data_date），不是首次发现日期
- 今天扫描到的所有股票都标NEW，不只是第一个
- 用户认为"每天扫描都算入选"，所以每天的日期都应该显示

## 日期列UI优化（2026-06-26）

用户反馈日期列看不清，优化样式：

```css
/* 暗色主题 */
.signal-row .sr-info .dates {
    font-size: 13px;      /* 原11px */
    color: #94a3b8;       /* 原#64748b */
    font-weight: 500;     /* 新增 */
    letter-spacing: 0.3px; /* 新增 */
}

/* 亮色主题 */
body.light .signal-row .sr-info .dates {
    color: #64748b;       /* 原#94a3b8 */
    font-weight: 500;
}
```

## 关键教训

1. **改代码前先理解用户期望**：用户说"今天有两个"是指今天扫描到了两只股票，不是指有两个新的首次发现
2. **Flask模板修改后必须重启**：`templates/report.html`在启动时加载，修改后必须kill进程重新启动
3. **NEW标签逻辑要按业务需求来**：不是"列表第一个"而是"今天的数据"
4. **日期列要醒目**：用户看不清小字灰色日期，用13px+亮色+加粗
5. **用户说"看git"**：当用户质疑数量/行为变化时，用`git show <commit>:<file> | grep`查原始版本对比，不要猜
6. **页面不要太长**：报告页信号限制10条（git历史默认值），用户明确说"页面太长了"
7. **用户说"去掉的那俩还是要的"**：去掉列/功能前必须确认。这次自作主张去掉了"数据价"和"累计涨跌"两列，用户立刻要求加回来。**教训：减法要问用户，加法可以自己做。**

## 列表行高优化（2026-06-26）

用户反馈"列表行太高了"，需要紧凑布局。同时"右边还空了一块"需要填充。

### 最终grid配置（8列，fr单位填充宽度）
```css
.signal-row {
    display: grid;
    grid-template-columns: 100px 80px 70px 70px 1fr 1fr 80px 1fr;
    padding: 6px 12px;
    gap: 6px;
    border-radius: 6px;
}
.signal-list { gap: 4px; }
```

### 列结构
| 列 | 宽度 | 内容 |
|----|------|------|
| sr-code | 100px | 代码+名称+NEW标签 |
| sr-info | 80px | 版本+日期 |
| sr-price(fp) | 70px | 发现价 |
| sr-price(dp) | 70px | 数据价 |
| sr-change | 1fr | 涨幅（保留1位小数） |
| sr-gain | 1fr | 累计涨跌（保留1位小数） |
| sr-max | 80px | 最高价+日期（合并显示） |
| sr-max-gain | 1fr | 最高涨幅（保留1位小数） |

### 页面宽度
```css
.report-container {
    width: 720px;  /* 保持原宽度，用户说"太宽了"后要求改回原来的 */
}
```
**⚠️ 不要改页面宽度**：用户说"原来是多少调一下"就是要回到git原始值720px。用fr单位填充列宽即可消除右边空白，不需要改容器宽度。

### 优化要点
- **用fr单位填充宽度**：涨幅、累计、最高涨幅用1fr自动填充，消除右边空白
- 原padding 10px 14px → 6px 12px
- 原gap 8px → 4px/6px
- 原border-radius 8px → 6px
- 涨幅精度从2位→1位小数，节省空间
- 最高价和日期合并：label显示"最高价(06-25)"，value显示价格
- **不要自作主张去掉列**：用户要保留所有8列，只是让它更紧凑
- **页面宽度保持720px**：改了用户会说"太宽了"

## 指标标题命名规范（2026-06-26）

用户要求"写的清晰点每一个指标标题"。最终命名：

| 列 | label | 说明 |
|----|-------|------|
| 入选价 | 入选价 | 原"发现价"，用户习惯叫"入选" |
| 现价 | 现价 | 原"数据价"，更直观 |
| 距入选 | 距入选 | 原"涨幅"/"距离首期"，明确是相对入选价的涨幅 |
| 累计涨跌 | 累计涨跌 | 原"累计"，补全含义 |
| 最高价 | 最高价(日期) | 原"最高"，括号内显示日期如"(06-25)" |
| 最高涨幅 | 最高涨幅 | 保持不变 |

**⚠️ 金融数据UI的label必须清晰**：用户不熟悉的术语要用更直观的表达。"数据价"→"现价"、"发现价"→"入选价"。

## 胜率计算修复（2026-06-26）

用户反馈"涨幅0的不应该算负"。

### 问题
`api/scan_profit.py`中：
```python
if profit_pct > 0:
    winning_count += 1
else:  # ← profit_pct == 0 也被算作亏损
    losing_count += 1
```

### 修复
```python
if profit_pct > 0:
    winning_count += 1
elif profit_pct < 0:  # ← 0%不计入胜负
    losing_count += 1
```

### 效果
修复前：4胜1亏（002141涨幅0%算亏）
修复后：4胜0亏（002141不计入胜负）
