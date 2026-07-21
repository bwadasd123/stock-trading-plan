# LOF/ETF套利监控页面 (/arbitrage)

## 概述
实时监控可套利的LOF/ETF标的，计算溢价率，方便发现套利机会。支持两种净值计算方式：
1. **天天基金估算** - 简单模式，直接用fundgz API
2. **底层资产计算** - 高级模式，基于持仓+实时价格计算（参考 lof.i668.vip）

## 文件结构
- `services/arbitrage_targets.py` - 可套利标的列表（约44只）
- `services/fund_holdings.py` - 基金持仓映射配置（23只基金）
- `services/asset_prices.py` - 底层资产实时价格获取
- `services/nav_calculator.py` - 基于持仓的估算净值计算
- `api/arbitrage.py` - 套利监控API
- `templates/arbitrage.html` - 套利监控页面（卡片式布局+详情弹窗）

## 数据源

### 场内价格
- 东财行情API (`push2.eastmoney.com`)，使用 `fltt=2` 返回小数格式

### 估算净值（两种方式）

**方式1：天天基金API（简单）**
- `fundgz.1234567.com.cn/js/{code}.js` - JSONP格式
- 返回：`gsz`(估算净值), `dwjz`(最新净值), `gszzl`(估算涨跌)

**方式2：底层资产计算（高级，参考 lof.i668.vip）**
- 基金持仓配置 → 底层资产实时价格 → 计算估算净值
- 计算公式：`估算净值 = 基准净值 × (1 + 持仓收益 + 期货收益)`
- 持仓收益 = Σ(权重 × 涨跌幅)
- 期货收益 = 美股持仓权重 × 期货涨跌幅

### 底层资产价格获取
- **美股ETF**：东财API（`105.{ticker}`）优先，Yahoo Finance API备用（可直连）
- **港股**：东财API（`116.{code}`）
- **期货**：东财API（`101.{ticker}00Y`），仅GC/SI可用

### 溢价率计算
```
溢价率 = (场内价格 - 估算净值) / 估算净值 × 100%
```

## 可套利标的分类
| 类别 | 数量 | 代表标的 |
|------|------|---------|
| 黄金 | ~7只 | 518880, 159934, 160719 |
| 白银 | 1只 | 161226 |
| 原油 | ~6只 | 160216, 501018, 162719 |
| 美股 | ~10只 | 161125, 160213, 513100 |
| 港股 | ~8只 | 513050, 513180, 159920 |
| 中概 | ~5只 | 164906, 159605 |

## 申购状态管理
标的列表包含申购状态字段 `(代码, 名称, 类型, 分类, 申购状态)`：
- `open` - 可正常申购
- `limit` - 限额申购（仍可操作，但金额受限）
- `closed` - 暂停申购（无法套利）

**前端显示：**
- 🟢 可申购 / 🟡 限额 / 🔴 暂停
- 暂停申购的行半透明显示（`opacity: 0.7`）
- 筛选按钮"✅ 可操作"只显示有溢价且可申购的标的

**API返回字段：**
```json
{
  "subscribe_status": "open|limit|closed",
  "can_arbitrage": true  // open或limit且有溢价
}
```

**常见暂停申购标的：**
- 原油类：160216, 501018, 160723, 163208（外汇额度限制）
- QDII美股：160213（纳斯达克100LOF经常暂停）
- 中概：164906（中国互联LOF经常暂停）

### ⚠️ QDII ETF申购状态（重要）
**美股相关ETF场外申购基本都是暂停的**（QDII额度限制），包括：
```python
("513100", "纳指ETF", "ETF", "美股", "closed"),
("513300", "标普500ETF华夏", "ETF", "美股", "closed"),
("513500", "标普500ETF博时", "ETF", "美股", "closed"),
("159612", "标普500ETF国泰", "ETF", "美股", "closed"),
("159529", "标普消费ETF", "ETF", "美股", "closed"),
("159518", "标普油气ETF", "ETF", "美股", "closed"),
```

**用户纠正**：用户指出513100纳指ETF不应该显示"可申购"，实际是暂停状态。
- ETF虽然可以在场内买卖，但场外申购（套利需要）基本都是暂停的
- 只有港股ETF、黄金ETF等才可能有场外申购
- 添加新标的时，美股ETF默认设为`closed`

## API端点
```
GET /arbitrage       - 套利监控页面
GET /api/arbitrage   - 套利数据API（JSON）
```

### API返回结构
```json
{
  "data": [
    {
      "code": "513100",
      "name": "纳指ETF国泰",
      "fund_type": "ETF",
      "category": "美股",
      "price": 2.218,
      "change_pct": -0.98,
      "estimated_nav": 2.0702,
      "nav": 2.0808,
      "nav_date": "2026-06-03",
      "estimated_change": -0.51,
      "premium_rate": 7.14,
      "status": "high_premium",
      "subscribe_status": "open",
      "can_arbitrage": true,
      "update_time": "2026-06-05 04:00"
    }
  ],
  "from_cache": false,
  "update_time": "15:30:00",
  "total": 90
}
```

## 状态标识
| 状态 | 溢价率 | 含义 |
|------|--------|------|
| 🔴 high_premium | > 3% | 高溢价，有套利机会 |
| 🟡 premium | 1-3% | 有溢价，可关注 |
| ⚪ flat | -1% ~ 1% | 平价，无机会 |
| 🟢 discount | < -1% | 折价 |

## 缓存策略
- 60秒TTL缓存，避免频繁请求
- 前端每60秒自动刷新

## UI设计（2026-06-05 升级）

参考 lof.i668.vip 重新设计，采用**卡片式布局**替代旧表格。

### 首页布局
- **统计面板**：4个统计卡片（高溢价≥3%/有溢价≥1%/折价≤-1%/暂停申购）
- **筛选按钮**：全部/高溢价/有溢价/可操作/折价
- **卡片网格**：`grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))`
- **分组显示**：可操作卡片 + "暂停申购"分组（半透明）

### 卡片设计
每张卡片显示：
- 基金名称 + 代码（monospace蓝色）
- 申购状态标签（绿色可申购/橙色限额/红色暂停）
- 实时溢价率大字（24px，红涨绿跌）

卡片配色（左边框4px标识状态）：
- 高溢价：左边框红色 + 背景`#fef5f5`
- 有溢价：左边框橙色 + 背景`#fff9f0`
- 平价：左边框蓝色 + 背景`#f0f8ff`
- 折价：左边框绿色 + 背景`#f0fff5`
- 暂停申购：灰色左边框 + `opacity: 0.7`

### 详情弹窗（Modal）
点击卡片弹出详情：
- **溢价率大字**（48px）
- **三列对比**：场内价格 / 估算净值 / 最新净值
- **信息网格**：基金类型、申购状态、估算涨跌、净值日期、场内涨跌、更新时间
- **溢价率计算公式**：展示完整计算过程
- ESC键和点击背景关闭

### 设计风格
- 亮色主题：背景`#f5f5f5`，白色卡片，圆角10px
- 最大宽度900px居中
- 移动端响应式：单列布局
- 水印：@一棵小韭菜 | JMY科技

### 用户偏好
- **显示全部标的**，不要只显示有溢价的，用状态标识区分
- 暂停申购的也要显示，但半透明表示无法操作
- 用户可以一眼看到全貌

## ⚠️ Pitfalls

### 东财API必须走代理池（WSL）
**所有**东财API请求在WSL环境下必须通过**代理池**，直连会超时/502/RemoteDisconnected。
**不要**手动 `get_proxy_dict()` 拿单个代理再 `requests.get()` — 单个代理可能已失效，会 Connection refused。
**必须**用 `safe_get` 走代理池自动轮询：
```python
from anti_crawl import safe_get, get_sector_headers

headers = get_sector_headers()
resp = safe_get(url, headers=headers, params=params, timeout=15)
```

**❌ 错误模式**（单代理，容易失败）：
```python
from anti_crawl import get_proxy_dict
_, proxy_str = get_proxy_dict()
proxies = {"http": proxy_str, "https": proxy_str}
resp = requests.get(url, proxies=proxies, timeout=10)  # 代理可能已断！
```

**✅ 正确模式**（代理池轮询）：
```python
from anti_crawl import safe_get, get_sector_headers
resp = safe_get(url, headers=get_sector_headers(), params=params, timeout=15)
```

**2026-06-05 教训**：`push2.eastmoney.com` 从WSL直连返回502，用单代理超时Connection refused，改用 `safe_get` 后41/44只价格全部获取成功。

### 批量API的code_map映射
东财批量行情API返回的 `f12` 字段是**纯代码**（如 `"518880"`），**不是** secid格式（`"1.518880"`）。
code_map的key必须用纯代码：
```python
# ✅ 正确
code_map[code] = code  # API返回f12=原始code

# ❌ 错误
code_map[secid] = code  # key是"1.518880"，但API返回f12="518880"，匹配不上
```

### 天天基金估值API (fundgz)
- 返回JSONP格式，需手动解析 `{...}` 部分
- **非交易时间返回空** `jsonpgz();`（无数据）
- fundgz 可走代理也可直连，用 `_try_request` 模式（代理优先→直连兜底）：
```python
def _try_request(url, headers=None, params=None, timeout=8):
    proxies = get_proxies()
    if proxies:
        try:
            resp = requests.get(url, headers=headers or HEADERS, params=params, proxies=proxies, timeout=5)
            if resp and resp.status_code == 200:
                return resp
        except Exception:
            pass
    try:
        return requests.get(url, headers=headers or HEADERS, params=params, timeout=timeout)
    except Exception:
        return None
```
- ⚠️ **push2.eastmoney.com 不能用 `_try_request`**，必须用 `safe_get`（代理池轮询）
```python
resp = requests.get(f"https://fundgz.1234567.com.cn/js/{code}.js", headers=headers, proxies=proxies, timeout=8)
if resp.text and "{" in resp.text:
    start = resp.text.find('{')
    end = resp.text.rfind('}') + 1
    data = json.loads(resp.text[start:end])
```

### 东财价格字段 (fltt参数)
- `fltt=1`：返回整数（分），需要 `/100`
- `fltt=2`：返回小数（元），直接使用
```python
params = {"secids": secid_str, "fields": "f12,f14,f2,f3", "fltt": 2}  # 直接返回元
```

### 性能优化：并发获取净值
90只基金逐个获取太慢（每只需走代理），使用 ThreadPoolExecutor 并发：
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(fetch_single_nav, code): code for code in all_codes}
    try:
        for future in as_completed(futures, timeout=45):
            try:
                code, result = future.result(timeout=5)
                if result:
                    nav_data[code] = result
            except Exception:
                pass
    except TimeoutError:
        logger.warning(f"部分净值获取超时，已获取 {len(nav_data)} 只")
```
- `as_completed` 的 timeout 是总超时（45秒）
- `future.result()` 的 timeout 是单个超时（5秒）
- 不要用裸 `except:` 捕获，会吞掉有意义的异常信息

### 导入路径
`safe_get` 来自 `anti_crawl` 模块，**不是** `services.proxy_pool`：
```python
from anti_crawl import safe_get  # ✅ 正确
from anti_crawl import get_proxy_dict  # 获取代理配置
```

### ETF市场判断
```python
if code.startswith("5"):
    secid = f"1.{code}"  # 上海
else:
    secid = f"0.{code}"  # 深圳
```

## ⚠️ 关键Pitfall：修改标的列表时的元组解包

**问题**：`ARBITRAGE_TARGETS` 元组有5个字段 `(代码, 名称, 类型, 类别, 申购状态)`，但代码中多处解包。修改字段数量时必须**同步更新所有解包位置**。

**检查命令**：
```bash
grep -n "ARBITRAGE_TARGETS" api/arbitrage.py
# 确保所有解包都匹配元组字段数
```

**常见错误**：
```python
# ❌ 如果元组有5个字段，这样会报 "too many values to unpack"
for code, name, fund_type, category in ARBITRAGE_TARGETS:

# ✅ 正确写法
for code, name, fund_type, category, subscribe_status in ARBITRAGE_TARGETS:
# 或者用 _ 忽略不需要的字段
for code, *_ in ARBITRAGE_TARGETS:
```

**已知解包位置**（修改标的列表后必须检查）：
- `api/arbitrage.py` 第77行：`get_all_etf_prices()` 函数
- `api/arbitrage.py` 第131行：`api_arbitrage()` 函数的 `all_codes` 推导
- `api/arbitrage.py` 第146行：组装结果循环

## 扩展指南
添加新标的：编辑 `services/arbitrage_targets.py`，添加元组 `(代码, 名称, 类型, 类别, 申购状态)`
- `open` = 可正常申购
- `limit` = 限额申购（仍可套利，但金额受限）
- `closed` = 暂停申购（无法套利，显示为半透明）

⚠️ **修改标的列表后必须同步更新所有解包位置**（见上方关键Pitfall）

## 底层资产计算系统（2026-06-05 新增）

### 概述
参考 lof.i668.vip 实现，基于基金持仓和底层资产实时价格计算估算净值。

### 文件结构
```
services/
├── fund_holdings.py    # 基金持仓映射配置
├── asset_prices.py     # 底层资产价格获取
└── nav_calculator.py   # 估算净值计算
```

### fund_holdings.py - 持仓配置
```python
FUND_HOLDINGS = {
    "164701": {
        "name": "汇添富黄金及贵金属LOF",
        "benchmark": "黄金ETF",
        "holdings": [
            {"ticker": "GLD", "name": "SPDR Gold Trust", "weight": 0.49, "market": "US"},
            {"ticker": "IAU", "name": "iShares Gold Trust", "weight": 0.48, "market": "US"},
        ],
        "cash_weight": 0.03,
        "calc_method": "黄金ETF收盘涨跌（加权）+ COMEX黄金期货盘后变动",
        "futures_ticker": "GC",
    },
    # ... 23只基金
}
```

**配置字段说明：**
- `holdings`: 底层资产列表，`weight` 为权重（0-1）
- `market`: 资产市场（US=美股, HK=港股, SH=上海黄金）
- `futures_ticker`: 对应的期货代码（用于盘后变动计算）
- `is_etf`: 是否为场内ETF（影响溢价计算逻辑）

### asset_prices.py - 价格获取
**优先级：东财API → Yahoo Finance API（美股）**

```python
def get_us_stock_price(ticker):
    """获取美股实时价格（优先东财，备用Yahoo Finance）"""
    # 1. 先尝试东财API
    resp = _try_request(url, params=params, timeout=8)
    if resp and resp.status_code == 200:
        # 解析东财数据...
    
    # 2. 备用：Yahoo Finance API（可直连，无需代理）
    yahoo_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    resp = requests.get(yahoo_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
    # 解析Yahoo数据...
```

**Yahoo Finance API格式：**
```json
{
  "chart": {
    "result": [{
      "meta": {
        "regularMarketPrice": 740.61,
        "previousClose": 744.21
      }
    }]
  }
}
```

**⚠️ 重要：Yahoo Finance可直连，不需要代理！** 在WSL环境下东财API需要代理，但Yahoo Finance可以直连。

### nav_calculator.py - 净值计算
```python
def calculate_estimated_nav(code):
    """计算基金估算净值"""
    config = get_fund_config(code)
    base_nav_info = get_base_nav(code)  # 从天天基金获取基准净值
    
    # 获取持仓资产价格
    holdings = config.get("holdings", [])
    prices = get_batch_prices([(h["ticker"], h["market"]) for h in holdings])
    
    # 计算持仓收益
    total_weighted_return = 0
    for holding in holdings:
        change_pct = price_info.get("change_pct", 0)
        contribution = weight * change_pct  # ⚠️ change_pct已是百分比，不要再除100
        total_weighted_return += contribution
    
    # 计算期货收益（如果有）
    futures_return = us_weight * futures_change  # 同样不要除100
    
    # 估算净值 = 基准净值 × (1 + 总收益率)
    estimated_nav = base_nav * (1 + total_return / 100)
```

**⚠️ 关键计算公式：**
```
持仓收益 = Σ(权重 × 涨跌幅)  # 涨跌幅已是百分比，如 -0.48 表示 -0.48%
期货收益 = 美股持仓权重 × 期货涨跌幅
总收益 = 持仓收益 + 期货收益
估算净值 = 基准净值 × (1 + 总收益 / 100)
```

**⚠️ 常见错误：change_pct已经是百分比！**
```python
# ❌ 错误：多除了100
contribution = weight * change_pct / 100

# ✅ 正确：change_pct已经是百分比（如 -0.48 表示 -0.48%）
contribution = weight * change_pct
```

### API端点
```
GET /api/arbitrage              - 套利数据列表
GET /api/arbitrage/detail/<code> - 单只基金详细计算过程
```

**详情API返回结构：**
```json
{
  "code": "513100",
  "name": "纳指ETF",
  "price": 2.205,
  "estimated_nav": 2.0807,
  "premium_rate": 5.97,
  "base_nav": 2.0808,
  "nav_date": "2026-06-03",
  "total_return": -0.4704,
  "holdings_return": -0.4704,
  "futures_return": 0,
  "calc_details": [
    {
      "ticker": "QQQ",
      "name": "Invesco QQQ Trust",
      "weight": 0.98,
      "change_pct": -0.48,
      "contribution": -0.4704,
      "price": 740.61,
      "prev_close": 744.21
    }
  ],
  "futures_detail": null,
  "method": "纳指ETF收盘涨跌 + 纳指期货盘后变动",
  "cash_weight": 0.02
}
```

### 前端详情弹窗
点击卡片弹出详情，展示：
1. **溢价率大字**（48px）
2. **三列对比**：场内价格 / 估算净值 / 基准净值
3. **持仓明细表格**：代码、名称、权重、涨跌幅、贡献度
4. **期货盘后变动**：期货代码、价格、涨跌幅、加权贡献
5. **计算公式**：完整展示计算过程

### 已配置的基金（23只）
| 类别 | 基金 | 底层资产 |
|------|------|----------|
| 黄金 | 164701, 160719, 518880, 159934 | GLD, IAU |
| 白银 | 161226 | SLV |
| 原油 | 160216, 501018, 162719, 162411 | USO, BNO, XLE, XOP |
| 美股 | 161125, 161128, 161129, 161130 | SPY, XLV, XLK, XLP |
| 纳指 | 160213, 513100, 513300 | QQQ |
| 标普 | 513500, 159612 | SPY |
| 港股 | 164705, 513050, 513180 | 2800.HK, KWEB, 3032.HK |
| 日本 | 513520, 159866 | EWJ |
| 欧洲 | 513030 | EWG |

### 与 lof.i668.vip 对比
| 功能 | lof.i668.vip | 我们 |
|------|-------------|------|
| 基金数量 | 6只 | 44只（23只有持仓配置） |
| 美股价格 | ✅ | ✅（东财+Yahoo双源） |
| 期货价格 | ✅ | ⚠️（仅GC/SI，NQ/ES无数据） |
| 计算公式 | ✅ | ✅ |
| 前端展示 | ✅ | ✅（卡片+详情弹窗） |
