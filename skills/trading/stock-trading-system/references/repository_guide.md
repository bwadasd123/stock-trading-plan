# 📈 3万本金股票交易计划

基于A股智能筛选系统的实战交易记录与操作计划。

## 项目结构

```
stock-trading-plan/
├── README.md              # 项目说明
├── positions/             # 持仓记录
│   └── current.json       # 当前持仓
├── history/               # 历史交易
│   └── trades.json        # 交易记录
├── scripts/               # 监控脚本
│   └── price_monitor.py   # 价格监控
└── analysis/              # 分析报告
    └── performance.md     # 收益统计
```

## 使用方法

### 1. 克隆仓库
```bash
git clone https://github.com/bwadasd123/stock-trading-plan.git
cd stock-trading-plan
```

### 2. 配置监控脚本
编辑 `scripts/price_monitor.py`，修改：
- `WX_WEBHOOK`: 你的企业微信Webhook
- `STOCK_CODE`: 股票代码（东财secid格式）
- `STOCK_NAME`: 股票名称
- `AVG_COST`: 持仓均价
- `SHARES`: 持仓数量
- `TAKE_PROFIT`: 止盈价
- `STOP_LOSS`: 止损价

### 3. 部署定时任务
```bash
# 添加到crontab，每5分钟运行
crontab -e
*/5 9-15 * * 1-5 cd /path/to/stock-trading-plan && python3 scripts/price_monitor.py
```

### 4. 更新持仓
每次交易后更新 `positions/current.json` 和 `history/trades.json`

### 5. 提交记录
```bash
git add .
git commit -m "交易：买入科安达 400股 16.443"
git push
```

## 文件说明

### positions/current.json
当前持仓记录，包含股票代码、数量、均价、止盈止损价等。

### history/trades.json
所有交易历史，用于复盘分析和收益统计。

### analysis/performance.md
收益统计和交易复盘，记录经验教训。

### scripts/price_monitor.py
价格监控脚本，推送到企业微信群。

## 注意事项

1. 每次交易后及时更新记录
2. 定期复盘总结经验教训
3. 严格执行止盈止损纪律
4. 不要贪心，按计划操作

---

*本项目仅供学习参考，不构成投资建议。*
