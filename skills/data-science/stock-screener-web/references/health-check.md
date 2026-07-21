# System Health Check Procedure

## Quick Health Check Command

Run this after startup or after changes to verify all endpoints:

```bash
# Full endpoint test (correct paths)
for ep in / /arbitrage /report /api/sector/flow /api/sector/top /api/task_history /api/history /api/history/stats /api/history/hot /api/dragon /api/watchlist /api/report_data /api/arbitrage /api/proxy_status /api/presets /api/daily/digest /api/kline /api/analyze /api/dual_scan_progress /api/dual_scan_results; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080${ep}" 2>/dev/null)
  printf "%-30s -> %s\n" "$ep" "$code"
done
```

## Component Checks

### Database
```bash
cd /home/jmy/stock-screener
/home/jmy/.hermes/hermes-agent/venv/bin/python -c "
from config import MYSQL_CONFIG
import pymysql
conn = pymysql.connect(**MYSQL_CONFIG)
cur = conn.cursor()
cur.execute('SHOW TABLES')
tables = [r[0] for r in cur.fetchall()]
print('Tables:', len(tables), tables[:10])
conn.close()
"
```

### Proxy Pool
```bash
curl -s http://localhost:8080/api/proxy_status | python3 -c "import sys,json; d=json.load(sys.stdin); print('Pool:', d.get('pool_size'), 'Available:', d.get('available'))"
```

### Watchlist / Presets
```bash
curl -s http://localhost:8080/api/watchlist | python3 -c "import sys,json; d=json.load(sys.stdin); print('Watchlist:', len(d.get('stocks', [])))"
curl -s http://localhost:8080/api/presets | python3 -c "import sys,json; d=json.load(sys.stdin); print('Presets:', len(d.get('presets', {})))"
```

## Known Endpoint Issues

*None currently — all endpoints return 200 as of 2026-06-08.*

### Previously Fixed: /api/sector/top was returning HTTP 500
- **Fix**: Added `try/except` wrapper to `api_sector_flow()` and `api_sector_top()` in `api/sector.py`
- **Lesson**: All API endpoints in `api/*.py` should have top-level try/except with logger.error() — prevents unhandled exceptions from returning 500 even when data is valid

## Expected Endpoint Map (correct paths)

| Endpoint | Method | Page |
|----------|--------|------|
| `/` | GET | Main dashboard |
| `/arbitrage` | GET | Arbitrage page |
| `/report` | GET | Report page |
| `/api/scan_all` | POST | Start scan |
| `/api/scan_progress` | GET | SSE progress |
| `/api/scan_results` | GET | Get results |
| `/api/sector/flow` | GET | Sector fund flow |
| `/api/sector/top` | GET | Top sectors |
| `/api/task_history` | GET | Task history |
| `/api/history` | GET | Signal history (params: days, page, limit, sort, dedup, code, **version**) |
| `/api/history/stats` | GET | History statistics |
| `/api/history/hot` | GET | Hot signals |
| `/api/history/dates` | GET | History dates |
| `/api/dragon` | GET | Dragon tiger |
| `/api/watchlist` | GET | Watchlist |
| `/api/report_data` | GET | Report JSON |
| `/api/arbitrage` | GET | Arbitrage targets |
| `/api/proxy_status` | GET | Proxy status |
| `/api/presets` | GET | Filter presets |
| `/api/daily/digest` | GET | Daily digest |
| `/api/kline` | GET | K-line data |
| `/api/analyze` | GET | Stock analysis |
| `/api/dual_scan_all` | POST | Start dual scan |
| `/api/dual_scan_progress` | GET | Dual scan SSE progress |
| `/api/dual_scan_results` | GET | Dual scan results |
| `/api/dual_scan_stop` | POST | Stop dual scan |
