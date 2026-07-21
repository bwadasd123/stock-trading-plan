# Frontend Page Addition Pattern (Post-Refactor)

## Architecture Overview

The UI uses **browser-style tab navigation** with a sidebar for navigation and a tab bar at the top of the content area. Each page is a `<div id="page-xxx">` that gets shown/hidden when tabs are switched.

## Browser-Style Tab System (Main Navigation)

### How It Works

- Left sidebar menu items open tabs in the right content area
- Tab bar at top shows open tabs with refresh (🔄) and close (×) buttons
- Tabs persist until explicitly closed
- Last tab cannot be closed
- Data is cached in memory for quick switching

### Tab Configuration in `app.js`

```javascript
const TAB_CONFIG = {
  daily: { icon: '📰', title: '今日看点', refreshable: true },
  scanner: { icon: '🔍', title: '市场扫描', refreshable: true },
  sector: { icon: '💰', title: '板块资金流向', refreshable: true },
  dragon: { icon: '🐉', title: '龙虎榜', refreshable: true },
  watchlist: { icon: '⭐', title: '自选股监控', refreshable: true },
  arbitrage: { icon: '💹', title: 'LOF套利', refreshable: true },
  history: { icon: '📜', title: '历史信号', refreshable: true },
  hot: { icon: '🔥', title: '热门信号', refreshable: true },
  tasks: { icon: '📋', title: '任务历史', refreshable: true },
  detail: { icon: '📈', title: '个股详情', refreshable: false },
  settings: { icon: '⚙️', title: '系统设置', refreshable: false }
};
```

### Key Functions

```javascript
let openTabs = [];      // Array of open tab IDs
let activeTab = 'scanner';  // Currently active tab

function openTab(tabId) {
  // Add tab if not exists, then switch to it
  if (!openTabs.includes(tabId)) {
    openTabs.push(tabId);
    renderTabs();
  }
  switchToTab(tabId);
}

function closeTab(tabId, event) {
  if (event) event.stopPropagation();
  if (openTabs.length <= 1) return;  // Can't close last tab
  
  openTabs = openTabs.filter(t => t !== tabId);
  if (activeTab === tabId) {
    const index = openTabs.indexOf(tabId);
    switchToTab(openTabs[Math.min(index, openTabs.length - 1)]);
  }
  renderTabs();
}

function refreshTab(tabId, event) {
  if (event) event.stopPropagation();
  // Clear cache for this tab
  if (tabId === 'sector') sectorData = {};
  loadTabData(tabId);
}

function switchToTab(tabId) {
  activeTab = tabId;
  // Update tab bar highlighting
  document.querySelectorAll('.tab-item').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.tab === tabId);
  });
  // Update page visibility
  document.querySelectorAll('.page').forEach(p => {
    p.classList.toggle('active', p.id === 'page-' + tabId);
  });
  // Update sidebar highlighting
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.page === tabId);
  });
  loadTabData(tabId);
}

function renderTabs() {
  const tabContainer = document.getElementById('tab-bar');
  let html = '';
  openTabs.forEach(tabId => {
    const config = TAB_CONFIG[tabId];
    const isActive = tabId === activeTab;
    html += `
      <div class="tab-item ${isActive ? 'active' : ''}" data-tab="${tabId}" onclick="switchToTab('${tabId}')">
        <span class="tab-icon">${config.icon}</span>
        <span class="tab-title">${config.title}</span>
        ${config.refreshable ? `<button class="tab-btn tab-refresh" onclick="refreshTab('${tabId}', event)" title="刷新">🔄</button>` : ''}
        <button class="tab-btn tab-close" onclick="closeTab('${tabId}', event)" title="关闭">×</button>
      </div>
    `;
  });
  tabContainer.innerHTML = html;
}
```

### HTML Structure

```html
<main class="content">
  <!-- Tab bar -->
  <div class="tab-bar" id="tab-bar"></div>
  
  <!-- Page content -->
  <div class="page-container">
    <div id="page-scanner" class="page">...</div>
    <div id="page-sector" class="page">...</div>
    <!-- etc -->
  </div>
</main>
```

### CSS for Tab Bar

```css
.tab-bar {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  min-height: 40px;
  overflow-x: auto;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
  min-width: 120px;
}

.tab-item.active {
  background: var(--bg-primary);
  border-color: var(--accent-blue);
  border-bottom: 2px solid var(--bg-primary);
}

.tab-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 2px 4px;
  margin-left: 4px;
}

.tab-close:hover {
  color: var(--accent-red);
}
```

## Adding a New Page

### Step 1: Add Nav Item in `templates/index.html` (sidebar section)

```html
<a href="#" class="nav-item" data-page="your_page">
  <span class="nav-icon">🎯</span>
  <span class="nav-text">Your Page Name</span>
</a>
```

### Step 2: Add Page Content Div

```html
<div id="page-your_page" class="page">
  <div class="page-controls">
    <select id="your_filter" class="select">
      <option value="7">近7天</option>
      <option value="30" selected>近30天</option>
    </select>
    <button class="btn btn-primary" onclick="loadYourData()">🔄 刷新</button>
  </div>
  <div id="your_page-result"></div>
</div>
```

### Step 3: Update `TAB_CONFIG` in `static/js/app.js`

```javascript
const TAB_CONFIG = {
  // ... existing tabs ...
  your_page: { icon: '🎯', title: 'Your Page Title', refreshable: true }
};
```

### Step 4: Update `loadTabData()` in `static/js/app.js`

```javascript
function loadTabData(tabId) {
  switch(tabId) {
    // ... existing cases ...
    case 'your_page':
      loadYourData();
      break;
  }
}
```

### Step 5: Add JS Function

```javascript
async function loadYourData() {
  const filter = document.getElementById('your_filter').value;
  try {
    const r = await fetch('/api/your_endpoint?days=' + filter);
    const d = await r.json();
    
    if (!d.results || !d.results.length) {
      document.getElementById('your_page-result').innerHTML = '<div class="empty-state">暂无数据</div>';
      return;
    }
    
    let h = '<table><tr><th>Col1</th><th>Col2</th></tr>';
    for (const item of d.results) {
      h += `<tr><td>${item.field1}</td><td>${item.field2}</td></tr>`;
    }
    h += '</table>';
    document.getElementById('your_page-result').innerHTML = h;
  } catch(e) {
    document.getElementById('your_page-result').innerHTML = '<div class="empty-state">加载失败</div>';
  }
}
```

## Inline Sub-Tabs (Within a Page)

For switching between related data views within a page (e.g., Industry vs Concept sectors), use inline tabs:

```html
<div class="tab-group">
  <button class="tab active sector-tab" data-type="industry" onclick="switchSectorType('industry')">🏭 行业板块</button>
  <button class="tab sector-tab" data-type="concept" onclick="switchSectorType('concept')">💡 概念板块</button>
</div>
<div id="sector-content"></div>
```

```javascript
let currentSectorType = 'industry';
let sectorData = {};  // Cache for quick switching

function switchSectorType(type) {
  currentSectorType = type;
  document.querySelectorAll('.sector-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.type === type);
  });
  if (sectorData[type]) {
    renderSectorData(sectorData[type]);
  } else {
    loadSectorFlow();
  }
}
```

## Modal Pattern

Use the `showModal(html)` / `closeModal()` functions:

```javascript
async function viewDetail(id) {
  const r = await fetch('/api/detail/' + id);
  const d = await r.json();
  
  let html = '<div class="modal-header">';
  html += '<h3>📋 Detail Title</h3>';
  html += '<button class="modal-close" onclick="closeModal()">&times;</button></div>';
  html += '<div class="metrics">';
  html += '<div class="metric"><div class="val">' + d.value + '</div><div class="lbl">Label</div></div>';
  html += '</div>';
  
  showModal(html);
}
```

## Clickable Elements Pattern

When making elements clickable (like stock names), use `javascript:void(0)` and `event.stopPropagation()`:

```javascript
const leadStockHtml = s.lead_stock ? 
  `<a href="javascript:void(0)" onclick="event.stopPropagation();analyzeStock('${s.lead_stock}')" class="lead-stock-link">${s.lead_stock_name} (${s.lead_stock})</a>` : 
  '-';
```

Always show both name AND code for stocks: `${s.lead_stock_name} (${s.lead_stock})`

## CSS Classes Reference

- `.tab-bar` / `.tab-item` / `.tab-item.active` - Browser-style tab bar
- `.tab-btn` / `.tab-refresh` / `.tab-close` - Tab action buttons
- `.page` / `.page.active` - Page visibility
- `.nav-item` / `.nav-item.active` - Sidebar navigation
- `.page-controls` - Top filter bar
- `.empty-state` - Empty data placeholder
- `.loading` - Loading indicator
- `.metrics` / `.metric` - Metric cards grid
- `.badge` / `.badge-green` / `.badge-red` / `.badge-blue` / `.badge-orange` - Status badges
- `.btn` / `.btn-primary` / `.btn-success` / `.btn-danger` / `.btn-secondary` - Buttons
- `.btn-refresh` - Clean refresh button with ↻ icon (user preferred over generic btn-primary for refresh actions)
- `.sector-card` - Sector flow cards
- `.lead-stock-link` - Clickable stock links
- `.tab-group` / `.tab-group .tab` - Inline sub-tabs within a page

## Refresh Button Styling

User feedback: "刷新按钮太丑了" - The generic `btn-primary` with 🔄 emoji was too bulky for refresh actions.

Solution: Custom `.btn-refresh` class with clean styling:

```css
.btn-refresh {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-refresh:hover {
  background: var(--accent-blue);
  border-color: var(--accent-blue);
  color: #fff;
}

.btn-refresh::before {
  content: "↻";
  font-size: 14px;
}
```

Usage: `<button class="btn-refresh" onclick="loadData()">刷新</button>`

## Integrating Standalone Pages into Main Nav

When a feature exists as a standalone page (e.g., `/arbitrage` with its own `arbitrage.html`), integrating it into the main dashboard requires 5 coordinated changes:

### Pattern (proven with arbitrage integration)

1. **`templates/index.html`** — Add sidebar nav item + page container div
2. **`static/js/app.js`** — Add to `TAB_CONFIG` + add case in `loadTabData()` switch
3. **`static/js/<feature>.js`** — Create new JS module with load/render/filter functions
4. **`static/css/style.css`** — Add component styles (use CSS variables for dark mode)
5. **`index.html` bottom** — Add `<script src>` for the new JS file

### Pitfalls
- **Standalone pages have inline styles** — Extract to CSS variables when integrating (don't copy raw hex colors)
- **Modals use `#modal-container`** — The main dashboard has a shared modal container; render into it instead of creating new overlays
- **Dark mode requires `[data-theme="light"]` overrides** — Every component with hardcoded backgrounds/borders needs light mode variants
- **CSS class name collisions** — Prefix new classes (e.g., `arb-` for arbitrage) to avoid conflicts with existing styles
