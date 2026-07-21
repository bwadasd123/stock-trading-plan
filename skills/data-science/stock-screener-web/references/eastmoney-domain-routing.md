# 东财API域名路由规则（2026-06-16最终版）

## 域名用途矩阵

| API路径 | push2delay (直连) | push2delay (代理) | push2his (直连) | push2his (代理) |
|---------|-------------------|-------------------|-----------------|-----------------|
| `/api/qt/clist/get` (股票列表) | ✅ | ✅ | - | ❌ 代理不可达 |
| `/api/qt/stock/get` (个股详情) | ✅ | ✅ | - | ❌ 代理不可达 |
| `/api/qt/stock/kline/get` (K线) | ❌ 空数据 | ❌ 空数据 | ✅ | ❌ 代理不可达 |
| `/api/qt/ulist.np/get` (ETF列表) | ✅ | ✅ | - | ❌ 代理不可达 |

## ⚠️ 关键约束（2026-06-16发现）

**宜代理IP只能访问 `push2delay.eastmoney.com`，不能访问 `push2his.eastmoney.com`**

### 测试验证
```
代理 → push2delay.eastmoney.com/api/qt/clist/get      ✅ 200 OK
代理 → push2delay.eastmoney.com/api/qt/stock/kline/get ✅ 200 OK 但 klines: [] (空)
代理 → push2his.eastmoney.com/api/qt/stock/kline/get   ❌ ProxyError / ConnectionError / HTTP 436 / 618
直连 → push2his.eastmoney.com/api/qt/stock/kline/get   ✅ 200 OK + 完整K线数据
```

### push2delay 的 K线接口返回空数据
```
GET http://push2delay.eastmoney.com/api/qt/stock/kline/get?secid=1.600519&klt=101&lmt=250
→ {"rc":0, "data":{"code":"600519","name":"贵州茅台","dktotal":0,"klines":[]}}
```
- `dktotal: 0` 表示没有K线数据
- 这是东财服务端行为，不是客户端问题

### push2his 只能直连
- 代理访问 push2his → 连接失败（代理服务商网络限制）
- 直连 push2his → 正常返回完整K线数据
- **系统代理** `172.29.192.1:2080` 可以转发到 push2his（通过环境变量 http_proxy）

## 架构分工

| 数据类型 | 接口域名 | 连接方式 |
|---------|---------|---------|
| 股票列表(clist) | push2delay | 代理（`safe_get`） |
| 个股详情(stock) | push2delay | 代理（`safe_get`） |
| K线数据(kline) | push2his | **直连 only**（`_direct_get`） |

## 代码实现

### K线获取（直连）— kline.py
```python
# ✅ 正确：push2his + 直连
url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
from anti_crawl import _direct_get
resp = _direct_get(url, headers=headers, params=params, timeout=10)

# ❌ 错误：push2delay的K线返回空
# url = "http://push2delay.eastmoney.com/api/qt/stock/kline/get"

# ❌ 错误：通过代理访问push2his（代理访问不了）
# resp = safe_get(url, ...)  # 代理会失败
```

### 股票列表（代理）— scanner.py
```python
# ✅ 正确：push2delay + 代理
url = "http://push2delay.eastmoney.com/api/qt/clist/get"
resp = safe_get(url, headers=headers, params=params, timeout=15)
```

### 直连函数 — anti_crawl.py
```python
def _direct_get(url, headers, params=None, timeout=10):
    """直连请求（直接用requests.get，不走代理不走Session）"""
    direct_headers = headers.copy()
    direct_headers["Cookie"] = COOKIE_MANAGER.get_cookie()
    resp = requests.get(url, headers=direct_headers, params=params, timeout=timeout,
                        verify=False, allow_redirects=True)
    return resp
```

### 代理健康检查 — anti_crawl.py
```python
# ✅ 用push2delay测试（代理能访问）
test_url = "http://push2delay.eastmoney.com/api/qt/clist/get"

# ❌ 不能用push2his测试（代理访问不了，会导致池子为空）
# test_url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
```

## 陷阱记录

1. **代理健康检查不能用push2his** — 所有代理都会失败，代理池为空
2. **push2delay的K线接口返回空** — 代理能访问但数据为空
3. **Session连接池复用旧连接** — `_direct_get()`不能用共享SESSION
4. **Session(trust_env=False)不可靠** — WSL下可能触发SOCKS依赖问题
5. **代理池初始化不检查健康** — 避免初始化太慢

## 诊断命令

```bash
# 测试代理能否访问push2delay
curl -x http://PROXY_IP:PORT -s "http://push2delay.eastmoney.com/api/qt/clist/get?pn=1&pz=1" | head -c 100

# 测试代理能否访问push2his（预期失败）
curl -x http://PROXY_IP:PORT -s "http://push2his.eastmoney.com/api/qt/stock/kline/get?secid=0.000001&klt=101&lmt=5" | head -c 100

# 测试直连push2his（预期成功）
curl -s "http://push2his.eastmoney.com/api/qt/stock/kline/get?secid=0.000001&klt=101&lmt=5" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'klines={len(d[\"data\"][\"klines\"])}')"
```

## 历史变更
- 2026-06-08: 发现push2返回502，改为push2his
- 2026-06-10: push2his直连也失败，发现push2delay可直连（但K线返回空）
- 2026-06-10: 确认push2his K线必须走代理
- **2026-06-16**: 发现代理访问不了push2his！K线改为直连，代理只用于列表数据
