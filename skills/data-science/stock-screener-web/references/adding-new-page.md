# 添加新页面到Dashboard

## 必须完成的3个步骤（缺一不可）

### 1. 创建API蓝图（如需要）
```python
# api/my_feature.py
from flask import Blueprint, jsonify
my_feature_bp = Blueprint('my_feature', __name__)

@my_feature_bp.route('/api/my_feature', methods=['GET'])
def get_data():
    return jsonify({"success": True, "data": {}})
```

### 2. 在 app.py 注册蓝图
```python
# app.py — import + register
from api.my_feature import my_feature_bp
app.register_blueprint(my_feature_bp)
```

### 3. 在 index.html 添加页面 + 在 app.js 注册TAB_CONFIG

**index.html** — 侧边栏导航：
```html
<a href="#" class="nav-item" data-page="my_feature">
  <span class="nav-icon">🎯</span>
  <span class="nav-text">我的功能</span>
</a>
```

**index.html** — 页面内容区（在 `<!-- 系统设置页面 -->` 之前）：
```html
<div id="page-my_feature" class="page">
  <!-- 内容 -->
</div>
```

**static/js/app.js** — **TAB_CONFIG 必须注册！**：
```javascript
const TAB_CONFIG = {
  // ... existing entries ...
  my_feature: { icon: '🎯', title: '我的功能', refreshable: true },
};
```

## ⚠️ 常见错误
- **页面点不开**：TAB_CONFIG 没注册。点击侧边栏链接无反应。
- **页面内容不显示**：`id="page-xxx"` 和 `data-page="xxx"` 不匹配。
- **JS报错**：页面JS代码在页面元素不存在时执行。用 `if (document.getElementById('xxx'))` 保护。
