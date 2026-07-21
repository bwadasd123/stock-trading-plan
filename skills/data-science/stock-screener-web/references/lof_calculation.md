# LOF套利高级计算模式

## 概述
参考 lof.i668.vip 实现，基于**底层资产实时价格**计算估算净值，而非依赖天天基金API。

## 架构设计
```
services/fund_holdings.py   # 基金持仓映射配置
services/asset_prices.py    # 底层资产实时价格获取
services/nav_calculator.py  # 估算净值计算引擎
api/arbitrage.py            # API端点（含详情接口）
```

## 计算公式
```
持仓收益 = Σ(持仓权重 × 底层资产涨跌幅)
期货收益 = 美股持仓权重 × 期货涨跌幅
总收益 = 持仓收益 + 期货收益
估算净值 = 基准净值 × (1 + 总收益%)
溢价率 = (场内价格 - 估算净值) / 估算净值 × 100%
```

## 持仓映射配置 (fund_holdings.py)
```python
FUND_HOLDINGS = {
    "513100": {
        "name": "纳指ETF",
        "benchmark": "纳斯达克100指数",
        "holdings": [
            {"ticker": "QQQ", "name": "Invesco QQQ Trust", "weight": 0.98, "market": "US"},
        ],
        "cash_weight": 0.02,
        "calc_method": "纳指ETF收盘涨跌 + 纳指期货盘后变动",
        "futures_ticker": "NQ",  # 关联期货代码
        "is_etf": True,
    },
    "164701": {
        "name": "汇添富黄金及贵金属LOF",
        "holdings": [
            {"ticker": "GLD", "name": "SPDR Gold Trust", "weight": 0.49, "market": "US"},
            {"ticker": "IAU", "name": "iShares Gold Trust", "weight": 0.48, "market": "US"},
        ],
        "futures_ticker": "GC",  # COMEX黄金期货
    },
}
```

## 东财美股/期货API secid格式
```python
# 美股ETF/股票
secid = f"105.{ticker}"  # 105.QQQ, 105.SPY, 105.GLD

# 港股
secid = f"116.{code}"  # 116.2800, 116.3032

# 期货
futures_map = {
    "GC": "101.GC00Y",  # COMEX黄金
    "SI": "101.SI00Y",  # COMEX白银
    "CL": "101.CL00Y",  # WTI原油
    "ES": "101.ES00Y",  # 标普500期货
    "NQ": "101.NQ00Y",  # 纳指期货
}
```

## ⚠️ 关键Pitfall：change_pct已经是百分比
东财API返回的 `change_pct`（f3字段）**已经是百分比**（如 -0.48 表示 -0.48%），计算贡献时**不要再除以100**：

```python
# ✅ 正确
contribution = weight * change_pct  # 0.98 × (-0.48) = -0.47%

# ❌ 错误（会导致数值缩小100倍）
contribution = weight * change_pct / 100  # 0.98 × (-0.48) / 100 = -0.0047%
```

**2026-06-05 教训**：初始实现错误地除以100，导致持仓收益显示为 -0.0047% 而非正确的 -0.47%。

## 详情API端点
```
GET /api/arbitrage/detail/<code>
```

返回完整计算过程：
```json
{
  "code": "513100",
  "name": "纳指ETF",
  "price": 2.205,
  "estimated_nav": 2.0807,
  "base_nav": 2.0808,
  "premium_rate": 5.97,
  "total_return": -0.47,
  "holdings_return": -0.47,
  "futures_return": 0,
  "calc_details": [
    {
      "ticker": "QQQ",
      "name": "Invesco QQQ Trust",
      "weight": 0.98,
      "change_pct": -0.48,
      "contribution": -0.47,
      "price": 740.61,
      "prev_close": 744.19,
      "market": "US"
    }
  ],
  "futures_detail": {
    "ticker": "NQ",
    "price": 21234.5,
    "change_pct": -0.3,
    "us_weight": 0.98,
    "weighted_contribution": -0.29
  },
  "method": "纳指ETF收盘涨跌 + 纳指期货盘后变动",
  "cash_weight": 0.02
}
```

## 前端展示
- 卡片上显示 `📊 详细计算` 徽章（有持仓配置的基金）
- 点击弹窗展示：
  - 溢价率大字
  - 场内价格/估算净值/基准净值 三列对比
  - 持仓明细表格（代码、名称、权重、涨跌幅、贡献）
  - 期货盘后变动详情
  - 完整计算公式

## 代理策略（重要）
- **美股/期货价格**：必须用 `safe_get` 走代理池（push2.eastmoney.com WSL直连502）
- **天天基金净值**：可用 `_try_request`（代理优先→直连兜底）
- **重试机制**：代理不稳定，需要3次重试 + 0.5秒间隔
```python
for attempt in range(3):
    try:
        resp = safe_get(url, headers=headers, params=params, timeout=10)
        if resp and resp.status_code == 200:
            # 处理数据
            break
    except Exception as e:
        logger.debug(f"失败 (尝试 {attempt+1}): {e}")
        time.sleep(0.5)
```
