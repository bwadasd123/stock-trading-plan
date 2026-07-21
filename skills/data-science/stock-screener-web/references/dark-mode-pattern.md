# Dark/Light Mode CSS Pattern

## CSS Variables (in style.css :root)
```css
:root {
  --bg-primary: #0f1117;
  --bg-secondary: #1a1d29;
  --bg-tertiary: #252836;
  --border-color: #2a2d3a;
  --text-primary: #e0e0e0;
  --text-secondary: #888;
  --accent-green: #4CAF50;
  --accent-red: #ef5350;
  --accent-blue: #2196F3;
  --accent-orange: #ff9800;
}

[data-theme="light"] {
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-tertiary: #f1f5f9;
  --border-color: #e2e8f0;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --accent-green: #22c55e;
  --accent-red: #ef4444;
  --accent-blue: #3b82f6;
  --accent-orange: #f59e0b;
}
```

## Required Light Theme Overrides
Components with hardcoded backgrounds need explicit overrides:
```css
[data-theme="light"] .modal-overlay { background: rgba(0, 0, 0, 0.4); }
[data-theme="light"] .btn-refresh { background: #e2e8f0; color: #333; border-color: #d1d5db; }
[data-theme="light"] .sector-card { background: #fff; border-color: #e5e7eb; }
[data-theme="light"] .stats-dashboard { background: #fff; border-color: #e5e7eb; }
[data-theme="light"] .filter-panel { background: #fff; border-color: #e5e7eb; }
[data-theme="light"] .result-panel { background: #fff; }
[data-theme="light"] .page-controls { background: #fff; border-color: #e5e7eb; }
[data-theme="light"] .settings-card { background: #fff; border-color: #e5e7eb; }
[data-theme="light"] .lead-stock-link { color: #3b82f6; }
```

## JS Toggle (in app.js)
```javascript
function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeButton(savedTheme);
}
function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  updateThemeButton(next);
}
```

## Rule
Any new component with hardcoded background/border/color MUST add a `[data-theme="light"]` override.
