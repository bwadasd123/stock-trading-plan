# 扫描超时诊断

## 问题现象

扫描任务显示 `timeout` 状态，扫描0只股票。

## 诊断步骤

### 1. 检查任务状态
```sql
SELECT id, scan_id, status, start_time, end_time, 
       total_stocks, error_message
FROM scan_task_history 
ORDER BY id DESC 
LIMIT 10;
```

### 2. 检查代理池状态
```bash
curl -s http://localhost:8080/api/proxy_pool/stats | jq
```

### 3. 检查代理API
```bash
curl -s "http://api3.ydaili.cn/tools/BMeasureApi.ashx?action=BEAPI&secret=***&number=1&orderId=YOUR_ORDER_ID&format=txt&type=1&split=3"
```

### 4. 检查网络连接
```bash
curl -s -o /dev/null -w "%{http_code}" "http://push2delay.eastmoney.com/api/qt/clist/get?pn=1&pz=1"
```

## 常见原因

### 1. 代理池为空
**症状**：代理池stats显示pool_size=0
**原因**：代理API调用失败
**解决**：
- 检查代理API配置
- 验证网络连接
- 手动刷新代理池：`POST /api/proxy_pool/refresh`

### 2. 代理API返回错误
**症状**：代理API返回 `{"status":"207","info":"secret解密失败"}`
**原因**：代理配置错误
**解决**：
- 检查secret和orderId
- 联系代理服务商

### 3. 网络问题
**症状**：API请求超时
**原因**：网络不稳定
**解决**：
- 检查服务器网络
- 尝试直连测试

### 4. 任务卡住
**症状**：任务状态为running但无进度
**原因**：进程被kill或异常退出
**解决**：
- 等待30分钟自动清理
- 或手动清理：`UPDATE scan_task_history SET status='timeout' WHERE status='running' AND TIMESTAMPDIFF(MINUTE, created_at, NOW()) > 30`

### 5. 代理API失败阻塞Flask启动（2026-06-16发现）
**症状**：`python3 app.py` 进程存在，但 `curl localhost:8080` 返回 "Connection refused"
**原因**：`EnhancedProxyPool._fill_on_init()` 在启动时运行，代理API返回错误（如"secret解密失败"），初始化持续重试超时，Flask永远无法监听端口
**诊断**：
```bash
# 检查进程是否在运行
ps aux | grep "python3 app.py" | grep -v grep
# 检查端口是否在监听
ss -tlnp | grep 8080
# 检查日志是否有代理错误
cat /tmp/stock_screener.log | grep -i "代理API"
```
**解决**：
1. 修复代理API配置（secret/orderId）
2. 或临时将 `PROXY_POOL_TARGET_SIZE` 设为0跳过初始化
3. 或修改 `_fill_on_init()` 为非阻塞（设置较短超时）

## 解决方案

### 方案1：增强代理池
- 代理复用机制
- 代理健康检查
- 代理池监控
- 失败重试机制

### 方案2：优化扫描逻辑
- 减少K线请求次数
- 并发请求
- 优化代理策略

### 方案3：任务监控
- 心跳检测
- 超时自动清理
- 状态可视化

## 预防措施

1. **定期检查代理池**：每天扫描前检查代理池状态
2. **监控任务状态**：发现超时及时处理
3. **备份代理方案**：准备多个代理服务商
4. **网络监控**：确保服务器网络稳定

## 相关代码

### 超时任务清理
```python
def _cleanup_stale_tasks():
    """清理之前卡住的任务状态（超过30分钟的 running 状态改为 timeout）"""
    conn = get_db()
    if conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE scan_task_history 
                SET status = 'timeout', 
                    error_message = '任务超时自动标记',
                    end_time = NOW()
                WHERE status = 'running' 
                AND TIMESTAMPDIFF(MINUTE, created_at, NOW()) > 30
            """)
            conn.commit()
        conn.close()
```

### 代理池监控
```python
def _monitor_pool(self):
    """监控代理池状态"""
    while True:
        time.sleep(60)  # 每分钟检查一次
        with self.lock:
            pool_size = len(self.proxies)
            if pool_size < self.target_size:
                threading.Thread(target=self._refill_async, args=(1,), daemon=True).start()
```
