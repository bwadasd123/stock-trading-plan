# Dragon Tiger (龙虎榜) & Watchlist (自选股监控) Patterns

## Dragon Tiger (龙虎榜) Implementation

### API Endpoint
```
https://datacenter-web.eastmoney.com/api/data/v1/get
```

### Key Parameters
```python
params = {
    "sortColumns": "SECURITY_CODE",
    "sortTypes": 1,
    "pageSize": 50,
    "pageNumber": 1,
    "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",  # 上榜个股
    "columns": "ALL",
    "source": "WEB",
    "client": "WEB",
    "filter": f'(TRADE_DATE>=\'{date}\')(TRADE_DATE<=\'{date}\')',
}
```

### Field Mapping
| API Field | Description | Unit |
|-----------|-------------|------|
| SECURITY_CODE | 股票代码 | - |
| SECURITY_NAME_ABBR | 股票名称 | - |
| CLOSE_PRICE | 收盘价 | 元 |
| CHANGE_RATE | 涨跌幅 | % |
| TURNOVERRATE | 换手率 | % |
| ACCUM_AMOUNT | 成交额 | **元** (not 万) |
| BILLBOARD_NET_AMT | 龙虎榜净买入 | **元** |
| BILLBOARD_BUY_AMT | 买入额 | **元** |
| BILLBOARD_SELL_AMT | 卖出额 | **元** |
| EXPLAIN | 上榜原因 | - |

### ⚠️ CRITICAL: Amount Units
**All amount fields from this API are in YUAN (元), not wan (万)!**

Frontend display must convert to 亿:
```javascript
const amountYi = (s.amount / 1e8).toFixed(2);  // Convert yuan to 亿
const netBuyYi = (s.net_buy / 1e8).toFixed(2);
```

### Buy/Sell Seat Details
For individual stock detail:
- Buy seats: `reportName: "RPT_BILLBOARD_DAILYDETAILSBUY"`
- Sell seats: `reportName: "RPT_BILLBOARD_DAILYDETAILSSELL"`
- Key fields: `OPERATEDEPT_NAME`, `BUY_AMT`, `SELL_AMT`, `NET_AMT`

---

## Watchlist (自选股监控) Implementation

### Storage
- File: `~/.hermes/stock_watchlist.json`
- Format: JSON with `stocks` array and `alerts` object

### Data Structure
```json
{
  "stocks": [
    {
      "code": "600519",
      "name": "贵州茅台",
      "target_price": 2000,
      "stop_loss": 1500,
      "notes": "长期持有",
      "added_at": "2026-05-29 12:00:00",
      "updated_at": "2026-05-29 12:00:00"
    }
  ],
  "alerts": {}
}
```

### Alert Logic (CRITICAL)

#### Price Change Alert
```python
if abs(stock["change_pct"]) >= 5.0:  # Default threshold
    # Trigger alert
```

#### Target Price Alert
```python
# Only trigger when price >= target_price
if stock.get("target_price") and stock["price"] >= stock["target_price"]:
    # Trigger alert
```

#### Stop Loss Alert ⚠️
```python
# Only trigger when price FALLS BELOW stop_loss
if stock.get("stop_loss") and stock["price"] <= stock["stop_loss"]:
    # Trigger alert
```

**IMPORTANT**: Stop loss should be set BELOW the buy price. The alert triggers when the price DROPS to or below the stop loss level.

### Real-time Quote Integration
For accurate lead/lag stock percentages, use Sina API:
```python
from services.kline import get_sina_quote

quote = get_sina_quote(code)
if quote and quote.get('price') and quote.get('pre_close'):
    pct = (quote['price'] - quote['pre_close']) / quote['pre_close'] * 100
    stock_quotes[code] = round(pct, 2)
```

### Telegram Integration
```python
def send_telegram_alert(message):
    token = "BOT_TOKEN"
    chat_id = "CHAT_ID"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=10)
    return resp.status_code == 200
```

### UI Pattern for Watchlist Table
```javascript
// Show both name and code
<td>${s.name} (${s.code})</td>

// Color-coded target/stop prices
const targetHtml = s.target_price ? `<span style="color:#4CAF50">${s.target_price}</span>` : '-';
const stopHtml = s.stop_loss ? `<span style="color:#ef5350">${s.stop_loss}</span>` : '-';

// Alert badges with icons
const badgeCls = a.level === 'danger' ? 'badge-red' : a.level === 'success' ? 'badge-green' : 'badge-orange';
const icon = a.type === 'price_change' ? '⚠️波动' : a.type === 'target_price' ? '🎯达标' : '🛑止损';
```
