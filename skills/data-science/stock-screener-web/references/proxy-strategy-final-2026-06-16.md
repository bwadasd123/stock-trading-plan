# 代理策略最终版 (2026-06-16)

## 核心发现

### 1. 代理访问能力
- **push2delay.eastmoney.com** — 代理可用 ✅
- **push2his.eastmoney.com** — 代理可用 ✅（但短效代理容易过期）
- **系统代理(172.29.192.1:2080)** — push2his返回502 ❌

### 2. 关键问题
- 代理是**短效的**，放进池子可能很快就过期
- 系统代理对push2his返回502，所以直连fallback不可靠
- `ALL_PROXY`环境变量(socks5://)会导致"Missing dependencies for SOCKS support"错误

### 3. 最终方案

#### 代理池策略
```
池大小: 3个（小一点没事，主要是保持能用）
健康检查: _fill_on_init用push2delay检查，_refill_async不检查健康
补充策略: 代理失败时自动补充新代理（不检查健康，让实际使用时检测）
```

#### 数据获取策略
```
股票列表(clist) → push2delay + 代理池
K线数据(kline) → push2his + 代理池（代理失败自动换新代理重试）
直连fallback → _direct_get()（但系统代理返回502，不可靠）
```

#### 配置参数
```
PROXY_POOL_TARGET_SIZE = 3
max_retries = 2（safe_get重试次数）
delay = 2（重试间隔秒数）
Cookie TTL = 120秒（2分钟）
```

#### 代码实现
```python
# kline.py - K线获取用代理池
resp = safe_get(url, headers=headers, params=params, timeout=10)

# anti_crawl.py - 代理池补充不检查健康
def _refill_async(self, count):
    p = get_proxy_from_api()
    if p:
        with self.lock:
            if p not in self.proxies and len(self.proxies) < self.target_size:
                self.proxies[p] = {"last_used": None, "created": datetime.now()}

# anti_crawl.py - 直连清除SOCKS代理
def _direct_get(url, headers, params=None, timeout=10):
    import os
    os.environ.pop('all_proxy', None)
    os.environ.pop('ALL_PROXY', None)
    # ... requests.get(...)
```

## 用户偏好
- 池子小一点没事，主要是保持能用
- Cookie 720秒太久了，改成120秒
- 代理有时候能一直用，所以要用池子不要每次实时获取
