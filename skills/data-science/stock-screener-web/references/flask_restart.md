# Flask 重启规范

## 核心规则

**⚠️ 修改任何 .py 或 .html 文件后必须立即重启 Flask！**

用户已多次提醒忘记重启。这是最高优先级的操作规范。

## 重启命令（推荐流程）

```bash
# 1. 按端口杀旧进程（比 pkill 更可靠）
kill $(lsof -ti:8080) 2>/dev/null; sleep 2

# 2. 确认端口已释放
ss -tlnp | grep 8080 || echo "Port 8080 is free"

# 3. 后台启动（用 background=true，不要加 shell &）
cd /home/jmy/stock-screener && /home/jmy/.hermes/hermes-agent/venv/bin/python app.py
```

**⚠️ 必须用 hermes-agent venv python**，uv Python 3.11 缺少 flask 等依赖。

### 备选启动方式

```bash
# 用 nohup 确保后台运行
cd /home/jmy/stock-screener && nohup /home/jmy/.hermes/hermes-agent/venv/bin/python app.py > /tmp/flask.log 2>&1 &
sleep 3 && ss -tlnp | grep 8080
```

## 验证重启成功

```bash
# 最可靠的方式：检查端口监听
ss -tlnp | grep 8080 && echo "✅ Flask running on 8080" || echo "❌ Port 8080 not listening"

# 可选：检查HTTP响应
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
```

## 需要重启的文件类型

- `*.py` - 所有Python文件（api/, services/, models/, app.py）
- `*.html` - 所有模板文件（templates/）
- `*.js` - 不需要重启（静态文件直接刷新浏览器）

## 常见错误

1. 改完代码直接告诉用户"已完成"但没重启
2. 用 foreground 模式启动（应该用 background=true）
3. 忘记 cd 到正确目录
4. **`pkill -f 'python.*app.py'` 不可靠** — 用 `kill $(lsof -ti:8080)` 按端口杀进程
5. **shell `&` 后台启动会立即退出** — 必须用 terminal 工具的 `background=true` 参数
6. **进程日志为空不代表失败** — 用 `ss -tlnp | grep 8080` 验证端口监听
