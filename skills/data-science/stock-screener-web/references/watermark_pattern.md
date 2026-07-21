# 全屏水印实现

## CSS方案

使用 flexbox 布局 + JS 动态生成，实现水印铺满屏幕。

### ⚠️ html2canvas 兼容模式（推荐）

如果页面需要截图功能，**不能用 `position: fixed`**，html2canvas 不支持。

```css
/* 容器必须 position: relative */
.report-container { position: relative; }

.watermark-overlay {
  position: absolute;  /* ✅ 不能用 fixed！html2canvas不渲染fixed */
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  z-index: 99;  /* 不能太高，否则截图按钮点不到 */
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
}
```

### 纯展示模式（不需要截图）

```css
.watermark-overlay {
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  z-index: 9999;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
}
```

### 水印项样式

```css
.watermark-item {
  width: 300px;
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: rotate(-35deg);
  flex-shrink: 0;
}
.watermark-item span {
  font-size: 16px;
  color: rgba(30, 64, 175, 0.15);  /* 半透明蓝色 */
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: 2px;
  user-select: none;
}
```

## JavaScript

### ⚠️ 必须用 DOMContentLoaded（2026-06-25血泪教训）

**问题**：脚本在 `<div id="watermark">` 之前执行时，`getElementById` 返回 null，后续的 `addEventListener` 也不会注册。

**错误模式**：
```html
<script>
function generateWatermarks() {
  const overlay = document.getElementById('watermark'); // null！元素还没创建
  overlay.innerHTML = html; // 报错，后续代码不执行
}
generateWatermarks(); // 💥 报错
window.addEventListener('resize', generateWatermarks); // 不会执行！
</script>

<div class="watermark-overlay" id="watermark"></div>  <!-- 脚本在它之前 -->
```

**✅ 正确**：用 DOMContentLoaded 确保 DOM 加载完成
```javascript
function generateWatermarks() {
  const overlay = document.getElementById('watermark');
  const container = document.querySelector('.report-container');
  if (!overlay || !container) return;  // 防御性检查
  
  const text = '水印文字';
  const itemWidth = 300;
  const itemHeight = 150;
  
  // ⚠️ 用容器尺寸而非窗口尺寸（absolute定位时）
  const containerWidth = container.scrollWidth;
  const containerHeight = container.scrollHeight;
  const cols = Math.ceil(containerWidth / itemWidth) + 1;
  const rows = Math.ceil(containerHeight / itemHeight) + 1;
  const total = cols * rows;
  
  let html = '';
  for (let i = 0; i < total; i++) {
    html += `<div class="watermark-item"><span>${text}</span></div>`;
  }
  overlay.innerHTML = html;
}

// ✅ 等DOM加载完成后再生成
document.addEventListener('DOMContentLoaded', function() {
  generateWatermarks();
  window.addEventListener('resize', generateWatermarks);
});
```

### 纯展示模式（fixed定位）

```javascript
function generateWatermarks() {
  const overlay = document.getElementById('watermark');
  if (!overlay) return;
  
  const text = '水印文字';
  const itemWidth = 300;
  const itemHeight = 150;
  
  // fixed定位用窗口尺寸
  const cols = Math.ceil(window.innerWidth / itemWidth) + 2;
  const rows = Math.ceil(window.innerHeight / itemHeight) + 2;
  const total = cols * rows;
  
  let html = '';
  for (let i = 0; i < total; i++) {
    html += `<div class="watermark-item"><span>${text}</span></div>`;
  }
  overlay.innerHTML = html;
}
```

## html2canvas 截图要点

### ⚠️ 已知限制

1. **`position: fixed` 不渲染** — 必须改用 `position: absolute` + 容器 `position: relative`
2. **`background-clip: text` 不渲染** — 渐变文字效果在截图中显示为普通文字或消失，改用纯色
3. **`transform: rotate()` 可能异常** — 水印的旋转在某些情况下渲染不正确

### 截图时隐藏/显示元素

```javascript
async function takeScreenshot() {
  const btn = document.getElementById('screenshot-btn');
  btn.textContent = '⏳ 截图中...';
  btn.classList.add('loading');
  
  try {
    // 只隐藏按钮，保留水印
    const themeBtn = document.querySelector('.theme-toggle');
    const screenshotBtnEl = document.getElementById('screenshot-btn');
    themeBtn.style.display = 'none';
    screenshotBtnEl.style.display = 'none';
    
    const container = document.querySelector('.report-container');
    const canvas = await html2canvas(container, {
      backgroundColor: document.body.classList.contains('light') ? '#f0f2f5' : '#0a0e17',
      scale: 2,
      useCORS: true,
      logging: false
    });
    
    // 恢复显示
    themeBtn.style.display = '';
    screenshotBtnEl.style.display = '';
    
    // 下载图片
    const link = document.createElement('a');
    const now = new Date();
    const dateStr = now.toISOString().slice(10);
    link.download = `JMY_看板_${dateStr}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    
    btn.textContent = '✅ 已保存';
    setTimeout(() => { btn.textContent = '📸 截图'; btn.classList.remove('loading'); }, 2000);
  } catch(e) {
    // 恢复显示（错误时也要恢复）
    document.querySelector('.theme-toggle').style.display = '';
    document.getElementById('screenshot-btn').style.display = '';
    btn.textContent = '❌ 失败';
    setTimeout(() => { btn.textContent = '📸 截图'; btn.classList.remove('loading'); }, 2000);
  }
}
```

### CDN引入

```html
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
```

## 要点

- `pointer-events: none` 确保不影响页面交互
- `user-select: none` 防止选中水印文字
- 窗口 resize 时重新生成水印
- 透明度 0.15 适中，不影响内容阅读
- **需要截图时用 absolute，不需要截图时用 fixed**
- **脚本必须在 DOMContentLoaded 中执行，不能在 DOM 元素之前直接调用**
