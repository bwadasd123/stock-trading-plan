# 扫描系统盈利统计（/report页面）

## 概述
在板块资金流向和历史信号之间，新增"📊 扫描系统本月战绩"区域，调用 `/api/scan/monthly-profit` API。

## 布局结构
```
📊 扫描系统本月战绩
├── 汇总卡片（4列grid）：本月信号数、胜率、平均涨幅、胜/负
├── 计算逻辑说明（可折叠，灰色小字）
└── 信号明细表：代码、名称、发现价、现价、涨幅、RSI、信号数、发现时间
```

## API
- 端点: `/api/scan/monthly-profit`
- 文件: `api/scan_profit.py`
- 返回: `{ success, summary: {total_signals, win_rate, avg_profit, winning_count, losing_count}, signals: [...], calc_logic }`

## HTML结构
```html
<div class="section-title">📊 扫描系统本月战绩</div>
<div class="profit-summary" id="profit-summary"></div>
<div style="padding: 0 20px 4px;">
  <div id="profit-calc-logic" style="..."></div>
</div>
<div id="profit-table-wrap"></div>
```

## CSS样式（暗色主题）
```css
.profit-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 6px 20px 10px; }
.profit-card { background: #0f172a; border-radius: 8px; padding: 12px; text-align: center; border: 1px solid #1e293b; }
.profit-card .label { font-size: 12px; color: #64748b; margin-bottom: 4px; }
.profit-card .value { font-size: 20px; font-weight: 700; }
.profit-card .value.green { color: #22c55e; }
.profit-card .value.red { color: #ef4444; }
.profit-card .value.blue { color: #60a5fa; }
.profit-card .value.yellow { color: #fbbf24; }

.profit-table { width: 100%; border-collapse: collapse; background: #0f172a; border-radius: 8px; overflow: hidden; margin: 0 20px 14px; max-width: calc(100% - 40px); }
.profit-table th { background: #1e293b; padding: 10px 8px; font-size: 12px; color: #64748b; font-weight: 600; text-align: center; }
.profit-table td { padding: 10px 8px; font-size: 13px; border-bottom: 1px solid #1e293b; text-align: center; }
.profit-table .code { color: #60a5fa; font-weight: 600; font-family: 'SF Mono', 'Consolas', monospace; }
.profit-table .name { color: #e1e5eb; font-weight: 500; }
.profit-table .price { color: #a78bfa; font-weight: 600; }
.profit-table .rsi { color: #fbbf24; font-size: 12px; }
```

## 亮色主题覆盖（必须！）
```css
body.light .profit-card { background: #ffffff; border-color: #e2e8f0; }
body.light .profit-card .label { color: #64748b; }
body.light .profit-table { background: #ffffff; }
body.light .profit-table th { background: #f1f5f9; color: #475569; }
body.light .profit-table td { border-color: #e2e8f0; color: #334155; }
body.light .profit-table .name { color: #1e293b; }
body.light .profit-table .code { color: #3b82f6; }
body.light #profit-calc-logic { background: #f8fafc !important; border-color: #e2e8f0 !important; color: #475569 !important; }
```

## JS实现
在 `loadReport()` 成功回调末尾调用 `loadProfitStats()`，独立try/catch，失败不影响主报表。

```javascript
async function loadProfitStats() {
  try {
    const resp = await fetch('/api/scan/monthly-profit');
    const data = await resp.json();
    if (!data.success) return;
    
    const s = data.summary;
    // 汇总卡片
    document.getElementById('profit-summary').innerHTML = `
      <div class="profit-card"><div class="label">本月信号</div><div class="value blue">${s.total_signals}只</div></div>
      <div class="profit-card"><div class="label">胜率</div><div class="value ${s.win_rate >= 50 ? 'green' : 'red'}">${s.win_rate}%</div></div>
      <div class="profit-card"><div class="label">平均涨幅</div><div class="value ${s.avg_profit >= 0 ? 'green' : 'red'}">${s.avg_profit >= 0 ? '+' : ''}${s.avg_profit}%</div></div>
      <div class="profit-card"><div class="label">盈利/亏损</div><div class="value ${s.winning_count >= s.losing_count ? 'green' : 'red'}">${s.winning_count}胜${s.losing_count}负</div></div>
    `;
    
    // 计算逻辑（可选显示）
    if (data.calc_logic) {
      const calcEl = document.getElementById('profit-calc-logic');
      calcEl.style.display = 'block';
      calcEl.innerHTML = data.calc_logic.replace(/\n/g, '<br>');
    }
    
    // 信号明细表
    if (data.signals && data.signals.length) {
      document.getElementById('profit-table-wrap').innerHTML = `
        <div style="padding: 0 20px 14px; overflow-x: auto;">
          <table class="profit-table">
            <tr><th>代码</th><th>名称</th><th>发现价</th><th>现价</th><th>涨幅</th><th>RSI</th><th>信号数</th><th>发现时间</th></tr>
            ${data.signals.map(s => {
              const cls = s.profit_pct >= 0 ? 'up' : 'down';
              const sign = s.profit_pct >= 0 ? '+' : '';
              return `<tr>
                <td class="code">${s.ts_code}</td>
                <td class="name">${s.stock_name}</td>
                <td class="price">${parseFloat(s.first_price).toFixed(2)}</td>
                <td class="price">${parseFloat(s.current_price).toFixed(2)}</td>
                <td class="${cls}" style="font-weight:700;">${sign}${s.profit_pct}%</td>
                <td class="rsi">${s.avg_rsi || '-'}</td>
                <td>${s.signal_count}</td>
                <td style="color:#94a3b8;font-size:12px;">${s.first_time}</td>
              </tr>`;
            }).join('')}
          </table>
        </div>
      `;
    }
  } catch(e) {
    console.error('加载盈利统计失败:', e);
  }
}
```

## ⚠️ 注意事项
1. 盈利统计独立加载，失败不影响大盘指数、板块、信号的显示
2. 计算逻辑区域默认隐藏，有数据时才显示
3. 涨幅列用 `.up`/`.down` 类着色（红涨绿跌，与主表一致）
4. RSI列为空时显示 `-`
5. **亮色主题必须覆盖所有新元素** — 包括 `.profit-card`、`.profit-table`、`#profit-calc-logic` 等。用户会点右上角切换主题检查，漏掉任何一个都会被发现。
