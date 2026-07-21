# 代理池管理 - 宜代理 (ydaili)

## 架构

```
anti_crawl.py
├── PROXY_CONFIG          # 宜代理API配置 (secret, orderId)
├── ProxyPool             # 代理池类 (线程安全)
├── get_proxy_from_api()  # 从API获取单个代理IP
├── get_proxy_dict()      # 返回 (proxies_dict, proxy_str)
├── safe_get()            # 核心请求函数 (代理轮换+失败降级)
└── SESSION               # requests.Session(trust_env=False)
```

## 关键流程: safe_get()

```
1. get_proxy_dict() → 获取代理IP（必须获取到）
2. SESSION.get(url, proxies=代理IP) → 请求
3. 如果 200 → 返回
4. 如果 407 → mark_bad + 切换新代理 + 刷新Cookie
5. 如果 超时/连接错误 → mark_bad + 切换新代理 + 刷新Cookie
6. 最多重试5次，每次都切换新代理
7. 最后返回 None（不允许降级到直连）
```

## ⚠️ 关键陷阱: 必须使用代理（2026-06-16更新）

**用户明确要求**: 绝对不能降级到直连，必须使用代理。

**修复**: 移除 `proxy_failed` 标记和降级逻辑：
```python
for attempt in range(max_retries):
    if attempt > 0:
        PROXY_POOL.mark_bad(proxy_str)
        use_proxies, proxy_str = get_proxy_dict()
        if proxy_str:
            # 刷新Cookie
            COOKIE_MANAGER.invalidate()
            headers["Cookie"] = COOKIE_MANAGER.get_cookie()
        else:
            time.sleep(3)
            continue
    
    resp = SESSION.get(url, headers=headers, params=params, proxies=use_proxies, timeout=timeout)
    
    if resp.status_code == 200:
        return resp
    elif resp.status_code == 407:
        # 代理认证失败，切换新代理（不降级到直连）
        continue

return None  # 失败，不允许降级到直连
```

## 东财API端点（2026-06-10更新）

| 端点 | 股票列表(clist) | K线(kline) | 直连 | 代理 |
|------|----------------|------------|------|------|
| `push2delay.eastmoney.com` | ✅ | ❌ **返回空数据** | ✅ | ✅ |
| `push2his.eastmoney.com` | ✅ | ✅ **必须走代理** | ❌ 拒绝 | ✅ |
| `push2.eastmoney.com` | ❌ | ❌ | ❌ 拒绝 | ❌ 拒绝 |
| `push2ex.eastmoney.com` | ❌ | ❌ | ❌ 404 | ❌ 404 |

**重要**: K线数据只能通过 `push2his` + 代理获取。`push2delay` 的K线接口返回空数据（dktotal=0）。
详见 `references/eastmoney-domain-routing.md`。

## 用户偏好

- 用户管理代理池，"代理不会失效，没了我会补的"
- **永远不要质疑订单号是否过期**
- "代理池" = 宜代理API返回的代理IP，不是本地代理
- **⚠️ 不用本地代理** — 用户明确要求只用宜代理API的代理IP，不用本地代理(172.25.176.1:2080)。代码中不应有本地代理的fallback逻辑。

## 系统代理干扰

WSL环境变量可能设置 `HTTP_PROXY=http://192.168.80.1:2080`，这会导致:
- requests.get() 默认走系统代理 → 超时/502
- SESSION.trust_env=False 可避免此问题
- 但 safe_get 中 proxies={} 时仍受系统代理影响

**解决方案**: safe_get 始终使用 SESSION (trust_env=False)

## 代理池启动延迟

代理池在Flask启动时异步初始化（daemon thread），需要几秒填充：
- 启动后前几次请求可能因代理池为空而失败
- 测试API前等待3-5秒
- 代理池状态可通过 `/api/proxy_status` 检查
