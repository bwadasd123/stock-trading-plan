# CSS Theme Variables Reference

## 暗色模式 (`:root`)
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
  --accent-color: #4CAF50;
}
```

## 亮色模式 (`[data-theme="light"]`)
```css
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
  --accent-color: #22c55e;
}
```

## 新增变量规则
新增CSS变量时，**必须在两个主题块中都定义**，否则元素在某个主题下会不可见。

常用变量：
- `--accent-color` - 按钮、强调色
- `--card-bg` - 卡片背景
- `--input-bg` - 输入框背景
- `--border-color` - 边框颜色
- `--text-primary` / `--text-secondary` - 文字颜色
