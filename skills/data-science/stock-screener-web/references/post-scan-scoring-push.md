# 盘后扫描评分+企微推送

## 触发时机
`run_full_scan()` 在 `scanner_dual.py` 中结束时自动调用 `_push_scan_recommendation()`

## 评分规则（_score_stock）
| 条件 | 分值 | 说明 |
|------|------|------|
| RSI 60-75 | 1分 | 趋势强但不超买 |
| 量比 ≥ 2 | 1分 | 有资金关注 |
| MACD金叉 | 1分 | 趋势确认 |
| 非涨停（涨跌<9.5%） | 1分 | 不追高 |

## 操作建议
| 得分 | 操作 | 仓位 |
|------|------|------|
| 4分 | ✅ 可进 | 满仓20% |
| 3分 | ⚠️ 谨慎 | 半仓10% |
| ≤2分 | ❌ 不进 | — |

## 入场价
建议挂单 `现价 × 0.98`（回调2%入场）

## 推送渠道
- 从 `/home/jmy/.hermes/profiles/eastmoney-bot/.env` 读取 WX_WEBHOOK
- 无股票也推送 "今日无通过"
- 最多推送5只

## Report页面价格数据源
历史信号"现价"从 `stock_snapshot` 取今天最新价格，不再用扫描时的旧价：
```python
cur2.execute("""
    SELECT ts_code, latest_price, change_pct
    FROM stock_snapshot
    WHERE ts_code IN (%s) AND DATE(scan_time) = CURDATE()
""", codes)
```
`stock_snapshot` 在扫描时已存所有股票价格（3198条/天），不需要额外同步。
