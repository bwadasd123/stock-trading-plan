# 系统设置页面空白诊断

## 症状
点击"系统设置"标签，标签激活但内容区域完全空白。

## 诊断步骤

### 1. 检查页面是否有active类
```javascript
document.querySelector('#page-settings').classList.toString()
// 应该返回 "page active"
```

### 2. 检查offsetHeight
```javascript
document.querySelector('#page-settings').offsetHeight
// 如果是0，说明页面没有渲染
```

### 3. 检查DOM层级链（关键！）
```javascript
var el = document.querySelector('#page-settings');
var chain = [];
while (el && el !== document.body) {
  chain.push({tag: el.tagName, id: el.id, className: el.className, display: getComputedStyle(el).display});
  el = el.parentElement;
}
console.log(chain);
```

**正常层级**：`page-settings > page-container > main`
**异常层级**：`page-settings > backtest-container > page-backtest(display:none) > page-container > main`

如果发现page-settings嵌套在其他page里面，就是HTML div未关闭。

### 4. 检查settings-container高度
```javascript
document.querySelector('.settings-container').offsetHeight
// 如果是0，检查子元素
document.querySelector('.settings-section').offsetHeight
document.querySelector('.settings-card').offsetHeight
```

## 已知Bug修复

### Bug: HTML div未关闭导致页面嵌套（2026-06-17）
**根因**：index.html中回测页面(page-backtest)的两个`<div>`没有正确关闭，导致page-settings被嵌套在page-backtest里面。

**症状**：DOM层级显示page-settings在page-backtest内部，而page-backtest没有active类所以display:none。

**修复**：在index.html中找到缺失的`</div>`并补上。具体位置在回测页面的backtest-container关闭标签附近。

**诊断命令**：
```bash
# 检查index.html中div的开闭是否匹配
grep -n '<div\|</div>' /home/jmy/stock-screener/templates/index.html | head -100
```
