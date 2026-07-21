# 代理池策略 (2026-06-16更新)

## 核心原则

1. **代理优先，直连兜底** — 优先使用代理，代理全部失败时自动降级到直连
2. **IP和Cookie独立处理** — 代理失败只换IP，反爬拦截只刷新Cookie
3. **快速降级** — 代理失败3次后立即降级，不要浪费时间

## 配置参数

```python
# anti_crawl.py
PROXY_POOL_TARGET_SIZE = 10  # 代理池大小
max_retries = 3  # 重试次数
delay = 2  # 重试间隔（秒）

# services/kline.py
timeout = 10  # K线获取超时（秒）
```

## 实现逻辑

### 1. 代理获取
```python
use_proxies, proxy_str = get_proxy_dict()
if not proxy_str:
    logger.warning("⚠️ 无法获取代理，直接使用直连")
    return _direct_get(url, headers, params, timeout)
```

### 2. 代理重试
```python
for attempt in range(max_retries):
    try:
        # 代理请求
        resp = SESSION.get(url, proxies=use_proxies, timeout=timeout)
        if resp.status_code == 200:
            return resp
    except Exception as e:
        # 代理失败，切换新代理
        if proxy_str:
            PROXY_POOL.mark_bad(proxy_str)
        time.sleep(delay)  # 2秒
```

### 3. 降级到直连
```python
# 代理全部失败，降级到直连
logger.error(f"❌ 代理请求失败，已重试 {max_retries} 次: {url}")
logger.info(f"🔄 代理全部失败，降级到直连: {url}")
return _direct_get(url, headers, params, timeout)
```

### 4. 直连实现（关键）
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

## 监控线程优化

### 问题
`_monitor_pool()` 访问 `info["uses"]` 但代理info字典没有该key，导致KeyError。

### 解决
简化监控逻辑，只检查池大小：
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

## 验证方法

### 1. 检查代理池状态
```bash
curl -s http://localhost:8080/api/proxy_status | python3 -m json.tool
```

### 2. 测试K线获取
```python
from services.kline import get_kline_data
data = get_kline_data('000001', period='101', limit=10)
print(f"数据条数: {len(data['klines'])}")
```

### 3. 观察日志
```bash
tail -f /tmp/stock-screener.log | grep -E "代理|直连|降级"
```

## 性能对比

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 代理池大小 | 5 | 10 |
| 重试次数 | 5 | 3 |
| 重试间隔 | 5秒 | 2秒 |
| K线超时 | 20秒 | 10秒 |
| 扫描速度 | 慢（卡在代理超时） | 快（快速降级到直连） |

## 关键教训

1. **代理质量比数量更重要** — 10个不稳定的代理不如5个稳定的代理
2. **快速降级是关键** — 代理失败时要快速降级到直连，不要浪费时间重试
3. **SESSION连接池是陷阱** — 东方财富服务器会关闭空闲连接，导致SESSION复用失败
4. **监控线程要简化** — 不要访问不存在的字典key，会导致线程崩溃
5. **配置修改后必须验证** — 修改代码后要重启服务并验证配置生效
