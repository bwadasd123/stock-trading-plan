# GitHub项目：aiagents-stock

## 项目信息
- **仓库**: https://github.com/oficcejo/aiagents-stock
- **Stars**: 1,539 ⭐
- **功能**: 复合多AI智能体股票分析系统

## 核心功能

### 1. 交易策略（12种）
- 均线系统（金叉/死叉）
- MACD策略
- KDJ策略
- 布林带
- 量价分析
- 趋势跟踪
- AI模型驱动（Transformer深度学习）

### 2. 仓位管理
- 动态仓位调整
- 最大持仓限制
- 分散投资策略
- 止损止盈设置

### 3. 买卖点判断
- 自动生成买入/卖出信号
- 图表标记
- 企业微信/钉钉推送

### 4. 其他功能
- 策略回测系统
- 实时监控
- Streamlit可视化界面
- 游资龙虎榜跟踪
- 板块预警轮动分析
- 新闻流量监测

## 与现有系统的结合

```
选股系统 → 选出股票 → aiagents-stock分析 → 给出买卖建议
     ↓
  科安达(002972) → AI分析 → "建议买入，仓位20%，止盈+15%，止损-8%"
```

## 部署信息（2026-06-23 已部署）

### 安装路径
```
/home/jmy/aiagents-stock
```

### API配置
项目支持任何OpenAI兼容API，已配置使用小米mimo：
```env
DEEPSEEK_API_KEY=<从Hermes环境读取>
DEEPSEEK_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
DEFAULT_MODEL_NAME=mimo-v2.5-pro
```

**⚠️ API密钥读取方式：**
用户说"从环境里读"时，去 `~/.hermes/profiles/eastmoney-bot/.env` 和 `config.yaml` 读取现有配置，不要问用户要：
```bash
# config.yaml 中找 base_url 和 model
cat ~/.hermes/profiles/eastmoney-bot/config.yaml | grep -A 5 "xiaomi\|mimo"

# .env 中找 API key
cat ~/.hermes/profiles/eastmoney-bot/.env | grep -i "api_key"
```

### 启动命令
```bash
cd /home/jmy/aiagents-stock
streamlit run app.py --server.port 8501 --server.headless true
```

### ⚠️ deepseek_client.py 修复（部署时必须）
mimo模型需要修改 `deepseek_client.py`：
```python
# 原代码只检查 "reasoner"
if "reasoner" in model_to_use.lower() and max_tokens <= 2000:

# 必须加入 "mimo"
if ("reasoner" in model_to_use.lower() or "mimo" in model_to_use.lower()) and max_tokens <= 2000:
```

详见 `references/mimo-api-config.md`

### 访问地址
http://localhost:8501

### 已知问题
- **ProxyError**: 系统使用代理（172.25.176.1:2080），部分外部API（如东方财富push2his、同花顺basic.10jqka.com.cn）会被代理拦截。Akshare会自动重试3次后降级。
- **Streamlit warnings**: `use_container_width` 已弃用警告，不影响功能。
- **代理相关数据获取失败**: 资金流向、换手率等依赖东方财富API的数据可能获取失败，但核心分析功能不受影响。

### 依赖安装
```bash
cd /home/jmy/aiagents-stock
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### .env 完整配置模板
```env
# API配置（使用小米mimo替代DeepSeek）
DEEPSEEK_API_KEY=<key>
DEEPSEEK_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
DEFAULT_MODEL_NAME=mimo-v2.5-pro

# 时区
TZ=Asia/Shanghai

# 可选：Tushare
TUSHARE_TOKEN=

# 可选：MiniQMT量化交易
MINIQMT_ENABLED=false

# 可选：TDX数据源
TDX_BASE_URL=http://127.0.0.1:5000

# 监控配置
LOW_PRICE_BULL_SCAN_INTERVAL=60
LOW_PRICE_BULL_HOLDING_DAYS=5
```

## 持仓导入

系统自带示例股票，必须先清理再导入用户持仓：

```python
from portfolio_manager import PortfolioManager

pm = PortfolioManager()

# 1. 先清理所有非持仓股票
stocks = pm.get_all_stocks()
for stock in stocks:
    if stock['code'] != '002972':  # 保留用户持仓
        pm.delete_stock(stock['id'])

# 2. 添加用户持仓
pm.add_stock(
    code='002972',
    name='科安达',
    cost_price=16.443,
    quantity=400,
    note='扫描发现价15.80，止盈+15%，止损-8%',
    auto_monitor=True
)
```

**⚠️ 用户明确要求：只保留他的持仓，其他股票必须删除！**

## 部署Pitfalls

### SOCKS代理依赖
如果系统使用SOCKS代理，必须安装 `pysocks`：
```bash
pip3 install pysocks
```
否则所有HTTP请求会报 `Missing dependencies for SOCKS support`。

### 代理导致数据获取失败
部分外部API（东方财富push2his、同花顺basic.10jqka.com.cn）会被代理拦截。
Akshare会自动重试3次后降级到备用数据源。核心分析功能不受影响。

### 启动前清除代理环境变量
```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
streamlit run app.py --server.port 8501 --server.headless true
```

## 适用场景
- 3万本金小资金短线交易
- 需要AI辅助分析买卖点
- 需要仓位管理建议
- 需要实时盯盘预警
