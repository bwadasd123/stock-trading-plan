# 备份文件结构

## 路径
`/home/jmy/stock-screener/backup_YYYY-MM-DD_N.json`

## 顶层键
```json
{
  "date": "2026-06-16",
  "stock_snapshot": [],        // 全量扫描结果（几百只，未筛选）
  "stock_scan_results": [],    // 筛选后推荐股票（通常1只）★
  "scan_task_history": []      // 扫描任务记录
}
```

## 关键区别
| 字段 | 数量 | 用途 |
|------|------|------|
| `stock_snapshot` | 300+ | 原始扫描数据，包含所有涨幅较大的股票 |
| `stock_scan_results` | 1-2 | **最终推荐**，经过RSI/MACD/量比等条件筛选 |

## stock_scan_results 字段
```json
{
  "ts_code": "002972",
  "stock_name": "科安达",
  "latest_price": "15.80",
  "change_pct": "8.67",
  "volume_ratio": "2.66",    // 量比 > 1.5 ✓
  "rsi14": "70.10",          // RSI 70-80 ✓
  "cci20": "293.80",
  "macd_gold": 1,            // MACD金叉 ✓
  "ma5": "13.09",
  "ma10": "13.06",
  "ma20": "12.79",           // 价格需站上MA20
  "circ_market_cap": "38.87",
  "data_date": "2026-06-16",
  "scan_time": "2026-06-16 18:10:11"
}
```

## 读取代码
```python
import json
data = json.load(open('backup_2026-06-16_2.json'))
results = data.get('stock_scan_results', [])
for r in results:
    print(f"{r['ts_code']} {r['stock_name']} RSI:{r['rsi14']}")
```
