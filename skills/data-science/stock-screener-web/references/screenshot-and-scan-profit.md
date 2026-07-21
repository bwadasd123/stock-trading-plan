# 截图功能 + 扫描盈利统计

## 截图功能

### 实现方式
- 使用 `html2canvas@1.4.1` 库
- 侧边栏顶部绿色"📸 截图"按钮
- 点击后自动保存当前活动页面为PNG

### 文件位置
- JS: `static/js/screenshot.js`
- 库引入: `templates/index.html` 的 `<head>` 中添加 CDN

### 功能特点
- 自动添加水印（JMY科技 + 日期时间）
- 文件名格式: `JMY_看板_2026-06-25.png`
- 支持所有页面截图（今日看点、板块资金等）

### 代码结构
```javascript
// 主要函数
captureScreenshot()      // 截图当前活动页面
captureElement(elementId) // 截图指定元素
showToast(message)       // 显示成功提示
```

### 注意事项
- 截图容器宽度固定1200px
- 使用scale: 2保证清晰度
- 背景色使用 `#1a1a2e`（深色主题）

---

## 扫描盈利统计 API

### API端点
`GET /api/scan/monthly-profit`

### 功能
统计本月扫描系统推荐的股票表现

### 返回数据
```json
{
  "success": true,
  "date": "2026-06-25",
  "time": "15:33:22",
  "summary": {
    "total_signals": 4,
    "winning_count": 4,
    "losing_count": 0,
    "win_rate": 100.0,
    "avg_profit": 12.03,
    "total_profit": 48.11
  },
  "signals": [
    {
      "ts_code": "600162",
      "stock_name": "香江控股",
      "first_price": 2.92,
      "current_price": 3.50,
      "profit_pct": 19.86,
      "first_time": "06-03 23:57",
      "signal_count": 6,
      "avg_rsi": 78.6,
      "status": "win"
    }
  ],
  "calc_logic": "计算逻辑:\n1. 查询本月所有扫描信号（去重，取每只股票首次出现价）\n2. 获取每只股票的当前实时价格\n3. 计算涨幅 = (当前价 - 发现价) / 发现价 × 100%\n4. 胜率 = 盈利信号数 / 总信号数 × 100%\n5. 平均涨幅 = 所有信号涨幅之和 / 信号数量"
}
```

### 前端展示
- 在今日看点页面顶部显示统计卡片
- 包含：平均涨幅、信号数量、胜率、盈亏比
- 信号明细表格（股票、发现价、当前价、涨幅、发现时间）
- 计算逻辑说明

### 文件位置
- 后端: `api/scan_profit.py`
- 前端: `static/js/scan_profit.js`
- 蓝图注册: `app.py` 中 `scan_profit_bp`

### 关键实现细节
1. **SQL查询必须用单%** — `DATE_FORMAT(NOW(), '%Y-%m-01')` 不是 `%%Y-%%m-01`
2. **NO_PROXY设置** — 获取东财价格前设置 `os.environ['NO_PROXY'] = '*'`
3. **批量获取价格** — `get_batch_prices(ts_codes)` 减少HTTP请求
4. **超时控制** — 每个请求timeout=5秒

### 前端容器
```html
<div id="scan-profit-section"></div>
```
放在今日看点页面 `<div id="page-daily">` 内部最前面。
