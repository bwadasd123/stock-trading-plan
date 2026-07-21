# 扫描结果分析流程

## 分析步骤
1. 从DB获取扫描结果: `SELECT * FROM stock_scan_results WHERE id=X`
2. 获取近期K线: `get_kline_data(code, '101', 30)` → 近10日走势
3. 分析指标: RSI/CCI/MACD/量比/MA20
4. 结合用户策略给出操作建议

## 关键判断逻辑

### 追高风险判断
- 连续2天暴涨(>15%) → 不建议追
- 换手率突然放大5倍+ → 主力可能出货
- RSI>70 + CCI>200 → 超买区，追高风险大
- 股价偏离MA20>20% → 回调概率高

### 入场时机
- 等回调到MA20附近再入
- 高开>3%不追
- 集合竞价观察

### 计算示例（3万本金）
```
本金: 30,000元
仓位: 20% = 6,000元
股价: 15.80元
可买: 6000 / 15.80 = 379股 → 取整300股
实际: 300 × 15.80 = 4,740元
止损: 15.80 × 0.92 = 14.54元 → 亏损378元
止盈: 15.80 × 1.15 = 18.17元 → 盈利711元
```

## 数据库表结构
stock_scan_results表字段: id, scan_id, ts_code, stock_name, latest_price, change_pct, turnover, volume_ratio, rsi14, cci20, macd_dif, macd_dea, macd_bar, macd_gold, ma5, ma10, ma20, circ_market_cap, data_date, scan_time

注意: 字段名是ts_code不是code，stock_name不是name。查询用字典访问。
