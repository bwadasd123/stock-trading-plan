# 回测系统

## 架构
- `services/backtest.py` — 回测引擎
- `api/backtest.py` — Flask蓝图，两个端点
- `templates/index.html` — 前端页面（侧边栏📊回测系统）

## API端点
### POST /api/backtest/run
请求体:
```json
{
  "capital": 30000,
  "position_pct": 0.20,
  "stop_loss": -0.08,
  "take_profit": 0.15,
  "max_hold_days": 5,
  "days": 30,
  "scan_date": "可选，YYYY-MM-DD格式，指定某天扫描结果",
  "scan_id": "可选，指定扫描ID",
  "code": "可选，单股代码如002972，回测该股所有扫描记录"
}
```

四种回测模式:
- **全量回测**: 只传`days`，回测最近N天所有扫描信号
- **指定日期**: 传`scan_date`（YYYY-MM-DD），回测该天扫描的所有股票（已去重）
- **指定扫描**: 传`scan_id`，回测某次扫描的所有股票
- **单股回测**: 传`code`，回测该股票的所有历史扫描记录

### GET /api/backtest/signals
返回可回测的扫描信号列表（最近90天）。

## 回测逻辑
1. 从`stock_scan_results`表读取扫描信号（**按股票代码去重，取最早扫描日期**）
   - 同一只股票连续多天被扫描到 → 只取最早那次
   - SQL: `GROUP BY ts_code, stock_name, latest_price` + `MIN(scan_time)`, `MIN(data_date)`
2. **关联版本信息** — `LEFT JOIN scan_task_history` 获取 task_name（老版本/新版本）
3. 获取每只股票的K线数据（通过代理，较慢）
4. 找到扫描日期在K线中的位置
5. 次日开盘价模拟买入（整百股，最少100股）
6. 逐日检查:
   - 当日最低价 ≤ 买入价×0.92 → 止损卖出
   - 当日最高价 ≥ 买入价×1.15 → 止盈卖出
   - 持仓第5天 → 收盘价卖出
7. 计算盈亏和统计指标

### 去重SQL模板（与历史信号一致，使用first_discovery_date）

**⚠️ 必须与历史信号页面去重逻辑一致！** 历史信号使用`v_scan_results_with_change`视图的`first_discovery_date = data_date`条件。回测也必须用相同逻辑，否则结果不一致。

**正确去重方法**（INNER JOIN first_discovery子查询）:
```sql
SELECT r.ts_code, r.stock_name, r.latest_price, 
       MIN(r.scan_time) as scan_time, MIN(r.data_date) as data_date, 
       MIN(r.scan_id) as scan_id,
       (SELECT COALESCE(t2.task_name, '') FROM scan_task_history t2 
        WHERE t2.scan_id = MIN(r.scan_id) LIMIT 1) as version
FROM stock_scan_results r
INNER JOIN (
    SELECT ts_code, MIN(data_date) as first_date
    FROM stock_scan_results
    GROUP BY ts_code
) first_discovery ON r.ts_code = first_discovery.ts_code AND r.data_date = first_discovery.first_date
WHERE r.scan_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
GROUP BY r.ts_code, r.stock_name, r.latest_price
ORDER BY scan_time
```

**验证方法**:
```sql
-- 去重后最近30天应与历史信号页面一致
SELECT COUNT(*) FROM v_scan_results_with_change 
WHERE scan_time >= DATE_SUB(NOW(), INTERVAL 30 DAY) AND first_discovery_date = data_date;
```

**❌ 错误方法**（简单GROUP BY，不去重）:
```sql
-- 这样同一只股票多天扫描会出现多条记录！
GROUP BY ts_code, stock_name, latest_price
```

### 指定日期SQL模板
```sql
WHERE DATE(r.scan_time) = %s
GROUP BY r.ts_code, r.stock_name, r.latest_price
```

### signals API（下拉框）按日期分组
```sql
SELECT DATE(scan_time) as scan_date, COUNT(*) as stock_count, MIN(scan_time) as scan_time
FROM stock_scan_results
WHERE scan_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY DATE(scan_time)
ORDER BY scan_date DESC
```
前端用`scan_date`作为value（格式YYYY-MM-DD），不用scan_id。

### 交易明细字段
每笔交易包含: code, name, scan_date, buy_date, buy_price, sell_date, sell_price, shares, cost, pnl, pnl_pct, hold_days, sell_reason, scan_id, **version**（老版本/新版本）

## 输出统计
- 总交易数、胜率、总盈亏、收益率
- 平均盈利、平均亏损、盈亏比
- 最大单笔盈亏、最大连续亏损、最大回撤
- 按卖出原因分类统计
- 累计收益曲线数据（ECharts渲染）
- 每笔交易明细表

## 前端特性
- 参数可调（资金、仓位、止损、止盈、持仓天数）
- ECharts累计收益曲线图
- 盈亏颜色编码（绿盈红亏）
- 响应式布局
- **交易明细表列**: 股票、版本(新/老)、买入(日期+价格)、卖出(日期+价格)、盈亏、收益率、持仓天数、卖出原因

### UI布局（2026-06-17修正）
**标题行 + 按钮同行**：标题和"开始回测"按钮在同一行（flex两端对齐），参数面板在下方。按钮必须在首屏可见，不能被参数面板挤到屏幕外。
```html
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
  <div><h3>📊 策略回测</h3><p>描述...</p></div>
  <button>▶ 开始回测</button>
  <button id="btn-stop-backtest" style="display:none;">⏹ 停止回测</button>
</div>
<!-- 参数面板在下面 -->
```
**停止按钮**: 回测开始后显示红色停止按钮，点击重置按钮状态。停止按钮用`#ef4444`红色背景。

### 下拉框（指定扫描）
按日期分组，不用scan_id。前端传`scan_date`参数（YYYY-MM-DD格式匹配正则）。

## 性能注意
- 每只股票需1次代理请求获取K线数据
- **⚠️ 必须添加请求延时** — 每次K线请求后等待2秒（`time.sleep(2)`），否则频繁请求会导致代理池耗尽、重试5次仍失败
- 代理慢时回测可能需要数分钟
- 建议先用`scan_id`单个测试，确认正常后再批量

## 数据来源
- 扫描信号: `stock_scan_results`表
- K线数据: 东方财富`push2his`API（通过代理池）

## 代理获取方式（与双版本扫描完全一致）
回测的K线获取调用链路和双版本扫描一模一样：
```
backtest.py → get_kline_data() → safe_get() → PROXY_POOL.get()
scanner_dual.py → get_kline_data() / get_kline_data_old() → safe_get() → PROXY_POOL.get()
```
两者使用同一个`safe_get`、同一个代理池、同一个重试逻辑（最多10次换代理）。不需要额外的代理处理逻辑。
