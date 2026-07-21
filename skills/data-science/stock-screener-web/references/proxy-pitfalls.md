# Proxy & Network Pitfalls

## Proxy Pool Blocking Startup (CRITICAL)
`anti_crawl.py` `ProxyPool.__init__` calls `_fill_on_init()` synchronously. When proxy API key is expired (ydaili.cn), each `get_proxy_from_api()` retries 3× with 8s timeout + 2s sleep = 30s/attempt × 10 attempts = **up to 5 minutes blocking**.

**Fix**: Make non-blocking:
```python
# In ProxyPool.__init__:
threading.Thread(target=self._fill_on_init, daemon=True).start()
```

**Also**: `safe_get()` calls `get_proxy_dict()` → `PROXY_POOL.get()` → `_refill(2)` if empty. Every `safe_get` can block ~60s if proxy API is down.

## eastmoney API Endpoint Fallback (CRITICAL)
**`push2.eastmoney.com` can return 502 (nginx Bad Gateway).** When this happens, ALL stock list and sector flow requests fail — scanner gets 0 stocks, sector flow empty.

**Fallback**: Use `push2his.eastmoney.com` instead. Same API paths work on both hosts:
- `/api/qt/clist/get` — stock list (used by scanner, sector flow)
- `/api/qt/stock/get` — individual stock data
- `/api/qt/stock/kline/get` — K-line data (this was always on push2his)

**Important**: `push2his` works with **direct HTTP** (no proxy needed in WSL). `push2` also returns 502 on direct connection. So when push2 is down, proxy won't help — must switch to push2his.

**Migration**: Use `sed` to batch-replace across all .py files:
```bash
find . -name "*.py" -exec sed -i 's|push2\.eastmoney\.com|push2his.eastmoney.com|g' {} \;
```
Watch for `http.client.HTTPSConnection("push2.eastmoney.com")` in sector_flow.py — needs separate sed since it's not a URL format.

## Proxy 407 Authentication Failure → Direct Fallback
Proxy pool returns IPs that require authentication (407 Proxy Authentication Required). This means the ydaili proxy type may not match the expected format.

**Fix in `safe_get()`**: When HTTP 407 received, mark proxy as bad and try next proxy. If all proxies fail, fall back to direct connection:
```python
elif resp.status_code == 407:
    # 代理认证失败，只换代理
    logger.warning(f"⚠️ 代理认证失败(407)，切换新代理")
    if proxy_str:
        PROXY_POOL.mark_bad(proxy_str)
    time.sleep(1)
    continue
```

**After all retries failed**: Fall back to direct connection using `_direct_get()`:
```python
# 代理全部失败，降级到直连
logger.error(f"❌ 代理请求失败，已重试 {max_retries} 次: {url}")
logger.info(f"🔄 代理全部失败，降级到直连: {url}")
return _direct_get(url, headers, params, timeout)
```

**⚠️ SESSION连接池陷阱**: 直连必须用 `requests.get` 直接请求，不能用共享SESSION（连接池复用旧连接导致失败）。

## Proxy Pool Blocking Startup (CRITICAL)
`calculateScore()` in scanner.js:
```javascript
if (circCap && circCap <= 200)  // circCap=0 is falsy → fails!
```
When proxy fails, `circ_cap` defaults to 0, and JavaScript treats 0 as falsy. Shows "不通过" for 流通市值 check even though stock passes.

**Root fix**: Make the API call work (use proxy). **Frontend fix** (defensive): `if (circCap > 0 && circCap <= 200)`.

## api/scan.py Import Pitfall
When modifying `/api/analyze`, ensure these imports exist at top of `api/scan.py`:
```python
import re
import logging
logger = logging.getLogger(__name__)
```
The old code used local `import re as _re` and `import requests as _req` which were removed during cleanup. Without the top-level imports, you get `NameError: name 're' is not defined` → 500 error.

## Proxy API Key Renewal
- Provider: ydaili.cn
- Config: `anti_crawl.py` → `PROXY_CONFIG["PROXY_GET_URL"]`
- When expired: proxy pool empties → all eastmoney requests fail → circ_cap=0, scanner hangs
- Renewal: regenerate from ydaili.cn dashboard, update the URL

## SESSION Connection Pool Trap (2026-06-16)
`requests.Session` objects reuse TCP connections, but eastmoney servers actively close idle connections, causing subsequent requests to fail.

**Symptoms**:
```python
# Direct request succeeds
resp = requests.get(url, headers=headers, timeout=10)  # ✅ Success

# SESSION request fails
resp = SESSION.get(url, headers=headers, timeout=10)  # ❌ ConnectionError
```

**Error message**:
```
ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**Solution**: Direct connection fallback must use `requests.get()` directly, not shared SESSION.

## Monitor Thread KeyError (2026-06-16)
`_monitor_pool()` accesses `info["uses"]` but proxy info dict doesn't have this key, causing KeyError crash.

**Solution**: Simplify monitoring logic to only check pool size:
```python
def _monitor_pool(self):
    """监控代理池状态"""
    while True:
        time.sleep(60)  # 每分钟检查一次
        with self.lock:
            pool_size = len(self.proxies)
            # 简化监控：只检查池大小
            if pool_size < self.target_size:
                logger.warning(f"⚠️ 代理池不足: {pool_size}/{self.target_size}")
                threading.Thread(target=self._refill_async, args=(1,), daemon=True).start()
```
