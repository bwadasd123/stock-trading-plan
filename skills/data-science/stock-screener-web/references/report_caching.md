# 报表页面缓存优化

## 问题

`/api/report_data` 每次加载都实时调用东财API获取板块数据，导致页面卡顿。

## 解决方案

优先从已保存的今日看点缓存（`daily_digest_cache` 表）读取数据。

### 修复位置
- `/home/jmy/stock-screener/api/report.py`

### 逻辑流程

1. 检查 `force` 参数，非强制则尝试读缓存
2. 调用 `load_daily_digest(date_str)` 从MySQL读取
3. 缓存命中 → 直接返回（秒加载）
4. 缓存未命中 → 实时获取东财API

### 关键代码模式

```python
# 优先从已保存的今日看点读取
if not force:
    from models.database import load_daily_digest
    cached = load_daily_digest(date_str)
    if cached and cached.get("inflow_sectors"):
        # 转换缓存数据格式...
        return jsonify(result)
```

## 相关Pitfalls

### 前端缓存条件 bug

**问题代码：**
```javascript
if (!forceRefresh && tabDataCache['daily'] && !tabDataCache['daily'].from_cache) {
```

**问题：** `from_cache: true` 的数据被错误地认为"无效缓存"，导致每次都重新请求。

**修复：**
```javascript
if (!forceRefresh && tabDataCache['daily']) {
```

**教训：** `from_cache` 只是标记数据来源，不应影响缓存有效性判断。
