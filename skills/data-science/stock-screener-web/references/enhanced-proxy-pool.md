# Enhanced Proxy Pool

## Overview

Enhanced proxy pool with proxy reuse, health checking, and monitoring capabilities.

## Key Features

### 1. Proxy Reuse
- **无使用次数限制** — 代理能用就一直用，失败再换
- 减少代理API调用
- 随机选择可用代理

### 2. Health Checking
- **用eastmoney.com测试代理**（不是httpbin.org）
- 代理池初始化和补充都带健康检查
- 失败代理标记并移除
- 失败时自动补充新代理

### 3. Cookie刷新
- 代理失败时自动刷新Cookie
- 重新获取Cookie后重试请求
- 避免因Cookie过期导致的请求失败

### 4. 代理优先，直连兜底
- **优先使用代理**，代理全部失败时自动降级到直连
- 代理失败3次后立即降级，不要浪费时间
- 直连必须用 `requests.get` 直接请求，不能用共享SESSION

## API Endpoints

### GET /api/proxy_pool/stats
Returns proxy pool statistics:
```json
{
  "success": true,
  "data": {
    "pool_size": 10,
    "target_size": 10,
    "total_requests": 100,
    "successful_requests": 95,
    "failed_requests": 5,
    "proxy_switches": 3,
    "last_proxy": "1.2.3.4:8080"
  }
}
```

### POST /api/proxy_pool/refresh
Manually refresh proxy pool:
```json
{
  "success": true,
  "message": "代理池已刷新",
  "data": { ... }
}
```

### GET /api/proxy_pool/health
Health check:
```json
{
  "success": true,
  "healthy": true,
  "data": { ... }
}
```

## Implementation Details

### Class: EnhancedProxyPool
Location: `anti_crawl.py`

```python
class EnhancedProxyPool:
    def __init__(self, target_size=10):
        self.target_size = target_size
        self.proxies = {}  # {proxy_str: {"last_used": None, "created": None}}
```

### Key Methods
- `get()` - Get a proxy from pool (无使用次数限制)
- `mark_bad(proxy_str)` - Mark proxy as failed
- `mark_success()` - Increment success counter
- `mark_failure()` - Increment failure counter
- `get_stats()` - Get pool statistics
- `_check_proxy_health(proxy_str)` - 用eastmoney.com测试代理健康状态

### Monitoring Thread
- Runs every 60 seconds
- Checks pool size
- Auto-refills when needed
- **简化逻辑** — 只检查池大小，避免访问不存在的字典key

### ⚠️ 代理字典必须包含uses字段 (2026-06-17)
`self.proxies[p]`初始化时必须有`"uses": 0`，否则`_monitor_pool`访问`info["uses"]`会KeyError崩溃。

**所有添加代理的地方都要检查：**
- `_fill_on_init` — 初始化填充
- `_refill` — 同步补充
- `_refill_async` — 异步补充
- `_replace_proxy` — 替换代理

**正确格式：**
```python
self.proxies[p] = {
    "uses": 0,           # 必须！
    "last_used": None,
    "created": datetime.now()
}
```

**症状：** 日志出现 `Exception in thread Thread-3 (_monitor_pool): KeyError: 'uses'`

## Usage

### In safe_get()
```python
def safe_get(url, headers, params=None, timeout=10, max_retries=3):
    """代理优先，直连兜底"""
    # 优先使用代理
    use_proxies, proxy_str = get_proxy_dict()
    if not proxy_str:
        logger.warning("⚠️ 无法获取代理，直接使用直连")
        return _direct_get(url, headers, params, timeout)
    
    # 代理重试逻辑
    for attempt in range(max_retries):
        try:
            resp = SESSION.get(url, proxies=use_proxies, timeout=timeout)
            if resp.status_code == 200:
                return resp
        except Exception as e:
            # 代理失败，切换新代理
            if proxy_str:
                PROXY_POOL.mark_bad(proxy_str)
            time.sleep(2)  # 2秒间隔
    
    # 代理全部失败，降级到直连
    logger.error(f"❌ 代理请求失败，已重试 {max_retries} 次: {url}")
    logger.info(f"🔄 代理全部失败，降级到直连: {url}")
    return _direct_get(url, headers, params, timeout)
```

### Direct Connection Fallback
```python
def _direct_get(url, headers, params=None, timeout=10):
    """直连请求（直接用requests.get，避免Session连接池问题）"""
    try:
        direct_headers = headers.copy()
        direct_headers["Cookie"] = COOKIE_MANAGER.get_cookie()
        # 使用requests.get直接请求，避免Session连接池问题
        resp = requests.get(
            url,
            headers=direct_headers,
            params=params,
            timeout=timeout,
            verify=False,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            if is_bot_detected(resp.text):
                logger.warning(f"🤖 直连也被反爬拦截: {url}")
                return None
            if is_valid_json_response(resp.content):
                logger.info(f"✅ 直连成功: {url}")
                return resp
        logger.warning(f"⚠️ 直连也失败 (HTTP {resp.status_code}): {url}")
    except Exception as e:
        logger.error(f"❌ 直连异常: {e}")
    return None
```

### Monitoring
```python
stats = get_proxy_pool_stats()
if stats["pool_size"] == 0:
    logger.warning("代理池为空！")
```

## ⚠️ SESSION连接池陷阱

### 问题
`requests.Session` 对象会复用TCP连接，但东方财富服务器会主动关闭空闲连接，导致后续请求失败。

### 症状
```python
# 直接请求成功
resp = requests.get(url, headers=headers, timeout=10)  # ✅ 成功

# SESSION请求失败
resp = SESSION.get(url, headers=headers, timeout=10)  # ❌ ConnectionError
```

### 错误信息
```
ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

### 解决
直连fallback必须用 `requests.get()` 直接请求，不能用共享SESSION。

## Troubleshooting

### Pool Empty
1. Check proxy API configuration
2. Verify network connectivity
3. Check proxy API quota
4. Use `/api/proxy_pool/refresh` to manually refill
5. **自动降级到直连** — 代理池为空时自动使用直连

### High Failure Rate
1. Check proxy quality
2. Verify target website accessibility
3. **用eastmoney.com测试代理健康状态**（不是httpbin.org）
4. 检查Cookie是否过期（代理失败时自动刷新）

### Performance Issues
1. Increase `target_size` for more proxies (default: 10)
2. **无使用次数限制** — 代理能用就一直用
3. Monitor `proxy_switches` rate
4. **快速降级** — 代理失败3次后立即降级到直连
