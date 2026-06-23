# 股票价格监控系统

基于A股智能筛选系统的实时价格监控，推送到企业微信群。

## 功能

- 🔔 开盘播报 9:30
- ⏰ 整点播报 每小时
- ⚡ 涨跌提醒 超1%
- 📋 挂单提醒 10:30
- 🎯 止盈触发 +15%
- 🚨 止损触发 -8%
- 📊 收盘总结 15:00

## 交易逻辑

**固定止盈止损为主，技术指标作为参考：**

| 项目 | 规则 | 说明 |
|------|------|------|
| 止盈 | +15% | 固定目标 |
| 止损 | -8% | 固定底线 |
| 持仓 | 3-5天 | 固定时间 |
| RSI | 参考 | 动态调整建议 |
| MA10/MA20 | 参考 | 支撑位参考 |

## 快速开始

### 1. 设置环境变量

```bash
# 企业微信Webhook（必填）
export WX_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key"

# 或者写入 ~/.bashrc
echo 'export WX_WEBHOOK="你的webhook地址"' >> ~/.bashrc
source ~/.bashrc
```

### 2. 修改配置

编辑 `scripts/price_monitor.py`，修改以下配置：

```python
# 股票配置
STOCK_CODE = "0.002972"    # 东财secid格式
STOCK_NAME = "科安达"
AVG_COST = 16.443          # 持仓均价
SHARES = 400               # 持仓数量
DB_TS_CODE = "002972"      # 数据库中的股票代码

# 止盈止损（固定）
TAKE_PROFIT_PCT = 15       # +15%
STOP_LOSS_PCT = 8          # -8%
HOLD_DAYS = "3-5天"
```

### 3. 部署定时任务

```bash
# 添加到crontab
crontab -e

# 每5分钟运行（交易时间）
*/5 9-15 * * 1-5 WX_WEBHOOK="你的key" cd /path/to/stock-trading-plan && python3 scripts/price_monitor.py >> /tmp/monitor.log 2>&1
```

### 4. 测试运行

```bash
# 手动测试
WX_WEBHOOK="你的key" python3 scripts/price_monitor.py
```

## 推送消息示例

```
📈 科安达 17.67 (+7.5%)
━━━━━━━━━━━━━━━━
💰 持仓：400股 | 市值：7068元
📊 盈亏：+490元
━━━━━━━━━━━━━━━━
🔺 今日：+2.20%
📏 振幅：3.76%
🔄 换手：7.94%
━━━━━━━━━━━━━━━━
🟢 外盘：55695手 (53%)
🔴 内盘：49242手 (47%)
📊 判断：买方强势 ✅
━━━━━━━━━━━━━━━━
🎯 止盈：18.91 (+15%)
🚨 止损：15.13 (-8%)
⏰ 持仓：3-5天
━━━━━━━━━━━━━━━━
📊 技术参考
   RSI14：70.1
   MA10：15.02
   MA20：13.61
```

## 目录结构

```
stock-trading-plan/
├── README.md              # 项目说明
├── skill/                 # 交易系统文档
│   ├── SKILL.md
│   ├── templates/
│   └── references/
├── positions/             # 持仓记录
├── history/               # 交易历史
├── scripts/               # 监控脚本
│   └── price_monitor.py
└── analysis/              # 收益分析
```

## 隐私说明

**本仓库为公开仓库，请勿提交以下敏感信息：**

- ❌ 企业微信Webhook Key
- ❌ 数据库密码
- ❌ API密钥
- ❌ 个人持仓详情（金额、成本等）

**正确做法：**
- Webhook Key 通过环境变量传入
- 数据库配置在 stock-screener 项目的 config.py 中（不提交）
- 持仓信息在本地 positions/ 目录（已加入 .gitignore）

## 相关项目

- [A股智能筛选系统](https://github.com/bwadasd123/stock-screener) - 选股扫描
- [交易系统Skill](skill/SKILL.md) - 完整交易策略

## 免责声明

本项目仅供学习参考，不构成投资建议。股市有风险，投资需谨慎。
