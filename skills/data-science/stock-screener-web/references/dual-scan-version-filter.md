# 双版本对比扫描 - 版本筛选功能

## 概述

双版本对比扫描的结果存储在同一张表 `stock_scan_results` 中，通过 `scan_id` 后缀区分版本：
- `_old` → 老版本 (smplmt=460 采样)
- `_new` → 新版本 (日线)
- 无后缀 → 普通扫描

## 修改记录 (2026-06-10)

### 1. HTML (templates/index.html)

在历史信号页面的 `page-controls` 中添加版本筛选下拉框：

```html
<select id="hist_version" class="select">
  <option value="">全部版本</option>
  <option value="normal">普通扫描</option>
  <option value="old">老版本 (smplmt=460)</option>
  <option value="new">新版本 (日线)</option>
</select>
```

### 2. JS (static/js/app.js)

`loadHistory()` 函数添加版本参数：

```js
const version = document.getElementById('hist_version')?.value || '';
if (version) url += '&version=' + version;
```

表格显示版本标签（使用已有 CSS class）：

```js
let versionTag = '—';
if (s.scan_id) {
  if (s.scan_id.endsWith('_old')) {
    versionTag = '<span class="badge badge-orange">老版本</span>';
  } else if (s.scan_id.endsWith('_new')) {
    versionTag = '<span class="badge badge-blue">新版本</span>';
  }
}
```

表格 header 需要加 `<th>版本</th>`。

### 3. API (api/history.py)

添加 version 参数解析和 SQL 条件：

```python
version = request.args.get("version", "")

version_condition = ""
if version == "old":
    version_condition = "AND scan_id LIKE '%_old'"
elif version == "new":
    version_condition = "AND scan_id LIKE '%_new'"
elif version == "normal":
    version_condition = "AND scan_id NOT LIKE '%_old' AND scan_id NOT LIKE '%_new'"
```

所有 count_sql 和 data SQL 都需要追加 `{version_condition}`。

### 4. README.md

功能概览表格、项目结构、使用文档都需要同步更新。

## 注意事项

- CSS 已有 `badge-orange` 和 `badge-blue` 样式，无需额外添加
- 浏览器可能缓存 JS/CSS，需要用户 Ctrl+F5 强制刷新
- 代理池为空时，东财 push2 API 可能返回 502，导致扫描 0 只股票

## ⚠️ filter参数陷阱（2026-06-10发现）

手动触发双版本扫描时，必须传完整的filter参数：

```python
# ❌ 错误：只传第一轮条件，第二轮不过滤
requests.post("/api/dual_scan_all", json={"r1_turnover": 10, "r1_cap_max": 200})

# ✅ 正确：传完整的7个条件
requests.post("/api/dual_scan_all", json={
    "r1_turnover": 10,
    "r1_cap_max": 200,
    "r2_rsi": 70,        # RSI > 70
    "r2_macd": True,      # MACD金叉
    "r2_cci": True,       # CCI > 0
    "r2_ma20": True,      # 价格 > MA20
    "r2_vol_ratio": 1.5,  # 量比 ≥ 1.5
    "r2_turnover": 10     # 换手率 > 10%
})
```

`check_filters()` 函数中，`filters.get("r2_rsi", 0)` 默认值为0表示不检查该条件。如果所有r2_参数都是0/False，第二轮筛选等于没过滤，所有通过第一轮的股票都会被标记为pass=True。

前端会自动传所有条件，但代码测试/API调用时容易遗漏。

## ⚠️ 前端/后端key映射不一致 (2026-06-17)

前端发送的key与扫描器期望的key不同，API层必须做转换：

| 前端key | 扫描器key | 含义 |
|---------|-----------|------|
| `turn1` | `r1_turnover` | 第一轮换手率 |
| `cap` | `r1_cap_max` | 第一轮流通市值上限 |
| `rsi` | `r2_rsi` | 第二轮RSI阈值 |
| `volr` | `r2_vol_ratio` | 第二轮量比 |

**症状：** 日志显示使用默认条件（`换手率>0%, 流通市值≤9999亿`），而非用户设定的条件。

**修复位置：** `app.py` 的 `/api/dual_scan_all` 路由，添加映射转换：
```python
filters = {
    "r1_turnover": data.get("turn1", 10),
    "r1_cap_max": data.get("cap", 200),
    "r2_rsi": data.get("rsi", 70),
    "r2_vol_ratio": data.get("volr", 1.5),
    # ... 其他条件
}
```
