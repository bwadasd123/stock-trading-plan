# WSL VPN Proxy Issues

## Problem

WSL environment has system-wide proxy set by Windows VPN/Clash:

```bash
HTTP_PROXY=http://172.20.64.1:2080
HTTPS_PROXY=http://172.20.64.1:2080
ALL_PROXY=http://172.20.64.1:2080
```

This causes **ALL HTTPS traffic** to be intercepted at the network level, not just HTTP proxy level.

## What DOESN'T Work

| Approach | Result |
|----------|--------|
| `requests.get(url, proxies={})` | Still routes through VPN proxy |
| `requests.Session(trust_env=False)` | Sometimes works, sometimes doesn't (VPN state dependent) |
| `os.environ['NO_PROXY'] = '*'` | Doesn't affect already-imported modules |
| `http.client.HTTPSConnection` | Gets `RemoteDisconnected` - VPN intercepts at network level |
| `curl --noproxy '*'` | Also fails - VPN transparent proxy |

## What DOES Work

### 1. External Proxy Pool (Reliable)

Use proxies from external APIs (e.g., ydaili.cn) that route through different networks:

```python
# anti_crawl.py - get_proxy_dict() returns external proxy
proxies, proxy_str = get_proxy_dict()
resp = requests.get(url, proxies=proxies, timeout=15)
```

**Pitfall**: Proxy API keys expire. Error message: `"secret解密失败，请重新生成API链接！"` with status `207`. Need to regenerate API link from provider dashboard.

### 2. `http.client` with `ProxyHandler({})` (Sometimes Works)

When VPN is in certain states, this can bypass:

```python
import http.client, ssl
from urllib.parse import urlencode

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = http.client.HTTPSConnection("push2.eastmoney.com", context=ctx, timeout=15)
params = urlencode({"pn": 1, "pz": 5, ...})
conn.request("GET", f"/api/qt/clist/get?{params}", 
             headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"})
resp = conn.getresponse()
raw = resp.read().decode("utf-8")
conn.close()
```

**Warning**: This is unreliable - may work one session and fail the next depending on VPN state.

### 3. Start Flask Without Proxy Env Vars

```bash
cd /home/jmy/stock-screener && env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u NO_PROXY python app.py
```

**Caveat**: Even with env vars unset, the VPN may still intercept at network level.

## Diagnosis Commands

```bash
# Check proxy env vars
env | grep -i proxy

# Check routing (default gateway = VPN gateway)
ip route | grep default

# Test direct connection
curl -v --noproxy '*' https://push2.eastmoney.com/ 2>&1 | head -20

# Test with VPN proxy
curl -s -x http://172.20.64.1:2080 'https://push2.eastmoney.com/' 2>&1 | head -5

# Test external proxy
curl -s -x http://EXTERNAL_PROXY:PORT 'https://push2.eastmoney.com/' 2>&1 | head -5
```

## Decision Tree

```
Need to call East Money API?
├── Is this a high-volume batch operation (scanner)?
│   └── Use anti_crawl.safe_get() with proxy pool
│       └── If proxy pool empty → check proxy API key
├── Is this a single dashboard request (今日看点)?
│   └── Try requests.Session(trust_env=False) first
│       └── If fails → use http.client direct
│           └── If fails → fall back to proxy pool
└── Is this a constituent stock query (outflow stocks)?
    └── Use http.client direct (ProxyHandler({}))
        └── If fails → skip (non-critical data)
```

## Critical: Cookie Caching Bug (2026-06-01)

The `EastMoneyCookieManager.get_cookie()` in `anti_crawl.py` had a caching bug that made the scanner 10-50x slower. When Playwright fails (always, without `playwright install chromium`), the fallback cookie was NOT cached. Every API call retried Playwright (2-5 seconds each to fail).

**Fix**: Cache the fallback cookie in both the empty-cookie and exception branches. See pitfall #42 in SKILL.md for the exact code change.

**Impact**: Scanner went from "73 → 0只" (all pages timing out) to "74 → 74只" (normal).

## Proxy Pool Maintenance

### Checking Proxy Pool Health

```python
from anti_crawl import PROXY_POOL, PROXY_STATUS
print(f"Pool size: {PROXY_POOL.size}")
print(f"Current: {PROXY_STATUS['current']}")
print(f"Total used: {PROXY_STATUS['total_used']}")
```

### Proxy API Key Expiration

Symptoms:
- All proxy requests fail
- Logs show: `⚠️ 代理API返回错误: secret解密失败`
- Pool size stays at 0 or rapidly depletes

Fix:
1. Login to proxy provider dashboard (e.g., ydaili.cn)
2. Regenerate API link
3. Update `PROXY_CONFIG["PROXY_GET_URL"]` in `anti_crawl.py`
4. Restart Flask server

### Manual Proxy Test

```python
from anti_crawl import get_proxy_from_api
proxy = get_proxy_from_api()
print(f"Got proxy: {proxy}")

if proxy:
    import requests
    r = requests.get("https://push2.eastmoney.com/api/qt/clist/get",
                     proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
                     timeout=10, verify=False)
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
```
