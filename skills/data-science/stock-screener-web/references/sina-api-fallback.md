# Sina API Fallback for Market Indices

## Problem

East Money push2 API (`push2.eastmoney.com/api/qt/stock/get`) sometimes returns 502 errors or empty responses when accessed directly (without proxy). This causes the daily digest page to show all zeros for index data.

## Solution: Use Sina Finance API

Sina's API is more reliable for basic index quotes. Use it as the primary source for market indices.

### API Endpoint

```
https://hq.sinajs.cn/list={codes}
```

### Index Codes (Sina format)

| Index | Code |
|-------|------|
| 上证指数 | `s_sh000001` |
| 深证成指 | `s_sz399001` |
| 创业板指 | `s_sz399006` |
| 上证50 | `s_sh000016` |
| 沪深300 | `s_sh000300` |

### Request Pattern

```python
import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 ...",
    "Referer": "https://finance.sina.com.cn",
})

codes = "s_sh000001,s_sz399001,s_sz399006"
resp = session.get(f"https://hq.sinajs.cn/list={codes}", timeout=10)
resp.encoding = "gbk"  # CRITICAL: Sina uses GBK encoding
```

### Response Format

```
var hq_str_s_sh000001="上证指数,4063.7219,-4.8472,-0.12,4536030,89602210";
var hq_str_s_sz399001="深证成指,15481.10,-94.029,-0.60,523212555,105939958";
```

### Field Mapping

Fields are comma-separated inside the quoted string:

| Position | Field | Example |
|----------|-------|---------|
| 0 | Name (名称) | 上证指数 |
| 1 | Current Price (当前价) | 4063.7219 |
| 2 | Change Amount (涨跌额) | -4.8472 |
| 3 | Change % (涨跌幅) | -0.12 |
| 4 | Volume (成交量, 手) | 4536030 |
| 5 | Amount (成交额, 万元) | 89602210 |

### Parsing Code

```python
def get_market_indices():
    indices = [
        {"code": "s_sh000001", "name": "上证指数"},
        {"code": "s_sz399001", "name": "深证成指"},
        {"code": "s_sz399006", "name": "创业板指"},
        {"code": "s_sh000016", "name": "上证50"},
        {"code": "s_sh000300", "name": "沪深300"},
    ]
    
    codes = ",".join([idx["code"] for idx in indices])
    resp = session.get(f"https://hq.sinajs.cn/list={codes}", timeout=10)
    resp.encoding = "gbk"
    
    results = []
    lines = resp.text.strip().split("\n")
    
    for i, line in enumerate(lines):
        if i >= len(indices):
            break
        idx = indices[i]
        try:
            data_str = line.split('"')[1] if '"' in line else ""
            if data_str:
                parts = data_str.split(",")
                if len(parts) >= 4:
                    results.append({
                        "name": idx["name"],
                        "price": float(parts[1]),
                        "change_pct": float(parts[3]),
                        "volume": float(parts[4]) if len(parts) > 4 else 0,
                        "amount": float(parts[5]) if len(parts) > 5 else 0,
                    })
        except Exception as e:
            logger.error(f"解析{idx['name']}数据失败: {e}")
    
    return results
```

## Northbound Capital Flow API

### Endpoint

```
https://push2.eastmoney.com/api/qt/kamt.rtmin/get
```

### Parameters

```python
params = {
    "fields1": "f1,f2,f3,f4",
    "fields2": "f51,f52,f53,f54,f55,f56",
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
}
```

### Response Structure

```json
{
  "data": {
    "s2n": ["10:00,12345678,-5000000,...", "10:05,12345678,-4000000,..."],
    "s2s": ["10:00,87654321,3000000,...", "10:05,87654321,2000000,..."]
  }
}
```

- `s2n` = 沪股通 (Shanghai Connect)
- `s2s` = 深股通 (Shenzhen Connect)
- Each entry is comma-separated: `time,net_inflow,net_buy,...`
- Values are in **元 (yuan)**, divide by 10000 for 万

### Parsing Code

```python
def get_northbound_flow():
    resp = session.get(url, params=params, timeout=10, verify=False)
    data = resp.json().get("data", {})
    
    # 沪股通 - latest entry
    s2n = data.get("s2n", [])
    if s2n:
        latest = s2n[-1].split(",")
        sh_net = float(latest[1]) if len(latest) > 1 and latest[1] != '-' else 0
    else:
        sh_net = 0
    
    # 深股通 - latest entry
    s2s = data.get("s2s", [])
    if s2s:
        latest = s2s[-1].split(",")
        sz_net = float(latest[1]) if len(latest) > 1 and latest[1] != '-' else 0
    else:
        sz_net = 0
    
    return {
        "sh_net": sh_net / 10000,  # 转为万
        "sz_net": sz_net / 10000,
        "total_net": (sh_net + sz_net) / 10000,
    }
```

### Pitfall: `-` Values

During non-trading hours or when data is unavailable, the API returns `'-'` for net inflow values. Always check `latest[1] != '-'` before converting to float.

## When to Use Each API

| Use Case | API | Reason |
|----------|-----|--------|
| Market indices (daily digest) | Sina | More reliable, no 502 errors |
| Stock quotes (real-time) | Sina (`hq.sinajs.cn`) | Fast, simple format |
| Sector flow | East Money push2 | Only source for sector data |
| Northbound flow | East Money kamt | Only source for Connect data |
| K-line data | East Money push2his | Historical data |
| Dragon Tiger | East Money datacenter | Only source for 龙虎榜 |
