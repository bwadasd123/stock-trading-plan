# 东财API端点诊断（2026-06-10更新）

## ⚠️ 域名路由矩阵（已确认）

| 域名 | 股票列表(clist) | K线(kline) | 个股详情(stock/get) | 直连 | 代理 |
|------|----------------|------------|-------------------|------|------|
| `push2delay.eastmoney.com` | ✅ | ❌ **返回空数据** | ✅ | ✅ | ✅ |
| `push2his.eastmoney.com` | ✅ | ✅ **必须走代理** | ✅ | ❌ 拒绝 | ✅ |
| `push2.eastmoney.com` | ❌ | ❌ | ❌ | ❌ 拒绝 | ❌ 拒绝 |
| `push2ex.eastmoney.com` | ❌ | ❌ | ❌ | ❌ 404 | ❌ 404 |

**关键发现（2026-06-10）**：
1. `push2delay` 的 K线接口返回 `dktotal:0, klines:[]` — 空数据，永远不能用于K线
2. `push2his` 直连被拒绝，但代理IP可以访问
3. `push2` 完全不可用（直连和代理都拒绝）

## 代码配置规则

```python
# K线数据 → push2his + 代理
url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
resp = safe_get(url, headers=headers, params=params, timeout=10)

# 股票列表 → push2delay（直连或代理都行）
url = "http://push2delay.eastmoney.com/api/qt/clist/get"
resp = safe_get(url, headers=headers, params=params, timeout=15)

# 个股详情 → push2delay
url = "http://push2delay.eastmoney.com/api/qt/stock/get"
resp = safe_get(url, headers=headers, params=params, timeout=10)
```

## 502 错误诊断

当 `push2.eastmoney.com` 返回 502 时，按以下顺序排查：

```bash
# 1. 检查连通性
ping -c 2 push2.eastmoney.com

# 2. 测试其他东财域名
curl -s -o /dev/null -w "%{http_code}" "http://quote.eastmoney.com/"
curl -s -o /dev/null -w "%{http_code}" "http://data.eastmoney.com/"

# 3. 测试K线API（需代理）
# 见 proxy-pool-management.md

# 4. 检查代理设置
echo $HTTP_PROXY $HTTPS_PROXY
```

## 代理相关

**⚠️ 用户明确要求：绝对不用本地代理（172.25.176.1:2080），只用宜代理API返回的代理IP。**

宜代理API返回的代理IP格式：`IP:PORT`（动态IP，每次调用返回不同IP）。
- 代理可访问：`httpbin.org`、`push2delay.eastmoney.com`、`push2his.eastmoney.com`
- 代理无法访问：`push2.eastmoney.com`（连接被拒）

WSL环境代理陷阱：
- 系统可能设置了错误的代理（如 `192.168.80.1:2080`）
- 检查方式：`echo $HTTP_PROXY $HTTPS_PROXY`
- 清除代理测试：`unset HTTP_PROXY HTTPS_PROXY`

## K线请求超时

K线通过代理访问push2his，单次请求可能需要5-15秒：
- API端点timeout: 30秒以上
- 前端等待超时: 60秒
- Flask刚启动时代理池未就绪，前几次请求可能超时
