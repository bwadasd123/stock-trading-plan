# ThreadPoolExecutor 停止模式 (2026-06-16)

## 问题

`ThreadPoolExecutor` 在 `with` 语句中使用时，无法从外部停止正在运行的任务。
用户点击"停止扫描"后，已提交的任务会继续执行完毕。

## 解决方案

使用全局executor引用 + `shutdown(wait=False, cancel_futures=True)`：

```python
# 全局变量
_current_executor = None
_executor_lock = threading.Lock()

# 启动扫描时
def run_full_scan(...):
    global _current_executor
    executor = ThreadPoolExecutor(max_workers=2)
    with executor:
        _current_executor = executor
        futures = [executor.submit(task, arg) for arg in args]
        for future in as_completed(futures):
            if not running:
                # 取消剩余任务
                for f in futures:
                    f.cancel()
                break
    _current_executor = None

# 停止扫描时
def stop_scan():
    global _current_executor
    with _executor_lock:
        if _current_executor:
            _current_executor.shutdown(wait=False, cancel_futures=True)
            _current_executor = None
```

## 关键点

1. **全局引用** — executor必须保存在模块级变量中，不能只在函数内部
2. **锁保护** — 用 `_executor_lock` 保护executor引用的读写
3. **shutdown参数**：
   - `wait=False` — 不等待正在运行的任务完成
   - `cancel_futures=True` — 取消队列中未执行的任务（Python 3.9+）
4. **清理引用** — shutdown后必须将executor设为None

## 注意事项

- `cancel_futures=True` 需要 Python 3.9+
- 正在执行的任务无法被强制终止，只能等待其完成或超时
- 如果任务内部有阻塞操作（如网络请求），需要设置合理的timeout
