# lof.i668.vip 参考分析

## 概述
lof.i668.vip 是一个LOF实时溢价监控网站，采用**自计算净值**的方式，比我们的天天基金API方案更精确。

## API端点
```
GET /api/premium/{fund_code}
```

## 数据结构（以164701汇添富黄金LOF为例）
```json
{
  "fund_code": "164701",
  "fund_name": "汇添富黄金及贵金属LOF",
  "market_price": 1.736,           // 场内价格
  "estimated_nav": 1.7416,         // 估算净值（自己算的）
  "premium_rate": -0.32,           // 溢价率
  "base_nav": 1.748,               // 基准净值（昨结算）
  "holdings_date": "2025年报",      // 持仓来源
  "cash_weight": 0.03,             // 现金占比
  "fee_rate": "0.80%",             // 申购费率
  "purchase_limit": "500.00元",    // 申购限额
  "purchase_status": "限额大",     // 申购状态
  "refresh_interval": 300,         // 刷新间隔（秒）
  "turnover_wan": 2146.0,          // 成交额（万）
  
  "calculation": {
    "method": "黄金ETF收盘涨跌（加权）+ COMEX黄金期货盘后变动",
    
    "etf_details": [                 // 底层持仓明细
      {
        "ticker": "GLD",
        "name": "SPDR Gold Trust",
        "market": "US",
        "weight": 0.49,              // 持仓权重
        "price": 411.27,             // 当前价格
        "prev_close": 407.87,        // 昨收
        "change_pct": -0.17,         // 涨跌幅
        "contribution": -0.00081     // 对净值的贡献
      },
      {
        "ticker": "IAU",
        "name": "iShares Gold Trust",
        "market": "US",
        "weight": 0.48,
        "price": 84.28,
        "prev_close": 83.59,
        "change_pct": -0.17,
        "contribution": -0.00080
      }
    ],
    
    "nq_detail": {                   // 期货/指数盘后变动
      "futures_label": "GC期货",
      "nq_price": 4495.47,           // 期货现价
      "ndx_close": 4505.0,           // 昨结算
      "nq_vs_ndx_pct": -0.21,        // 变动百分比
      "us_weight": 0.97,             // 美股权重
      "weighted_contribution": -0.00205  // 加权贡献
    },
    
    "step1_holdings_return": -0.1605,  // 步骤1：持仓收益
    "step2_nq_extra": -0.2052,         // 步骤2：期货增量
    "total_return": -0.3657            // 总收益
  }
}
```

## 核心计算公式
```
估算净值 = 基准净值 × (1 + 持仓收益 + 期货盘后变动)
       = base_nav × (1 + step1 + step2)
溢价率 = (场内价格 - 估算净值) / 估算净值 × 100%
```

## 前端页面
- 卡片式布局（与我们的设计类似）
- 点击卡片进入详情页 `/fund/{code}`
- 详情页展示完整计算过程和持仓明细
- 交易时间每5分钟自动刷新

## 与我们的方案对比

| 维度 | lof.i668.vip | 我们的方案 |
|------|-------------|-----------|
| 净值来源 | 自己算（底层资产实时价格） | 天天基金API（延迟估算） |
| 持仓数据 | 年报/季报解析 | 无 |
| 计算方法 | 持仓加权 + 期货盘后变动 | 简单公式 |
| 透明度 | 完整计算过程可见 | 黑盒 |
| 适用范围 | 需要维护持仓数据 | 通用，任何基金都能用 |
| 数据精度 | 高（实时追踪底层资产） | 中（依赖第三方估算） |

## 升级方向
如果要做类似lof.i668.vip的方案，需要：
1. 解析基金年报/季报的持仓数据
2. 建立持仓数据库（定期更新）
3. 实时追踪底层资产价格（美股、港股、期货等）
4. 实现自定义计算公式（不同基金类型不同算法）
5. 盘后增量计算（期货、ETF盘后交易）

## 注意事项
- QDII基金持仓通常是海外市场资产，需要跨市场数据源
- 持仓数据有滞后性（年报/季报披露时间）
- 不同基金类型的计算方法不同（黄金类用金价、美股类用指数等）
