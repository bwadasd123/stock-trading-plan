# 双重价格对比实现

## 功能说明
推送消息同时显示两个价格维度：
1. 扫描发现价 → 看系统选出后的整体涨幅
2. 买入价 → 看实际持仓盈亏
3. 溢价 → 评估买入时机好坏

## 实现逻辑

### 1. 从数据库获取扫描发现价

```python
import pymysql
from config import MYSQL_CONFIG

def load_scan_info(ts_code):
    """从数据库加载首次扫描发现信息"""
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # 获取首次扫描
    cursor.execute('''
        SELECT latest_price, rsi14, scan_time
        FROM stock_scan_results 
        WHERE ts_code = %s 
        ORDER BY scan_time ASC 
        LIMIT 1
    ''', (ts_code,))
    first_scan = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if first_scan:
        return {
            "first_price": float(first_scan["latest_price"]),
            "first_time": str(first_scan["scan_time"])[:10],
            "first_rsi": float(first_scan["rsi14"]),
        }
    return None
```

### 2. 计算双重对比

```python
scan_price = scan_info["first_price"]  # 扫描发现价
avg_cost = 16.443                       # 实际买入价
price = current_price                   # 当前价格

# 基于扫描发现价的涨幅
profit_from_scan = (price - scan_price) / scan_price * 100

# 基于买入价的盈亏
profit_from_cost = (price - avg_cost) / avg_cost * 100

# 买入价相对于发现价的溢价
cost_premium = (avg_cost - scan_price) / scan_price * 100
```

### 3. 推送消息格式

```
🔍 双重对比
   扫描发现价 15.80（2026-06-16）
   └ 现价涨幅 +9.8%
   实际买入价 16.443
   └ 买入溢价 +4.1%
```

## 两套止盈止损

基于两个价格分别计算止盈止损：

```python
# 基于买入价
COST_TP = avg_cost * 1.15   # +15%
COST_SL = avg_cost * 0.92   # -8%

# 基于扫描发现价
SCAN_TP = scan_price * 1.15  # +15%
SCAN_SL = scan_price * 0.92  # -8%
```

推送消息中同时显示两套止盈止损参考：

```
🎯 止盈参考
   买入价 16.443  →  18.91（+15%）
   发现价 15.80  →  18.17（+15%）

🚨 止损参考
   买入价 16.443  →  15.13（-8%）
   发现价 15.80  →  14.54（-8%）
```

## 用途说明

- **扫描发现价涨幅**：评估选股系统的准确性
- **买入价盈亏**：评估实际持仓收益
- **买入溢价**：评估买入时机（溢价高=追高，溢价低=抄底）
- **两套止盈止损**：双重参考，更全面

## 注意事项

1. 扫描发现价是首次扫描时的价格，不是当前扫描价格
2. 溢价 = (买入价 - 发现价) / 发现价 × 100%
3. 如果溢价过高（如>10%），说明买入时机不好，追高了
4. 如果溢价为负，说明买入价低于发现价，抄底成功
