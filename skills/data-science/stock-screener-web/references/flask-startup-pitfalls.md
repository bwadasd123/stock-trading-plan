# Flask后台启动与进程输出捕获

## 问题
`terminal(background=true)` 不捕获Python stdout。进程运行但output为空。

## 解决方案

### 方案1: tee重定向
```bash
bash -c 'python3 -u app.py 2>&1 | tee /tmp/stock_app.log'
```

### 方案2: 日志文件
```python
# app.py中配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler("/tmp/stock_app.log"),
        logging.StreamHandler()
    ]
)
```

### 方案3: nohup
```bash
nohup python3 -u app.py > /tmp/stock_app.log 2>&1 &
```

## Flask启动阻塞问题

### 原因
`init_anti_crawl()` 会初始化代理池（5个IP，每个3-5秒），总计约30秒。

### 解决: 异步初始化
```python
import threading

def init_async():
    try:
        from anti_crawl import init_anti_crawl
        init_anti_crawl()
    except Exception as e:
        logger.error(f"反爬模块初始化失败: {e}")

init_db()  # 数据库先初始化
threading.Thread(target=init_async, daemon=True).start()  # 反爬模块异步初始化

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
```

## Playwright浏览器未安装
- 错误: `Executable doesn't exist at .../chrome-headless-shell`
- 解决: `playwright install chromium`
- 如果下载超时(网络问题)，会自动fallback到伪造Cookie
- 不影响核心功能，只是Cookie质量降低

## ⚠️ 启动验证检查清单（必须执行）

**永远不要报告"服务已启动"而不验证：**
```bash
# 1. 杀掉所有残留进程
pkill -9 -f "python3.*app.py" 2>/dev/null; sleep 2

# 2. 启动
python3 -u app.py &

# 3. 等待代理池初始化（约30秒）
sleep 30

# 4. 验证三步
ss -tlnp | grep 8080 && echo "✅ 端口已监听" || echo "❌ 端口未监听"
curl -s --connect-timeout 5 http://127.0.0.1:8080/ | head -5
ps aux | grep app.py | grep -v grep
```

**常见失败模式：**
- 进程存在但端口未监听 → 代理API阻塞或Flask初始化卡住
- 端口监听但curl返回空 → Flask路由问题或模板渲染错误
- curl超时 → 检查HTTP_PROXY环境变量（可能走代理访问localhost）

## ⚠️ 环境变量陷阱

WSL环境中可能有 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量。`requests` 库会自动使用这些代理：
```bash
echo $HTTP_PROXY  # 可能是 http://192.168.80.1:2080
echo $NO_PROXY    # 通常包含 localhost,127.0.0.1
```

Flask服务本身不受影响（监听socket），但**测试请求**可能走代理：
- `curl` 会读取 `NO_PROXY`，通常能正确访问 localhost
- Python `requests` 库需要显式 `proxies={'http': None, 'https': None}` 或设置 `NO_PROXY`

## ⚠️ 重复代理池实例化

anti_crawl.py 中有两个代理池类：
1. 旧 `ProxyPool`（line ~154）：`PROXY_POOL = ProxyPool(PROXY_POOL_TARGET_SIZE)`
2. 新 `EnhancedProxyPool`（文件末尾）：`ENHANCED_PROXY_POOL = EnhancedProxyPool(...)`

两者都在模块级实例化，都会启动 daemon 线程调用代理API。如果代理API慢，两个池同时初始化会加倍耗时。建议注释掉旧的 `PROXY_POOL` 初始化。

## ⚠️ logging.Handler子类锁死锁（2026-06-16发现）

### 问题
`logging.Handler.__init__` 创建 `self.lock = threading.RLock()`（可重入锁）。
`handle()` 方法流程：`acquire(self.lock)` → `emit(record)` → `release(self.lock)`。

如果子类在 `__init__` 中写了 `self.lock = threading.Lock()`（非可重入锁），则：
1. `handle()` 调用 `self.acquire()` 获取 `self.lock`（现在是 Lock，不是 RLock）
2. `handle()` 调用 `self.emit(record)`
3. 子类 `emit()` 中 `with self.lock:` → 尝试再次获取同一把锁
4. **死锁！** Lock 不允许同一线程重入。

### 症状
- `python3 app.py` 进程存在，但端口永远不监听
- 日志输出到 `init_db()` 的 `logger.info("✅ 数据库表初始化完成")` 后就停住
- `curl localhost:8080` 返回 "Connection refused"
- 用 timeout 运行会 exit code 124（超时）

### 诊断
```python
import sys, threading, time, faulthandler
faulthandler.enable()

def watchdog():
    time.sleep(5)
    import traceback
    for thread_id, frame in sys._current_frames().items():
        print(f'=== Thread {thread_id} ===')
        traceback.print_stack(frame)
threading.Thread(target=watchdog, daemon=True).start()
```

在主线程栈中会看到：
```
File "api/log_stream.py", line 63, in emit
    with self.lock:  # ← 卡在这里
```

### 修复
```python
# ❌ 错误：self.lock 覆盖父类的 RLock
class LogStreamHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()  # 覆盖了父类的 self.lock！

# ✅ 正确：用不同名字
class LogStreamHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.sub_lock = threading.Lock()  # 不冲突
```

### 通用规则
**任何继承 `logging.Handler` 的子类，永远不要使用 `self.lock` 作为属性名。**
父类的 `handle()` → `acquire()`/`release()` 依赖 `self.lock`，覆盖它会导致死锁或竞态条件。
