# 实时日志流功能

## 架构
- **后端**: SSE (Server-Sent Events) 实时推送
- **前端**: EventSource API 接收
- **日志处理**: 自定义 logging.Handler 推送到队列

## 文件清单
- `api/log_stream.py` - SSE日志流API
- `static/js/log_stream.js` - 前端日志组件(LogStream类)
- `static/css/log_stream.css` - 深色主题样式
- `templates/log_viewer.html` - 独立日志查看页面

## API端点
| 路由 | 方法 | 说明 |
|------|------|------|
| `/logs` | GET | 日志查看页面 |
| `/api/log/stream` | GET | SSE实时日志流 |
| `/api/log/history` | GET | 日志历史查询 |
| `/api/log/clear` | POST | 清空日志历史 |

## 使用方式
```javascript
// 前端初始化
const logStream = new LogStream('logContainer', {
    maxLogs: 500,
    autoScroll: true,
    levelFilter: 'ALL'
});
```

## SSE连接参数
- `client_id`: 客户端唯一标识
- `level`: 日志级别过滤 (ALL/INFO/WARNING/ERROR/DEBUG)
- 心跳间隔: 30秒

## 功能特性
- 实时日志推送
- 日志级别过滤
- 自动/手动滚动切换
- 导出日志为文本文件
- 最近1000条日志历史
- 自动重连(3秒)

## 注意事项
- 需要在app.py中注册蓝图: `app.register_blueprint(log_stream_bp)`
- 需要在index.html中添加入口链接
- SSE连接会保持长连接，Nginx需要配置 `X-Accel-Buffering: no`
