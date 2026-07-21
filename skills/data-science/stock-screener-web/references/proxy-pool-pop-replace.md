# 代理池 Pop-Replace 模式（2026-06-16 最终版）

## 核心原则
1. 取出来用，成功还回，失败丢弃
2. **绝不走直连** — 池子空就等待重试，永远不暴露本地IP
3. 不过度设计 — 不要冷却池/黑名单

## 用户反馈
- "还加黑干啥啊 我都取出来了 用几次可能就用不了了 你理解吗？他补池子不就好了吗"
- "能改成池子空就等待吗 不然还会用我的本地"

## ProxyPool 实现
```python
class ProxyPool:
    def __init__(self, target_size=3):
        self.target_size = target_size
        self.proxies = []
        self.lock = threading.Lock()
        threading.Thread(target=self._fill_on_init, daemon=True).start()

    def get(self):
        with self.lock:
            if not self.proxies:
                self._refill(1)
            if not self.proxies:
                return None
            return self.proxies.pop(random.randint(0, len(self.proxies) - 1))

    def put_back(self, proxy):
        if not proxy:
            return
        with self.lock:
            if proxy not in self.proxies and len(self.proxies) < self.target_size:
                self.proxies.append(proxy)

    def mark_bad(self, proxy):
        pass  # 已不在池子

    def _refill(self, count):
        for _ in range(count * 3):
            if len(self.proxies) >= self.target_size:
                break
            p = get_proxy_from_api()
            if p and p not in self.proxies:
                self.proxies.append(p)

    def _refill_async(self, count):
        try:
            for _ in range(count * 3):
                p = get_proxy_from_api()
                if not p:
                    continue
                with self.lock:
                    if p not in self.proxies and len(self.proxies) < self.target_size:
                        self.proxies.append(p)
                        return
        except Exception as e:
            logger.warning(f"补充代理失败: {e}")
```

## safe_get — 只用代理，不走直连
```python
def safe_get(url, headers, params, timeout, max_retries=2):
    proxy = PROXY_POOL.get()
    if not proxy:
        time.sleep(3)
        proxy = PROXY_POOL.get()
        if not proxy:
            time.sleep(5)
            proxy = PROXY_POOL.get()
        if not proxy:
            return None

    use_proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    for attempt in range(max_retries):
        try:
            resp = SESSION.get(url, proxies=use_proxies, timeout=timeout)
            if resp.status_code == 200:
                PROXY_POOL.put_back(proxy)
                return resp
            elif resp.status_code in (407, 436):
                proxy = PROXY_POOL.get()
                if not proxy:
                    time.sleep(3)
                    proxy = PROXY_POOL.get()
                if not proxy:
                    return None
                use_proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
                continue
        except (ConnectionError, Timeout):
            proxy = PROXY_POOL.get()
            if not proxy:
                time.sleep(3)
                proxy = PROXY_POOL.get()
            if not proxy:
                return None
            use_proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            continue
    return None
```

## 注意事项
- _refill_async 检查 p not in self.proxies 防重复
- put_back 只成功时调用
- 池子大小3个
- Cookie TTL 120秒
- 407/436/连接错误 → 代理已不在池子，不用mark_bad
