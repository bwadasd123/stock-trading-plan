# 📈 3万本金股票交易系统

基于A股智能筛选系统的实战交易策略，包含完整交易流程、价格监控、记录复盘。

## 📂 仓库结构

```
stock-trading-plan/
├── README.md              # 项目说明
├── skill/                 # ⭐ 交易系统Skill（别人学习用）
│   ├── SKILL.md           # 完整交易文档
│   ├── templates/         # 可直接使用的模板
│   └── references/        # 参考文档
├── positions/             # 当前持仓
├── history/               # 交易历史
├── scripts/               # 监控脚本
└── analysis/              # 收益分析
```

## ⭐ Skill（核心）

**完整交易系统文档**，别人加载后可直接使用：

```
skill/
├── SKILL.md                      # 主文档：完整交易流程
├── templates/
│   ├── price_monitor.py          # 价格监控脚本（改配置即用）
│   ├── current_position.json     # 持仓记录模板
│   └── trades_history.json       # 交易历史模板
└── references/
    ├── quick_reference.md        # 快速参考卡（一页纸）
    └── repository_guide.md       # 仓库使用指南
```

**使用方法**：
1. 阅读 `skill/SKILL.md` 了解完整策略
2. 复制 `skill/templates/` 下的模板文件
3. 修改配置参数（股票代码、webhook等）
4. 按流程执行交易

## 📊 核心参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 本金 | 30,000元 | 固定不动 |
| 单股仓位 | 6,000元 (20%) | 最大投入 |
| 买入方式 | 分两笔，各3,000元 | 降低风险 |
| 止损线 | -8% | 必须执行 |
| 止盈目标 | +15% | 分批止盈 |
| 持仓时间 | 3-5天 | 超时减仓 |

## 🎯 当前持仓

| 股票 | 代码 | 数量 | 均价 | 止盈价 | 止损价 | 买入日 |
|------|------|------|------|--------|--------|--------|
| 科安达 | 002972 | 400股 | 16.443 | 18.91 | 15.13 | 2026-06-17 |

## 📱 价格监控

自动推送到企业微信群：
- 🔔 开盘播报 9:30
- ⏰ 整点播报 每小时
- ⚡ 涨跌提醒 超2%
- 🎯 止盈止损 触发推送
- 📊 收盘总结 15:00

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/bwadasd123/stock-trading-plan.git
cd stock-trading-plan

# 2. 阅读完整文档
cat skill/SKILL.md

# 3. 配置监控脚本
cp skill/templates/price_monitor.py scripts/
# 编辑 scripts/price_monitor.py 修改配置

# 4. 部署定时任务
crontab -e
# 添加: */5 9-15 * * 1-5 cd /path/to/stock-trading-plan && python3 scripts/price_monitor.py
```

## 📚 完整文档

详见 [skill/SKILL.md](skill/SKILL.md)，包含：
- 完整交易流程（扫描→分析→买入→持仓→监控→复盘）
- RSI持仓策略对照表
- 风险控制规则
- 实战教训总结
- 工具使用说明

## ⚠️ 风险提示

本策略基于历史数据回测，不构成投资建议。股市有风险，投资需谨慎。

---

**JMY科技有限公司** | 东财数据部
