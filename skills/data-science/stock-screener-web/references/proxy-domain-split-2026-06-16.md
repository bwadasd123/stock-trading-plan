# 代理域名分工方案 (2026-06-16最终版)

## 核心发现

宜代理IP只能访问 `push2delay.eastmoney.com`，**不能**访问 `push2his.eastmoney.com`。

### 测试验证
```
代理 → push2delay.eastmoney.com/api/qt/clist/get  ✅ 200 OK
代理 → push2his.eastmoney.com/api/qt/stock/kline/get  ❌ ProxyError/ConnectionError/HTTP 436/618
代理 → push2delay.eastmoney.com/api/qt/stock/kline/get  ✅ 200 OK 但 klines: [] (空数据)
直连 → push2his.eastmoney.com/api/qt/stock/kline/get  ✅ 200 OK + 完整K线数据
```

### 结论
- `push2delay` 的 K 线接口返回空数据（dktotal=0, klines=[]）
- `push2his` 的 K 线接口返回真实数据，但代理访问不了
- **K线数据只能直连获取**

## 架构分工

| 数据类型 | 接口域名 | 连接方式 |
|---------|---------|---------|
| 股票列表(clist) | push2delay | 代理 ✅ |
| 个股详情(stock) | push2delay | 代理 ✅ |
| K线数据(kline) | push2his | **直连 only** |

## 代码实现

### kline.py - K线获取（直连）
```python
def get_kline_data(code, period="101", limit=250):
    secid = convert_code(code)
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    # ... params ...
    headers = get_kline_headers(code)
    
    # push2his只能直连，代理访问不了
    from anti_crawl import _direct_get
    resp = _direct_get(url, headers=headers, params=params, timeout=10)
```

### anti_crawl.py - 直连函数
```python
def _direct_get(url, headers, params=None, timeout=10):
    """直连请求（直接用requests.get，不走代理不走Session）"""
    direct_headers = headers.copy()
    direct_headers["Cookie"] = COOKIE_MANAGER.get_cookie()
    resp = requests.get(url, headers=direct_headers, params=params, timeout=timeout,
                        verify=False, allow_redirects=True)
    # ... validation ...
    return resp
```

### anti_crawl.py - 代理健康检查（用push2delay）
```python
def _check_proxy_health(self, proxy_str):
    test_url = "http://push2delay.eastmoney.com/api/qt/clist/get"
    # 代理能访问push2delay，不能访问push2his
    proxies = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
    resp = requests.get(test_url, proxies=proxies, params=test_params, timeout=8)
    return resp.status_code == 200 and resp.text.startswith("{")
```

### scanner.py - 列表获取（代理）
```python
url = "http://push2delay.eastmoney.com/api/qt/clist/get"
resp = safe_get(url, headers=headers, params=params, timeout=15)  # 走代理
```

## 陷阱记录

1. **代理健康检查不能用push2his** — 如果用push2his做健康检查，所有代理都会失败，代理池为空，所有请求都降级到直连
2. **push2delay的K线接口返回空** — 虽然代理能访问push2delay，但它的kline/get返回klines:[]，不能用
3. **Session连接池问题** — `_direct_get()`不能用共享SESSION，必须用`requests.get()`直接请求
4. **Session(trust_env=False)也不可靠** — 在WSL环境下可能触发SOCKS依赖问题
5. **代理池初始化不检查健康** — 避免初始化太慢，直接添加代理到池中，实际使用时再验证

## 系统代理注意

WSL环境有系统代理 `172.29.192.1:2080`（通过环境变量 http_proxy/https_proxy）。
`requests.get()` 会自动使用系统代理，这对直连是OK的（系统代理可以转发到push2his）。
不要设置 `trust_env=False` 或手动清空proxies，否则可能导致SOCKS依赖问题。
