# ECharts Modal Overlay Pattern

Reusable pattern for displaying ECharts charts in a modal overlay on any page.

## When to Use
- History trend charts (板块资金流向历史)
- Comparison charts (个股对比)
- Any time-series visualization that doesn't need a full page

## Pattern

### 1. JS Function (add to the page's JS module)
```javascript
letchartInstance = null;

function showHistoryChart() {
  const modal = document.getElementById('modal-container');
  modal.innerHTML = `
    <div class="modal-overlay active" onclick="closeChart(event)">
      <div class="arb-modal" onclick="event.stopPropagation()" style="max-width:900px;">
        <div class="modal-header">
          <h2>📈 图表标题</h2>
          <button class="modal-close" onclick="closeChart()">&times;</button>
        </div>
        <div style="display:flex;gap:10px;margin-bottom:15px;">
          <select id="chart_days" class="select" onchange="loadChartData()">
            <option value="1">今天</option>
            <option value="3" selected>近3天</option>
            <option value="7">近7天</option>
          </select>
        </div>
        <div id="chart-container" style="width:100%;height:400px;"></div>
        <div id="chart-loading" style="text-align:center;padding:20px;color:var(--text-secondary);">加载中...</div>
      </div>
    </div>
  `;
  loadChartData();
}

function closeChart(event) {
  if (event && event.target !== event.currentTarget) return;
  const modal = document.getElementById('modal-container');
  modal.innerHTML = '';
  if (chartInstance) { chartInstance.dispose(); chartInstance = null; }
}
```

### 2. ECharts Init (inside loadChartData)
```javascript
chartInstance = echarts.init(container);
chartInstance.setOption({
  tooltip: { trigger: 'axis' },
  legend: { data: legends, type: 'scroll', bottom: 0, textStyle: { color: '#999' } },
  grid: { left: 60, right: 20, top: 30, bottom: 60 },
  xAxis: { type: 'category', data: times, axisLabel: { color: '#999' } },
  yAxis: { type: 'value', axisLabel: { color: '#999' } },
  series: seriesData,
});
window.addEventListener('resize', () => chartInstance?.resize());
```

### 3. Trigger Button (in index.html page controls)
```html
<button class="btn btn-secondary" onclick="showHistoryChart()" style="margin-left:8px">📈 历史趋势</button>
```

## CSS Classes Used
- `.modal-overlay` — Full-screen backdrop (from style.css)
- `.arb-modal` — Modal content box (from arbitrage styles)
- `.modal-header` — Header with title + close button
- `.modal-close` — Close button
- `.select` — Styled select dropdown

## Key Points
- Use `document.getElementById('modal-container')` for the modal host
- Always dispose ECharts instance on close to prevent memory leaks
- Use `event.stopPropagation()` on modal content to prevent close-on-click-inside
- Use CSS variables for colors to support dark/light themes
- Add `window.addEventListener('resize', ...)` for responsive charts
