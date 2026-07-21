---
name: stock-screener-web
description: Extend and maintain the A股智能筛选 Web Dashboard (Flask + MySQL + 东方财富API). Add features, database tables, API endpoints, and frontend functionality.
tags: [stock, flask, mysql, eastmoney, web-dashboard, a股, screener]
triggers:
  - stock screener feature request
  - stock_web_v2.py modification
  - A股看板功能
  - add API endpoint to stock dashboard
  - stock database table
  - 板块资金流向
  - sector flow
  - 启动A股系统
  - 启动系统
  - start stock screener
  - A股系统启动
  - 启动A股
  - stock_screener startup
  - app.py startup
---

# A股智能筛选 Web Dashboard

## Overview

Flask-based web dashboard for A-share stock screening with:
- Full market scanning (东方财富API)
- Two-round filtering: fundamentals + technical indicators
- MySQL storage for results and snapshots
- SSE real-time progress
- Proxy pool management (anti-crawl)
- **板块资金流向** (Sector Fund Flow) - Industry & Concept sectors, with ECharts history trend charts
- **LOF/ETF套利监控** - Integrated into main dashboard nav (was standalone page)
- **龙虎榜** (Dragon Tiger List)
- **自选股监控** (Watchlist)
- **Dark/Light mode** - Full theme support with CSS variables

## ⚠️ 两个独立系统架构（必读）

本skill管理**两个独立系统**，共用同一个MySQL数据库但代码完全独立：

| 用户称呼 | 系统 | 代码目录 | API | 前端 |
|---------|------|---------|-----|------|
| **"主系统"** | 分析平台 | `/home/jmy/.hermes/profiles/eastmoney-bot/` | `api/history.py` | `static/js/app.js` + `index.html` |
| **"看板"** | 股票筛选器 | `/home/jmy/stock-screener/` | 见下方拆分 | 见下方拆分 |

**⚠️ 看板内部有两个独立页面显示历史信号**：
| 看板页面 | URL | API端点 | 前端文件 |
|---------|-----|---------|---------|
| 报告页 | `/report` | `api/report.py` → `/api/report_data` | `templates/report.html` |
| 历史信号tab | `/` (主页侧边栏) | `api/history.py` → `/api/history` | `templates/index.html` |

**三个地方都显示历史信号，但用不同的API和前端代码！改了一个另一个不会自动生效。**

### 用户说"看板的"时怎么判断改哪个？
- URL是 `http://localhost:8080/report` → 改 `api/report.py`
- 用户说"看板的历史信号页签"、"侧边栏的历史信号" → 改 `api/history.py`
- 不确定 → **两个都改**

修改数据展示时必须同时检查所有相关代码。详见`references/historical-signal-max-price.md`。

## Key References
- `references/log-streaming-pattern.md` - **实时日志流（SSE）实现模式**
- `references/proxy-pool-current.md` - **⚠️ 代理池当前实现（random.choice + mark_bad + refill）**
- `references/proxy-api-config.md` - **宜代理API配置（secret/orderId，永不变化）**
- `references/eastmoney-domain-routing.md` - **东财域名路由规则（push2delay vs push2his）**
- `references/kline-indicator-pitfalls.md` - **K线数据与指标计算陷阱**
- `references/executor-shutdown-pattern.md` - **ThreadPoolExecutor停止模式**
- `references/database-operations.md` - **数据库操作参考**
- `references/health-check.md` - Endpoint health check commands
- `references/post-scan-workflow.md` - **扫描结果解读 + 投资决策流程**
- `references/flask-startup-pitfalls.md` - **Flask启动陷阱（logging死锁、代理池阻塞）**
- `references/settings-page-pattern.md` - **系统设置页面模式（含CSS高度0 bug诊断）**
- `references/no-proxy-and-scan-profit.md` - **NO_PROXY问题 + 扫描盈利统计API**
- `references/report_profit_stats.md` - **/report页面盈利统计模块（本月战绩卡片+明细表）**
- `references/report-signal-dedup-and-date.md` - **报告页信号去重+日期显示修复（2026-06-26）**

## ⚠️ Development Rules — 改代码铁律

### 绝对不要过度工程化（血泪教训 2026-06-16）
用户说"小一点没事"就是字面意思。最简单的方案往往是用户想要的。
**反面案例**：用户说"池子空就等待"，我加了冷却池→黑名单→去掉池子→直接API获取→把整个代理池架构改掉了。用户非常生气。正确做法：只改那一行等待逻辑。
**反面案例2**: 用户说"代理池循环用死代理"，我加了冷却池(cooling dict)→用户说"还加黑干啥"→我改成pop/put_back→用户说"代理池本来就是好的"→我恢复原代码只改两处→用户说"很好 就这样的干得很好"。
**教训**: 用户指出的问题往往很小，解决方案也应该很小。先用`git diff`确认只改了目标位置。

### 用户要求改A，只改A（2026-06-16 强化）
不要改BCDEF。改之前先diff确认只改了目标位置。不要顺手"优化"其他地方。
**反面案例**: 用户要"池子空等待"+"Cookie改120秒"，我却重写了整个ProxyPool类、删了代理池、改了safe_get架构。用户原话："你又要改啥？我非常生气"、"刚才代理池都是好的你能理解吗 一直在这里绕什么啊"。
**正确做法**: `git checkout`恢复原文件 → 只改两行 → 测试 → 提交。

### 用户说"这个之前是好的"
意思是代码本来能用，你改坏了。**立刻git checkout恢复**，然后只做用户要求的小改动。

### 用户生气时立刻停止
说"停"就停，不要继续改代码。先总结当前状态，等用户指示。

### 改代码前先读，读完再改
不要边改边读。先把相关代码全部读完理解透，再动手改。
**改A只改A**，不要顺手"优化"其他地方。读完代码后先总结"我看到了什么"，不要读完就开始分析问题、提方案、改代码。

### 说话精简，不啰嗦
用户明确要求：上下文精简，直接给结论和操作，不反复确认。不要长篇分析、不要重复读代码、不要列举多种方案让用户选。做实事，说重点。

### 改完代码自己测试，不要让用户验证
改完代码后自己跑测试（curl、python脚本、浏览器），确认结果正确后再汇报。不要让用户去测试。
**反面案例**: 我修了代理池bug后说"你去测回测吧"，用户说"我建议你自己测试一下"。
**正确做法**: 改完 → 自己跑回测/请求 → 看日志确认 → 给用户结果截图或数据。

### 用户说"先看X怎么实现的"→ 只读，等下一步指令
用户让你先读代码理解实现，就只读+总结，然后停下来等用户指示下一步。不要读完就开始分析问题、提方案、改代码。用户想让你理解现状后再按他的思路来，不是让你自己找问题。
**反面案例**: 用户说"你先看下双版本对比怎么实现的"，我读完就开始分析代理池问题、提修改方案，用户暴怒："先听我说的内容 我让你先看下他怎么实现的明白吗？？？？？？？？？"。
**正确做法**: 读代码 → 用一两句话总结"我看完了，X用的是Y方式" → 停，等用户说下一步。

### 其他规则
1. **After ANY code change**: Restart Flask immediately
2. **After ANY code change**: Update README.md, then git commit + push
3. **Use `safe_get`** for all eastmoney API calls — 只用代理，池子空等待重试，不走直连
4. **Use `get_sector_headers()`** for proper headers
5. **Cache aggressively** - 60s TTL for API responses
6. **Mobile-first** - Responsive design for all pages
7. **After startup, run health check**
8. **All API endpoints need try/except**
9. **Browser cache** — 用户看不到代码变化时，先curl验证，再让用户Ctrl+F5
10. **Python Global Variable Pitfall** — `from module import var` creates local binding. Use `import module as m` + `m.var`
11. **K线API** — 禁用smplmt参数! 量比=今日/昨日。RSI用SMA。
12. **代理池配置** — 代码里`***`是混淆，不是失效。永远不要质疑订单号。
13. **⚠️ 数据库连接方式** — 使用 `from models.database import get_db`
14. **⚠️ logging.Handler子类锁死锁** — 子类不能用`self.lock`覆盖父类RLock，用`self.sub_lock`
15. **⚠️ 侧边栏外部链接** — 不加`data-page`属性，否则JS拦截
16. **⚠️ 新页面必须注册TAB_CONFIG** — `static/js/app.js`的`TAB_CONFIG`对象必须添加新页面条目，否则点击侧边栏不会切换页面。格式: `{ icon: '📊', title: '回测系统', refreshable: false }`
17. **⚠️ 代码没坏就不要改** — 用户说"之前是好的"→`git checkout`恢复→只改用户要求的部分。不要顺手"优化"其他地方。
18. **⚠️ 重要按钮必须放在页面顶部显眼位置** — 用户说"按钮竟然是个空白的 要不是我看了html我都不知道在哪"。主要操作按钮（开始、提交、保存等）必须放在标题右侧或下方，用醒目样式（大字号、主题色、足够padding）。不要放在右下角、浮动定位、或用低对比度颜色。**绝对不要让按钮在首屏之外** — 用户不会滚动去找按钮。最佳实践：标题和按钮在同一行（flex布局），用户一进页面就能看到。
19. **⚠️ UI元素必须适配亮暗主题** — 所有使用CSS变量的元素，必须确保变量在两个主题中都有定义。`style.css`的`:root`和`[data-theme="light"]`中都要定义。常用变量：`--accent-color`（主题色）、`--card-bg`、`--input-bg`等。用户说"纯白的 谁能看到"就是变量未定义导致的。检查方法：grep样式中使用的变量名，确认在两个主题块中都有定义。**新增元素必须同步添加亮色覆盖** — 包括卡片、表格、辅助区域（如计算逻辑说明框）。用户会主动切换主题检查，漏掉任何元素都会被发现。用`body.light #element-id`或`body.light .class-name`覆盖。**规则：每加一个新组件，先写暗色样式，再立刻写亮色覆盖，不要留到后面。**
19. **⚠️ 循环请求API必须加延时** — 代理池只有3个，循环请求K线/列表数据时必须`time.sleep(2)`，否则代理池耗尽、重试5次仍失败。适用于回测、批量分析等场景。
20. **⚠️ safe_get重试策略** — 默认10次重试，连续失败3次自动刷新Cookie。详见`anti_crawl.py`的`consecutive_failures`逻辑。
21. **⚠️ 去重逻辑必须与历史信号一致** — 回测去重使用`first_discovery_date = data_date`（从`v_scan_results_with_change`视图），不是简单GROUP BY。下拉框按日期分组显示，不是scan_id。
22. **⚠️ CSS .page类必须有active状态显示规则** — 系统设置等页面空白(高度0)通常是`.page`类缺少`.page.active { display: block; }`规则。也可能是HTML div未关闭导致页面嵌套在`display:none`的父元素中。诊断：浏览器控制台检查DOM层级链。详见`references/settings-page-pattern.md`。
23. **⚠️ 两个代理池不一致导致mark_bad无效** — `safe_get`中调用`PROXY_POOL.mark_bad()`(ProxyPool类185行)，但`get_proxy_dict`使用`ENHANCED_PROXY_POOL.get()`(EnhancedProxyPool类940行)。必须统一使用`ENHANCED_PROXY_POOL.mark_bad()`。症状：日志中看不到`🗑️ 移除失效代理`，坏代理一直在用。
24. **⚠️ 双版本扫描筛选条件key映射** — 前端发`turn1/cap/rsi/volr`，扫描器期望`r1_turnover/r1_cap_max/r2_rsi/r2_vol_ratio`。API层(`/api/dual_scan_all`)必须做转换。
25. **⚠️ 代理池字典必须包含uses字段** — `self.proxies[p]`初始化时必须有`"uses": 0`，否则`_monitor_pool`访问`info["uses"]`会KeyError崩溃。所有添加代理的地方（`_fill_on_init`、`_refill`、`_refill_async`、`_replace_proxy`）都要检查。症状：日志出现`Exception in thread Thread-3 (_monitor_pool): KeyError: 'uses'`。
26. **⚠️ 修bug必须同步更新文档** — 用户明确要求"记得文档也要改"。修完bug后检查README.md、相关*.md文档是否需要更新，然后一起commit+push。
27. **⚠️ 避免连续引入bug** — 用户抱怨"你最近的bug好多"。改代码前必须完整阅读相关代码，理解调用链，不要只看局部就改。修完后自己测试验证。
28. **⚠️ pymysql SQL中DATE_FORMAT用单%** — Python字符串中`%%Y-%%m-01`会被解释为字面量`%Y-%m-01`，而不是日期格式化。正确写法：`DATE_FORMAT(NOW(), '%Y-%m-01')`（单百分号）。症状：查询返回所有历史数据而非本月数据。
29. **⚠️ 东财API必须设置NO_PROXY** — 系统有HTTP_PROXY环境变量，导致东财API走代理超时。在获取东财数据前必须设置`os.environ['NO_PROXY'] = '*'`，用完后恢复原值。详见`references/no-proxy-and-scan-profit.md`。
30. **⚠️ 截图功能使用html2canvas** — 主看板用侧边栏按钮+`static/js/screenshot.js`；/report等独立页面用内联JS+CDN引入html2canvas。**截图时保留水印，只隐藏按钮**（用户发社群需要品牌标识）。详见`references/report_page.md`截图功能章节。
31. **⚠️ 用户说加到哪个页面就加到哪个页面** — 用户给了具体URL（如`http://localhost:8080/report`），功能必须加到那个页面，不是你认为"合适"的页面。**反面案例**：用户说"在report上加截图"，我加到了主看板index.html，用户质问"你加到哪里去了"。**正确做法**：看用户给的URL路径，确认对应的模板文件（如`/report`→`templates/report.html`），再动手。
32. **⚠️ CSS ::before + absolute在表格中会导致溢出** — `<tr>`上用`position: relative` + `::before`的`position: absolute`会导致表格列宽计算错误、内容溢出。**正确做法**：用内联`<span>`元素放在`<td>`内部，或改用卡片式布局（CSS grid的`.signal-row`）。详见`references/report_page.md`最新一行高亮样式章节。
33. **⚠️ 截图必须保留水印** — 用户截图发社群/论坛，水印是品牌标识。不要自作主张隐藏水印。只隐藏按钮（截图按钮、主题切换按钮），保留水印overlay。
34. **⚠️ 历史信号用卡片布局不用表格** — 信号列表用CSS grid卡片式（`.signal-list` + `.signal-row`），不用`<table>`。卡片布局更清晰、hover效果好、NEW标签不会撑破布局。列：代码+名称 | 版本+日期 | 发现价 | 数据价 | 距离首期 | 累计涨跌。详见`references/report_page.md`信号列表设计章节。
35. **⚠️ html2canvas不能渲染`position: fixed`元素** — 水印用`position: fixed`时截图中不显示。**解决方案**：水印overlay必须放在`report-container`内部，用`position: absolute`（容器需`position: relative`）。**额外注意**：水印生成函数必须用`container.scrollWidth/scrollHeight`计算数量（不用`window.innerWidth/Height`），且必须在`window.load`事件后再次生成（内容是动态fetch加载的）。详见`references/report_page.md`截图功能章节。
38. **⚠️ 主系统和看板是两个独立系统，看板内有两个历史信号页面** — 用户说"主系统"=`/home/jmy/.hermes/profiles/eastmoney-bot/`的`api/history.py`+`static/js/app.js`；用户说"看板"=`/home/jmy/stock-screener/`。但看板内部有两个独立页面显示历史信号：(1) 报告页`/report`用`api/report.py`→`/api/report_data`；(2) 侧边栏历史信号tab用`api/history.py`→`/api/history`。**用户说"看板的历史信号页签"→改`api/history.py`；用户给URL`/report`→改`api/report.py`；不确定→两个都改。** 改了一个另一个不会自动生效。**2026-06-26教训**：用户说"看板的"我只改了report页面，没改history tab，用户暴怒。详见`references/historical-signal-max-price.md`。
40. **⚠️ 报告页历史信号"现价"走stock_snapshot表，不要新建表（2026-06-29教训）** — `stock_snapshot`每天双版本扫描时已存全市场所有股票价格。report直接查`SELECT latest_price, change_pct FROM stock_snapshot WHERE ts_code IN (...) AND DATE(scan_time)=CURDATE()`。**不要新建signal_price_history表或定时同步任务**，也不要在report页面实时调API。用户说"既然每天拉的列表里都有金额为什么不存呢，你还得要实时获取"。**不存在的表**：signal_price_history。
41. **⚠️ 不要自作主张加cronjob（2026-06-29教训）** — 用户说"谁要你自动跑了啊"。如果系统已有流程覆盖需求（如扫描已经存了价格），就不要额外加定时任务。只做用户明确要求的事。
43. **⚠️ 盘后推送必须合并双版本(old+new) — 2026-06-30** `scanner_dual.py`原只传`results_new`，old=2/new=0时误报"今日无信号"。改为`all_results = results_old + results_new`合并。 — 用户说"日期列都看不清"。日期样式：font-size: 13px, font-weight: 500, letter-spacing: 0.3px。暗色主题color: #94a3b8，亮色主题color: #64748b。不要用小字浅灰色。详见`references/report-signal-dedup-and-date.md`。
41. **⚠️ 减法要问用户，加法可以自己做** — 去掉列/功能前必须确认。这次自作主张去掉了"数据价"和"累计涨跌"两列，用户立刻要求加回来。用户说"页面太长"→优化间距/padding，不要减少列数。用户说"列表行太高了"→压缩padding和gap，不要砍列。详见`references/report-signal-dedup-and-date.md`列表行高优化章节。
39. **⚠️ 水印生成必须用容器尺寸+DOMContentLoaded** — 两个坑：(1) 水印移到容器内部后，`generateWatermarks()`用`window.innerWidth/Height`会导致水印数量不够，必须用`container.scrollWidth/scrollHeight`；(2) **脚本在DOM元素之前执行是致命的**：`<script>`标签在`<div id="watermark">`之前，`getElementById`返回null→函数抛错→后面的`addEventListener`也执行不到→水印永远不生成。**正确做法**：用`DOMContentLoaded`包裹，且函数内加null检查。**错误**：直接调用`generateWatermarks()` + `window.addEventListener('load', ...)`，因为直接调用会抛错中断后续代码。**正确**：`document.addEventListener('DOMContentLoaded', function() { generateWatermarks(); window.addEventListener('resize', generateWatermarks); });`
36. **⚠️ html2canvas不能渲染`background-clip: text`** — 亮色主题下section-title用渐变文字（`background: linear-gradient(); -webkit-background-clip: text`）在截图中会变成实色背景块。**解决方案**：亮色主题下section-title用纯色`color`，不用渐变文字。
37. **⚠️ 卡片式信号列表每列必须有label** — 用户说"标题都没了 这样用户不知道具体值是什么意思"。`sr-change`和`sr-gain`列必须有`<div class="label">`小标签说明含义（如"距入选"、"累计涨跌"），不能只显示数字。**label命名要用直观表达**：入选价（非发现价）、现价（非数据价）、距入选（非涨幅/距离首期）、累计涨跌（非累计）、最高价(日期)（非最高）。详见`references/report-signal-dedup-and-date.md`。
38. **⚠️ 胜率计算涨幅0%不算亏损** — `api/scan_profit.py`中`profit_pct == 0`不应计入`losing_count`。用`elif profit_pct < 0`而不是`else`。用户说"涨幅0的不应该算负"。详见`references/report-signal-dedup-and-date.md`。
39. **⚠️ 页面宽度保持git原始值** — 报告页原720px。用户说"太宽了"→改回720px。右边空白用grid列`1fr`单位填充，不要改容器宽度。用户说"原来是多少调一下"就是要回到git版本。详见`references/report-signal-dedup-and-date.md`。

## Quick Start
```bash
cd /home/jmy/stock-screener  # ⚠️ 必须用绝对路径，~/stock-screener会解析到hermes profile目录
pkill -9 -f "python3.*app.py" 2>/dev/null; sleep 2
python3 -u app.py &
sleep 30 && ss -tlnp | grep 8080 && curl -s http://localhost:8080/ | head -5
```

## Proxy Pool Architecture
当前使用 `random.choice` + `mark_bad` + refill 模式。详见 `references/proxy-pool-current.md`。

- **代理池大小**: 3个（PROXY_POOL_TARGET_SIZE=3）
- **Cookie TTL**: 120秒（cache_ttl=120）
- **池子空处理**: 等3秒→重试→等5秒→返回None（**绝不走本地直连**）
- **代理健康检查**: `_fill_on_init`用push2delay检查，`_refill_async`不检查
- **safe_get重试时池子空**: 等3秒从池子取，取不到再等5秒继续循环
- **safe_get全部失败**: return None（不走直连）

### anti_crawl.py 核心流程
```
safe_get(url, headers, params)
  ├─ get_proxy_dict() → PROXY_POOL.get() → random.choice
  │   池空 → _refill(2) → get_proxy_from_api()
  │   黑名单: _bad_proxies里的IP会被refill跳过，5分钟清一次
  ├─ SESSION.get(proxies=代理)
  │   200 → return
  │   407 → mark_bad → 补新代理
  │   其他 → mark_bad → 重试
  ├─ 重试: mark_bad旧的 → get_proxy_dict()取新的
  │   池空 → 等3秒再取 → 等5秒继续循环
  └─ 全部失败 → return None（不走直连）
```

### 代理API密钥
代码里显示`***`是系统遮蔽，实际密钥是正确的。永远不要质疑密钥是否失效。
详见 `references/proxy-api-config.md`。

## 扫描流程
```
run_full_scan()
  ├─ 遍历板块(SECTOR_CONFIGS)
  │   └─ 逐页拉列表 → safe_get(push2delay)
  │       ├─ 第一轮筛选：换手率、流通市值
  │       └─ 第二轮：ThreadPoolExecutor(2线程)
  │           └─ analyze_single_stock()
  │               ├─ get_kline_data_old() → safe_get(push2his)
  │               ├─ get_kline_data()    → safe_get(push2his)
  │               ├─ calc_indicators()   → RSI/MACD/CCI/MA20/量比
  │               └─ check_filters()     → 7个条件过滤
  └─ 汇总结果 → 保存DB
```

每只股票过第一轮后需要3次代理请求（1次列表+2次K线双版本）。2线程并行。

## Architecture
```
app.py                    # Flask main entry + blueprint registration
config.py                 # Configuration
anti_crawl.py             # Proxy pool + cookie management
models/database.py        # MySQL connection + table init
services/
  scanner.py              # Stock scanning logic
  scanner_dual.py         # Dual version comparison scanning
  kline.py                # K-line data + indicators
  sector_flow.py          # Sector fund flow
  watchlist.py            # Watchlist
  backtest.py             # 策略回测引擎
api/
  scan.py                 # Scanner API
  dual_scan.py            # Dual version API
  sector.py               # Sector flow API
  proxy_pool.py           # Proxy pool monitoring
  log_stream.py           # SSE log streaming
  backtest.py             # 回测API (/api/backtest/run, /api/backtest/signals)
templates/index.html      # Main dashboard (含回测页面)
static/js/app.js          # Main app logic
static/css/style.css      # All styles (dark/light theme)
```

## 回测系统
- **入口**: 侧边栏 → 📊 回测系统
- **API**: `POST /api/backtest/run` (参数: capital, position_pct, stop_loss, take_profit, max_hold_days, days, scan_id, code)
- **三种模式**: 全量(按天数) / 指定扫描(scan_id) / 单股(code)
- **逻辑**: 扫描信号次日开盘买入 → 逐日检查止损/止盈 → 到期收盘卖出
- **输出**: 胜率、总盈亏、收益率、盈亏比、最大回撤、收益曲线(ECharts)、交易明细表
- **性能**: 每只股票需通过代理获取K线数据，回测较慢。建议用scan_id单个测试
- 详见 `references/backtest-system.md`

## ⚠️ 历史信号数据字段说明（2026-06-26）

**用户反馈**：报告页历史信号的"数据价"和"累计涨跌"容易混淆。

### 数据库字段
- `latest_price`: 每次扫描时的价格（不同扫描可能不同）
- `latest_snap_price`: 当前快照价（所有记录相同）
- `max_amount_price`: 扫描期间最高价（数据库有但报告页未显示）

### 报告页显示逻辑
- **发现价** = `first_price` = 首次扫描的`latest_price`
- **数据价** = `data_price` = 每次扫描的`latest_price`（每次不同）
- **距离首期** = (data_price - first_price) / first_price
- **累计涨跌** = (latest_snap_price - first_price) / first_price（所有记录相同，因为snap_price相同）

### 用户困惑点
1. "数据价"显示每次扫描的价格，不是历史最高价
2. "累计涨跌"所有记录相同（因为用的是同一个snap_price）

### ✅ 已修复：历史最高价显示（2026-06-26）

**问题**：`max_amount_price`是按**成交额最大**取的价格，不是**价格最高**。导致历史最高价显示错误。

**修复方案**：在`_load_signals()`函数中，从`stock_snapshot`表查询`MAX(latest_price)`：

```python
# 查询每只股票的历史最高价
cur.execute("""
    SELECT ts_code, MAX(latest_price) as max_price
    FROM stock_snapshot
    WHERE ts_code IN (%s)
    GROUP BY ts_code
""", codes)

# 查询历史最高价对应的日期
cur.execute("""
    SELECT s.ts_code, s.latest_price, s.scan_time
    FROM stock_snapshot s
    INNER JOIN (
        SELECT ts_code, MAX(latest_price) as max_price
        FROM stock_snapshot
        GROUP BY ts_code
    ) m ON s.ts_code = m.ts_code AND s.latest_price = m.max_price
""", codes)
```

**新增字段**：
- `max_price`: 历史最高价
- `max_price_date`: 最高价日期
- `max_gain`: 最高涨幅 = (max_price - first_price) / first_price

**前端显示**：添加"最高价"和"最高涨幅"列到信号卡片。

详见 `references/historical-signal-max-price.md`。

### ✅ 已修复：报告页信号不去重（2026-06-29更新）

**2026-06-26修复（已废弃）**：每只股票只显示最新一条记录。

**2026-06-29用户要求**：不要去重，每条记录都显示。同一只股票在不同日期的每条扫描记录都要独立展示。用户说"你怎么去重了 这不对吧"。

**当前实现**：`_load_signals()`遍历`all_rows`的每一条，不分组去重：
```python
for row in all_rows:  # 不是 for code, rows in stock_map.items()
    # 每条记录独立生成signal
```

**日期显示**：每条记录用各自的`data_date`。NEW标签按日期判断：`s.data_date === today`。

**⚠️ Flask模板修改后必须重启服务** — 模板在启动时加载，修改HTML后必须kill进程重新启动才能生效。

## Related Skills
- **scanner-trading-plan** — 基于扫描结果的单股交易策略（3万本金）
- **serenity-chokepoint-investing** — AI supply-chain bottleneck analysis
