---
name: douyin-video-workflow
description: 抖音视频制作完整流程：生成板块资金流向视频 + 获取当日股市数据 + 生成抖音标题
triggers:
  - 做视频
  - 抖音视频
  - 今日视频
  - 做今天视频
---

# 抖音视频制作工作流

## 执行步骤

### Step 1: 生成视频
```bash
mkdir -p "/mnt/c/Users/Administrator/Desktop/工作室/抖音小韭菜"
cd /home/jmy && /home/jmy/.hermes/hermes-agent/venv/bin/python flow_douyin.py -o "/mnt/c/Users/Administrator/Desktop/工作室/抖音小韭菜/stock_flow_douyin_$(date +%Y%m%d).mp4"
```
- 视频参数: 1080x1920, 8fps, ~30秒
- 内容: 板块主力资金净流入TOP10 + 净流出TOP10 折线图Race动画
- 水印: @一棵小韭菜

### Step 2: 获取当日股市数据
```python
import sys
sys.path.insert(0, '/home/jmy/stock-screener')
from anti_crawl import safe_get, get_sector_headers
import time

# 1. 大盘指数 (上证/深证/创业板/沪深300)
url = 'http://push2delay.eastmoney.com/api/qt/ulist.np/get'
params = {'fltt': 2, 'fields': 'f2,f3,f4,f12,f14', 'secids': '1.000001,0.399001,0.399006,1.000300'}

# 2. TOP10净流入板块 (使用 push2delay，不能用 push2!)
url2 = 'http://push2delay.eastmoney.com/api/qt/clist/get'
params2 = {'fid': 'f62', 'po': 1, 'pz': 10, 'pn': 1, 'np': 1, 'fltt': 2, 'invt': 2, 'fs': 'm:90+t:2', 'fields': 'f12,f14,f62'}

# 3. TOP10净流出板块
params3 = {'fid': 'f62', 'po': 0, 'pz': 10, 'pn': 1, 'np': 1, 'fltt': 2, 'invt': 2, 'fs': 'm:90+t:2', 'fields': 'f12,f14,f62'}

# 4. 涨跌家数
params4 = {'fltt': 2, 'fields': 'f104,f105,f106', 'secids': '1.000001'}
```

**或者使用服务层**（推荐，已处理字段转换）：
```python
from services.sector_flow import fetch_sector_flow
# 返回 processed dicts: sector_name, change_pct, main_net_inflow(万元), lead_stock_name, lead_stock_code
items = fetch_sector_flow('industry', sort_field='f62', page_size=10, ascending=False)
```

### Step 3: 生成抖音标题
根据数据提供4-5个标题风格：
- **爆款型**: 数据冲击力 + 热点话题（如4000点）
- **数据型**: 完整日期 + 核心数据
- **情绪型**: 引发共鸣的问句
- **悬念型**: 设置悬念引导观看
- **简洁型**: 精炼概括 + 标签

## 输出格式
```
✅ 今日抖音视频已生成完成！
- 时长/大小/文件路径

📊 今日股市概况
- 大盘指数 + 涨跌幅
- 资金流向TOP板块

🎬 抖音标题（4-5个风格供选择）
```

## 注意事项
- 视频生成约需5-6分钟（240帧渲染）
- 使用notify_on_complete等待完成
- 每次请求间隔1秒（防反爬）
- 标题要结合当日最大看点（如指数关口、板块异动）
