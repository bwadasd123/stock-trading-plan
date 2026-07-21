# 实时日志流（SSE）实现模式

## 概述

使用 Server-Sent Events (SSE) 实现服务器到客户端的实时日志推送。

## 架构

```
[Python Logger] → [LogStreamHandler] → [Subscriber Queues] → [SSE Response] → [Browser EventSource]
```

## 后端实现 (api/log_stream.py)

### LogStreamHandler 类
```python
class LogStreamHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.subscribers = {}  # {client_id: queue.Queue}
        self.sub_lock = threading.Lock()  # ⚠️ 不能叫self.lock，会覆盖父类RLock导致死锁！
    
    def subscribe(self, client_id: str) -> queue.Queue:
        q = queue.Queue(maxsize=100)
        with self.sub_lock:
            self.subscribers[client_id] = q
        return q
    
    def unsubscribe(self, client_id: str):
        with self.sub_lock:
            if client_id in self.subscribers:
                del self.subscribers[client_id]
    
    def emit(self, record):
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "message": self.format(record),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno
        }
        # 添加到历史记录
        log_history.append(log_entry)
        # 发送到所有订阅者
        with self.sub_lock:
            for client_id, q in list(self.subscribers.items()):
                try:
                    q.put_nowait(log_entry)
                except queue.Full:
                    q.get_nowait()  # 移除旧日志
                    q.put_nowait(log_entry)
```

**⚠️ 死锁陷阱**：`logging.Handler` 基类的 `handle()` 会先 `acquire(self.lock)` 再调用 `emit()`。如果子类用 `self.lock = threading.Lock()` 覆盖了父类的 RLock，`emit()` 中再次获取同一把锁就会死锁。Flask 启动卡死、端口永远不监听。详见 `flask-startup-pitfalls.md`。

### SSE 端点
```python
@app.route('/api/log/stream')
def stream_logs():
    client_id = request.args.get('client_id', str(time.time()))
    level_filter = request.args.get('level', 'ALL').upper()
    q = log_handler.subscribe(client_id)
    
    def generate():
        yield f"data: {json.dumps({'type': 'connected', 'client_id': client_id})}\n\n"
        # 发送历史日志
        for log_entry in log_history[-50:]:
            yield f"data: {json.dumps(log_entry)}\n\n"
        # 实时推送
        while True:
            try:
                log_entry = q.get(timeout=30)
                yield f"data: {json.dumps(log_entry)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'})
```

### 注册到根日志器
```python
log_handler = LogStreamHandler()
log_handler.setFormatter(logging.Formatter('%(message)s'))
root_logger = logging.getLogger()
root_logger.addHandler(log_handler)
```

## 前端实现 (static/js/log_stream.js)

### EventSource 连接
```javascript
const eventSource = new EventSource('/api/log/stream?client_id=xxx&level=ALL');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'heartbeat') return;
    addLogToUI(data);
};
eventSource.onerror = () => {
    // 自动重连
    setTimeout(() => connect(), 3000);
};
```

### 功能
- **日志级别过滤**: 下拉菜单选择 ALL/INFO/WARNING/ERROR/DEBUG
- **自动滚动**: 可切换自动/手动滚动模式
- **导出日志**: 导出为 .txt 文件
- **清空日志**: 清空历史记录

## 样式 (static/css/log_stream.css)

- 深色主题（#1e1e1e 背景）
- 日志级别颜色编码：
  - INFO: 蓝色 (#4fc1ff)
  - WARNING: 黄色 (#cca700)
  - ERROR: 红色 (#f44747)
  - DEBUG: 灰色 (#888)
- 左边框颜色编码
- 悬停高亮

## 访问方式

- **页面**: `http://localhost:8080/logs`
- **SSE流**: `GET /api/log/stream?client_id=xxx&level=ALL`
- **历史**: `GET /api/log/history?limit=100&level=ALL`
- **清空**: `POST /api/log/clear`

## 注意事项

1. **队列满处理**: 旧日志自动移除，防止内存溢出
2. **客户端断开**: `GeneratorExit` 时自动取消订阅
3. **心跳机制**: 30秒无日志时发送心跳，保持连接
4. **自动重连**: 前端断开后3秒自动重连
5. **历史记录**: 保留最近1000条日志
6. **Nginx代理**: 需要设置 `X-Accel-Buffering: no` 禁用缓冲
