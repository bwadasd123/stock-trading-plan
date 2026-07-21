# 代理池当前实现 (2026-06-17更新)

## 架构: random.choice + mark_bad + blacklist + refill

```
ProxyPool
  ├── proxies: List[str]       # 可用代理列表
  ├── _bad_proxies: set        # 坏代理黑名单（2026-06-17新增）
  ├── _bad_clear_time: float   # 上次清理黑名单时间
  ├── target_size: int = 3     # 目标大小
  ├── get()                    # random.choice, 池空→_refill(2), 5分钟清黑名单
  ├── mark_bad(proxy)          # 移除 + 加入_bad_proxies + 后台_refill_async(1)
  ├── _refill(count)           # 同步补充: 跳过_bad_proxies
  └── _refill_async(count)    # 异步补充: 跳过_bad_proxies，多试几次
```

### 黑名单机制（2026-06-17）
**问题**: mark_bad移除代理→_refill_async补新代理→但API可能返回同一个IP→加回来→循环失败。
**解决**: `_bad_proxies` set记录失效IP，`_refill`和`_refill_async`补充时跳过。5分钟自动清一次（允许重试）。
```python
# mark_bad时加入黑名单
self._bad_proxies.add(proxy_str)

# refill时跳过
if p not in self.proxies and p not in self._bad_proxies:
    self.proxies.append(p)

# _refill_async多试几次，跳过坏代理
for _ in range(count * 2):
    p = get_proxy_from_api()
    if p in self._bad_proxies:
        continue  # 跳过，继续获取新IP
```
get_proxy_dict()
  └── PROXY_POOL.get() → {"http": url, "https": url}

safe_get(url, headers, params, max_retries=10)
  ├─ 首次: get_proxy_dict()
  │   有代理 → 用
  │   无代理 → 等3秒重试 → 等5秒重试 → return None
  ├─ consecutive_failures = 0  # 连续失败计数器
  ├─ 重试循环:
  │   consecutive_failures >= 3:
  │     invalidate Cookie → get_cookie() → 重置计数器
  │   attempt > 0:
  │     mark_bad(旧代理)     # 移除出池子
  │     get_proxy_dict()     # 取新代理
  │     有 → 用
  │     无 → 等3秒再取 → 等5秒继续循环
  ├─ 请求:
  │   200 + valid JSON → consecutive_failures=0 → return (成功)
  │   200 + bot detected → invalidate Cookie → consecutive_failures++ → continue
  │   407 → mark_bad → consecutive_failures++ → continue
  │   其他HTTP → mark_bad → consecutive_failures++ → continue
  │   Timeout/ConnectionError → mark_bad → consecutive_failures++ → sleep(3) → continue
  └─ 全部重试失败 → return None
```

## 关键行为
1. **绝不走本地直连** - 池子空就等待，不会降级到直连
2. **代理有效期短** - API返回的代理可能很快过期，所以失败就mark_bad换新的
3. **mark_bad = 从池子移除 + 加入黑名单** - 移除出池子，记录到_bad_proxies防止补回来
4. **_refill_async不检查健康** - 直接添加到池子，让实际使用时检测
5. **Cookie 120秒缓存** - Playwright获取真实Cookie，缓存2分钟
6. **重试10次** - 默认max_retries=10
7. **连续失败3次换Cookie** - consecutive_failures计数器，成功重置为0
8. **黑名单5分钟清一次** - 允许重试之前的坏代理（IP可能重新分配）

## 代理API
- 提供商: 宜代理 (ydaili.cn)
- 获取方式: HTTP GET → 返回 `ip:port` 纯文本
- 配置详见: proxy-api-config.md

## 注意事项
- 代码中显示 `secret=***` 是系统安全遮蔽，实际密钥正确
- 每次调用API返回一个代理，代理可能重复（提供商IP池小）
- **_bad_proxies黑名单防止坏代理被补回来** - `_refill`和`_refill_async`都检查
- `_refill_async`会多试几次（count*2），跳过黑名单里的IP
- 扫描每只股票需要3次代理请求（1次列表+2次K线双版本），2线程并行
