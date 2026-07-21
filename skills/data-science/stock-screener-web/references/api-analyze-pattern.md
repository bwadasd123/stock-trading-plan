# /api/analyze 端点模式

## 概述
个股详情分析接口，返回K线数据、技术指标、实时行情、流通市值。

## 关键实现

### circ_cap 获取（流通市值）
```python
# api/scan.py 中的实现
from anti_crawl import safe_get as _safe_get, get_kline_headers

secid = f"1.{code}" if code.startswith(("600","601","603","605","688","689")) else f"0.{code}"
url = "http://push2.eastmoney.com/api/qt/stock/get"
params = {"secid": secid, "fields": "f84,f116,f117", "ut": "fa5fd1943c7b386f172d6893dbfba10b", "fltt": 1}
headers = get_kline_headers(code)
resp = _safe_get(url, headers=headers, params=params, timeout=10)

if resp and resp.status_code == 200:
    text = resp.text
    # 兼容JSONP和纯JSON
    m = re.search(r'\((\{.*\})\)', text)
    if m:
        text = m.group(1)
    d = json.loads(text).get("data", {})
    circ_share = d.get("f84", 0)  # 流通股本
    price = data["klines"][-1]["close"]
    circ_cap = round((circ_share * price) / 1e8, 2)
```

### 已知陷阱
1. **必须用 `safe_get`** - 直连东财会被拒绝（WSL环境）
2. **纯JSON响应** - `push2.eastmoney.com/api/qt/stock/get` 返回纯JSON，不是JSONP
3. **需要的imports** - `api/scan.py` 顶部必须有 `import re`, `import logging`, `logger = logging.getLogger(__name__)`
4. **circ_cap=0 会导致前端7指标检查失败** - JavaScript中 `if (circCap && ...)` 当 circCap=0 时为 false

## 前端 calculateScore 逻辑
```javascript
// scanner.js 中的7指标检查
function calculateScore(ind, price, circCap, turnover) {
    // 1. 流通市值≤200亿
    if (circCap && circCap <= 200) {  // ⚠️ circCap=0时为false
        items.push({name: '流通市值≤200亿', pass: true, ...});
    }
    // ... 其他6个指标
}
```
