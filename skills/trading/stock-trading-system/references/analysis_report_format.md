# AI分析报告格式示例

## 输出格式（用户偏好）

```
✅ 科安达(002972) AI分析报告完成！

---
📊 基本信息：
- 股票名称：科安达
- 当前价格：17.23元
- 涨跌幅：-0.35%

---
🔍 AI技术分析摘要：

趋势分析：
- ✅ 均线多头排列
- ✅ 短期和中期上涨动能强劲

超买超卖：
- ⚠️ RSI: 82.76 - 极度超买！
- ⚠️ KDJ: K=90.5, D=93.15 - 高位死叉雏形

---
🎯 关键技术位：
| 类型 | 价格 | 说明 |
|------|------|------|
| 阻力位 | 17.44 | 布林带上轨 |
| 支撑位 | 16.72 | MA5均线 |

---
📋 AI建议：
持仓者：将MA5（16.72）作为保护性止盈/止损线
持币者：当前追高风险极大，等待回调

---
⚠️ 风险提示：
1. RSI 82.76极度超买
2. 缩量上涨，量价背离

---
你的持仓情况：
- 持仓400股，成本价16.443元
- 当前盈利：+4.8%
- 建议：关注16.72支撑位，跌破则减仓
```

## 格式要求

1. **用emoji和分隔线** — 清晰分区
2. **关键数据用表格** — 技术位、指标值
3. **建议要具体** — 价格、数量、时间节点
4. **结合用户持仓** — 不是通用建议，是针对他的持仓
5. **风险提示要突出** — ⚠️标记

## 代码模板

```python
cd /home/jmy/aiagents-stock && python3 << 'EOF'
import os
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

from deepseek_client import DeepSeekClient
from stock_data import StockDataFetcher

stock_data_obj = StockDataFetcher()
stock_info = stock_data_obj.get_stock_info('002972')
stock_data = stock_data_obj.get_stock_data('002972', period='1y')
stock_data = stock_data_obj.calculate_technical_indicators(stock_data)
indicators = stock_data_obj.get_latest_indicators(stock_data)

client = DeepSeekClient()
result = client.technical_analysis(stock_info, stock_data, indicators)
print(result)
EOF
```

## 注意事项
- 必须unset代理环境变量（http_proxy等）
- mimo模型需要max_tokens=8000
- Akshare获取数据可能需要重试
