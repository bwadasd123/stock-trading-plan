# K线数据与指标计算陷阱

## ⚠️ 关键问题：smplmt参数 (2026-06-09发现)

### 问题描述
东财API的 `smplmt` 参数会导致返回**采样后的稀疏数据**，而不是完整的日线数据。

**错误示例**（de3.py中的配置）：
```python
"KLINE_SMPLMT": 460,  # ❌ 这会导致数据被采样！
```

**影响**：
- 返回的K线数据约20天一根，不是每日数据
- MA、RSI、MACD、CCI等指标全部基于错误数据计算
- 扫描结果严重失真

**修复方案**：去掉 `smplmt` 参数，只使用 `lmt` 控制返回数量

```python
# ✅ 正确的参数
params = {
    "secid": secid,
    "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    "fields1": "f1,f2,f3,f4,f5,f6",
    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    "klt": period,
    "fqt": 1,
    "beg": 0,
    "end": 20500101,
    # 注意: 不能使用smplmt参数！
    "lmt": limit,
    "_": int(time.time() * 1000) + 1
}
```

**验证方法**：
```python
# 检查K线数据是否连续
klines = get_kline_data('600519', '101', 30)
dates = [k['date'] for k in klines[-5:]]
# 应该是连续的交易日，如：6/3, 6/4, 6/5, 6/8, 6/9
# 如果间隔约20天，说明数据被采样了
```

### 问题根源确认 (2026-06-09)
- 直接请求东财API（不通过代理）也会返回采样数据
- 问题在API参数，不在代理
- de3.py本身也有这个问题，说明历史扫描记录的指标值都是基于错误数据

---

## 量比计算 (2026-06-09)

### 用户决策：跟随 de3.py 逻辑
用户明确要求量比计算跟随 de3.py 的逻辑，使用 **"今日/昨日"** 而非标准的"今日/5日均量"。

**当前实现（跟随 de3.py）**：
```python
vol_ratio = float(v.iloc[-1] / v.iloc[-2]) if v.iloc[-2] > 0 else 0
```

**注意**：标准定义是"今日/5日均量"，但用户选择跟随 de3.py。不要擅自修改。

---

## RSI计算方式

### SMA vs EMA
- **de3.py和当前系统**：使用SMA（简单移动平均）
- **通达信**：使用EMA（指数移动平均）
- **差异**：约6点（如RSI SMA=37.1, EMA=30.7）
- **结论**：趋势方向一致，数值略有差异，可接受

```python
# SMA方式（当前使用，跟随 de3.py）
delta = c.diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss.replace(0, np.nan)
rsi = 100 - (100 / (1 + rs))
```

---

## de3.py 参考文件

用户提供的 7 指标扫描逻辑参考实现：
- **Windows路径**: `C:\Users\Administrator\Downloads\Telegram Desktop\de3.py`
- **WSL路径**: `/mnt/c/Users/Administrator/Downloads/Telegram Desktop/de3.py`

所有指标计算必须与 de3.py 保持一致，除非用户明确要求修改。

---

## 回撤测试方法 (2026-06-09)

用户要求用历史扫描记录验证指标计算逻辑的正确性。

### 测试步骤
1. 查询数据库中的历史扫描记录
2. 选取几只典型股票
3. 用当前系统的逻辑重新计算它们在扫描当天的指标
4. 对比计算结果是否与数据库中记录的一致

### 注意事项
- 历史记录是用老版本（smplmt=460）扫描的，指标值基于采样数据
- 当前系统用完整日线计算，结果自然不同
- 两者不可直接对比，但可以验证当前系统的计算逻辑是否自洽

### 回撤测试结果 (2026-06-09)

**老版本逻辑（smplmt=460）vs 新版本逻辑（日线）：**

| 测试 | 通过率 | 说明 |
|------|--------|------|
| 老版本逻辑（smplmt=460） | 8/10 (80%) | 采样数据，信号时间不精确 |
| 新版本逻辑（日线） | 4/10 (40%) | 连续日线，信号精确 |

**失败原因分析：**
- MACD金叉不通过：采样数据跳过了金叉发生的当天
- 量比≥1.5不通过：采样数据的成交量是某一天的快照，不是扫描当天

**典型案例：**
- 银禧科技(300221)：扫描5月14日，采样数据跳到5月8日（换手率4.09% vs 当天18.29%）
- 汉邦高科(300449)：扫描5月13日，采样数据跳到5月11日（换手率2.20% vs 当天35.95%）

**结论：**
- 老版本的采样逻辑会导致信号触发时间不精确
- 当前系统的日线逻辑更准确，但历史记录不可直接对比
- 新旧扫描结果的指标值会不同，这是正常的

### 东财API限流
批量请求东财API时会被限流（RemoteDisconnected错误）。需要在请求之间添加延迟：
```python
time.sleep(0.5)  # 每次请求后等待0.5秒
```

```python
# 回撤测试示例
# 1. 获取K线数据
df = get_kline_data(code, 500)

# 2. 找到扫描日期对应的K线位置
date_idx = df[df['date'] == scan_date].index
idx = date_idx[0]

# 3. 截取到扫描日期为止的数据
df_slice = df.iloc[:idx+1]

# 4. 计算指标
rsi = calculate_rsi(df_slice['close'], 14)
cci = calculate_cci(df_slice['high'], df_slice['low'], df_slice['close'], 20)
# ...
```

---

## 双版本对比系统 (2026-06-09)

为了对比老版本（smplmt=460采样）和新版本（日线）的扫描逻辑差异，创建了一个双版本对比系统。

### ⚠️ Python全局变量陷阱（重要！）

在双版本对比系统中遇到了一个关键bug：`api/dual_scan.py` 直接导入了 `scanner_dual.py` 中的全局变量：

```python
# ❌ 错误方式 - 导入创建的是本地绑定
from services.scanner_dual import SCAN_STATE_OLD, SCAN_STATE_NEW
# 当 scanner_dual.py 重新赋值 SCAN_STATE_OLD = new_state 时
# 这里的 SCAN_STATE_OLD 仍然指向旧对象！

# ✅ 正确方式 - 通过模块引用访问
import services.scanner_dual as scanner_dual
# 使用 scanner_dual.SCAN_STATE_OLD 时总是获取最新值
```

**症状**：API返回的 scan_id 为空，因为前端获取的是导入时的旧对象引用。

**修复**：所有需要访问 scanner_dual 模块变量的地方，都使用 `import services.scanner_dual as scanner_dual` + `scanner_dual.VAR_NAME`。

### 文件结构
```
/home/jmy/stock-screener/
├── services/scanner_dual.py      # 双版本扫描服务
├── api/dual_scan.py              # 双版本扫描API（必须用模块引用方式）
├── static/js/dual_scan.js        # 前端JavaScript
├── static/css/dual_scan.css      # 前端样式
└── DUAL_SCAN_README.md           # 使用说明
```

### 功能特性
1. **同时运行**：老版本和新版本扫描同时进行
2. **实时进度**：通过SSE实时显示两个版本的扫描进度
3. **结果对比**：显示两个版本通过的股票，高亮差异
4. **数据存储**：两个版本的结果都保存到数据库

### API接口
- `POST /api/dual_scan_all` - 启动双版本扫描
- `GET /api/dual_scan_progress` - 获取扫描进度（SSE）
- `GET /api/dual_scan_results` - 获取扫描结果
- `POST /api/dual_scan_stop` - 停止扫描

### 使用方法
1. 启动Flask应用：`python app.py`
2. 访问：http://localhost:8080
3. 点击左侧导航栏的 "🔄 双版本对比"
4. 设置筛选条件
5. 点击 "🚀 启动双版本扫描"
6. 等待扫描完成，查看对比结果

### 数据库表
扫描结果保存在 `stock_scan_results` 表中：
- 老版本：scan_id 以 `_old` 结尾
- 新版本：scan_id 以 `_new` 结尾

---

## 东财API限流问题 (2026-06-09)

批量请求东财API时会被限流，出现 `RemoteDisconnected` 错误。

### 解决方案
1. **添加请求延迟**：每次请求后等待 0.5-1 秒
2. **重试机制**：遇到连接错误时重试 3 次
3. **使用代理池**：通过代理池分散请求

```python
# 示例：带重试的请求
def get_kline_data_with_retry(code, limit=500, max_retries=3):
    for retry in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            return resp.json()
        except Exception as e:
            if retry < max_retries - 1:
                time.sleep(2)
            else:
                raise e
```

---

## 正确的指标计算方式（跟随 de3.py）

| 指标 | 计算方式 | 备注 |
|------|----------|------|
| MA5/10/20 | `series.rolling(window).mean()` | 标准 |
| RSI(14) | SMA方式 | 与通达信有~6点差异，跟随 de3.py |
| MACD(12,26,9) | EMA方式 | 标准 |
| CCI(20) | 标准CCI公式 | 标准 |
| 量比 | 今日/昨日 | 跟随 de3.py，非标准定义 |

---

## 7个筛选条件（用户确认版 2026-06-09）

用户明确确认的7个筛选条件：

1. **流通市值≤200亿**
2. **MACD金叉**
3. **股价>20日均线**
4. **今日成交量>前一天1.5倍**（量比 = 今日/昨日）
5. **换手率>10%**
6. **CCI>0**
7. **RSI>70**

**注意**：量比定义是"今日/昨日"，不是标准的"今日/5日均量"。用户明确要求跟随 de3.py 逻辑。
