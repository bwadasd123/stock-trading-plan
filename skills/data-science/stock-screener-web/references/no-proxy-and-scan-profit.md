# NO_PROXY问题 + 扫描盈利统计API

## ⚠️ 东财API必须绕过代理（2026-06-25教训）

**问题**：系统设置了`HTTP_PROXY`和`HTTPS_PROXY`环境变量，导致东财API请求走代理，超时或失败。

**症状**：`curl http://push2delay.eastmoney.com/...`超时，但手动测试正常。

**✅ 解决方案**：在调用东财API前设置`NO_PROXY=*`：

```python
import os

def get_current_price(ts_code):
    # 东财API是内网，不走代理
    old_no_proxy = os.environ.get('NO_PROXY', '')
    os.environ['NO_PROXY'] = '*'
    
    try:
        url = f"http://push2delay.eastmoney.com/api/qt/stock/get?secid={secid}&fltt=2&fields=f43,f170"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())['data']
            os.environ['NO_PROXY'] = old_no_proxy  # 恢复
            return {'price': data['f43'], 'change_pct': data['f170']}
    except Exception as e:
        os.environ['NO_PROXY'] = old_no_proxy  # 恢复
        return None
```

**⚠️ 必须在finally或except中恢复NO_PROXY**，否则会影响后续其他代理请求。

---

## 扫描盈利统计API（2026-06-25新增）

### API端点
`GET /api/scan/monthly-profit`

### 功能
计算本月扫描信号的表现：
- 每只股票从发现价到当前价的涨跌幅
- 胜率（盈利信号数/总信号数）
- 平均涨幅
- 计算逻辑说明

### 后端实现
文件：`api/scan_profit.py`

```python
# SQL查询（⚠️ 用单百分号，不是双百分号）
cursor.execute("""
    SELECT ts_code, stock_name, 
           MIN(latest_price) as first_price,
           MIN(scan_time) as first_time,
           COUNT(*) as signal_count,
           AVG(rsi14) as avg_rsi
    FROM stock_scan_results 
    WHERE scan_time >= DATE_FORMAT(NOW(), '%Y-%m-01')  # ← 单百分号！
    GROUP BY ts_code, stock_name
    ORDER BY first_time ASC
""")
```

### ⚠️ SQL百分号转义陷阱
- **pymysql中**：用单百分号 `%Y-%m-01`
- **Python f-string中**：用双百分号 `%%Y-%%m-01`
- **症状**：双百分号`%%Y-%%m-01`会被解释为字面量`%Y-%m-01`，返回所有历史数据

### 前端实现
文件：`static/js/scan_profit.js`

在今日看点页面添加统计卡片：
- 平均涨幅、信号数量、胜率、盈亏比
- 信号明细表格（股票名、发现价、当前价、涨幅、发现时间）
- 计算逻辑说明

### 注册步骤
1. `app.py`导入蓝图：`from api.scan_profit import scan_profit_bp`
2. `app.py`注册蓝图：`app.register_blueprint(scan_profit_bp)`
3. `index.html`添加JS：`<script src="/static/js/scan_profit.js"></script>`
4. `index.html`添加容器：`<div id="scan-profit-section"></div>`（在daily-content之前）

### 用户偏好
- 用户要求显示**系统扫描信号的表现**，不是个人手动交易
- 用户要求把**计算逻辑也放在页面上**
