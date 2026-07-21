# 侧边栏外部链接模式

## 问题

侧边栏 `.nav-item` 的点击事件在 `app.js` 中被统一拦截：

```js
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', function(e) {
      e.preventDefault();  // ← 拦截所有默认行为
      const page = this.dataset.page;
      openTab(page);
    });
  });
```

如果一个 nav-item 没有 `data-page` 属性（如外部链接 `/logs`），点击后 `page` 为 undefined，什么都不做 → 用户看到空白。

## 解决方案

修改 `app.js` 的事件处理，只在有 `data-page` 时才 `preventDefault`：

```js
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', function(e) {
      const page = this.dataset.page;
      if (page) {
        e.preventDefault();
        openTab(page);
      }
      // 没有data-page的链接（如/logs）正常跳转
    });
  });
```

## 侧边栏添加外部链接的正确方式

```html
<!-- 不要加 data-page，让浏览器正常跳转 -->
<a href="/logs" class="nav-item" target="_blank">
  <span class="nav-icon">📋</span>
  <span class="nav-text">实时日志</span>
</a>
```

- 不加 `data-page` → JS 不拦截，浏览器处理链接
- 加 `target="_blank"` → 新窗口打开（可选）

## 涉及文件

- `static/js/app.js` — DOMContentLoaded 事件绑定
- `templates/index.html` — 侧边栏 nav-item

## 相关 Pitfall

- 模板（HTML）修改后必须重启Flask才能生效（模板启动时加载）
- JS/CSS修改后告诉用户 Ctrl+F5 强制刷新（浏览器缓存）
