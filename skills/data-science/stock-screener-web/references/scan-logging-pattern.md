# Scan Logging Pattern for User Verification

When user suspects scan calculations are wrong, add detailed foreground logs showing per-stock analysis.

## User Feedback

"我希望你再扫描的时候把日志过程放在前台可以吗？比对计算过程，我现在总感觉你计算的都不对"

## Implementation

### Round 1: Log filtered-out stocks with reasons

```python
# In services/scanner.py, Round 1 filter section
filtered_out = []
for s in stocks:
    ok = True
    reasons = []
    
    # 涨幅 > 0
    if filters.get("r1_change_gt0") and s["change_pct"] <= 0:
        ok = False
        reasons.append(f"涨幅{s['change_pct']:.2f}%≤0")
    
    # 换手率 > 阈值（只有当值 > 0 时才生效）
    turnover_min = filters.get("r1_turnover", 0)
    if turnover_min > 0 and s["turnover"] < turnover_min:
        ok = False
        reasons.append(f"换手率{s['turnover']:.2f}%<{turnover_min}%")
    
    # 成交额 > 阈值
    amount_min = filters.get("r1_amount", 0)
    if amount_min > 0 and s["amount"] < amount_min * 1e8:
        ok = False
        reasons.append(f"成交额{s['amount']/1e8:.2f}亿<{amount_min}亿")
    
    # PE > 0
    if filters.get("r1_pe_gt0") and s["pe"] <= 0:
        ok = False
        reasons.append(f"PE={s['pe']:.2f}≤0")
    
    # 流通市值 ≤ 阈值
    cap_max = filters.get("r1_cap_max", 9999)
    if cap_max < 9999 and s["circ_cap"] > cap_max:
        ok = False
        reasons.append(f"市值{s['circ_cap']:.2f}亿>{cap_max}亿")
    
    if ok:
        round1.append(s)
    else:
        filtered_out.append(f"{s['name']}({s['code']}): {', '.join(reasons)}")

logger.info(f"  第一轮筛选: {len(stocks)} → {len(round1)}只")
if filtered_out:
    for msg in filtered_out[:5]:
        logger.info(f"    ❌ {msg}")
    if len(filtered_out) > 5:
        logger.info(f"    ... 还有 {len(filtered_out) - 5} 只被过滤")
```

### Round 2: Log pass/fail with indicator values

```python
# In services/scanner.py, Round 2 filter section
ok = True
reasons = []

r2_rsi = filters.get("r2_rsi", 0)
if r2_rsi > 0 and ind.get("rsi", 0) < r2_rsi:
    ok = False
    reasons.append(f"RSI={ind.get('rsi', 0):.1f}<{r2_rsi}")

if filters.get("r2_macd") and not ind.get("macd_gold"):
    ok = False
    reasons.append("无MACD金叉")

if filters.get("r2_cci") and ind.get("cci", 0) <= 0:
    ok = False
    reasons.append(f"CCI={ind.get('cci', 0):.1f}≤0")

if filters.get("r2_ma20") and s["price"] <= ind.get("ma20", 0):
    ok = False
    reasons.append(f"价格{s['price']:.2f}≤MA20={ind.get('ma20', 0):.2f}")

r2_vol = filters.get("r2_vol_ratio", 0)
if r2_vol > 0 and ind.get("vol_ratio", 0) < r2_vol:
    ok = False
    reasons.append(f"量比={ind.get('vol_ratio', 0):.2f}<{r2_vol}")

r2_turn = filters.get("r2_turnover", 0)
if r2_turn > 0 and s["turnover"] < r2_turn:
    ok = False
    reasons.append(f"换手率={s['turnover']:.2f}%<{r2_turn}%")

s["pass"] = ok
results.append(s)

if ok:
    logger.info(f"    ✅ {s['name']}({s['code']}) 通过! RSI={ind.get('rsi',0):.1f} CCI={ind.get('cci',0):.1f} MACD金叉={'是' if ind.get('macd_gold') else '否'}")
else:
    logger.info(f"    ❌ {s['name']}({s['code']}) 不通过: {', '.join(reasons)}")
```

## Key Points

1. **Limit Round 1 logs to 5** - Avoid log spam when many stocks filtered
2. **Show ALL Round 2 logs** - Each stock requires API call, user wants to see each one
3. **Include actual values** - Not just pass/fail, but the calculated values for verification
4. **Use emoji indicators** - ✅ for pass, ❌ for fail for quick visual scanning

## 双版本扫描日志模式（scanner_dual.py）

双版本扫描需要**版本标注**，日志中用 `[老版本]` / `[新版本]` 前缀区分。

### 扫描开始 — 显示筛选条件

```python
logger.info(f"🚀 双版本扫描开始: {scan_id_base}")
logger.info(f"  📊 筛选条件:")
logger.info(f"    第一轮: 换手率>{filters.get('r1_turnover', 0)}%, 流通市值≤{filters.get('r1_cap_max', 9999)}亿")
r2_conditions = []
if filters.get('r2_rsi', 0) > 0: r2_conditions.append(f"RSI>{filters['r2_rsi']}")
if filters.get('r2_macd'): r2_conditions.append("MACD金叉")
if filters.get('r2_cci'): r2_conditions.append("CCI>0")
if filters.get('r2_ma20'): r2_conditions.append("价格>MA20")
if filters.get('r2_vol_ratio', 0) > 0: r2_conditions.append(f"量比>{filters['r2_vol_ratio']}")
if filters.get('r2_turnover', 0) > 0: r2_conditions.append(f"换手率>{filters['r2_turnover']}%")
logger.info(f"    第二轮: {', '.join(r2_conditions) if r2_conditions else '无'}")
logger.info(f"  📈 版本说明:")
logger.info(f"    老版本: 使用smplmt=460参数获取K线")
logger.info(f"    新版本: 使用完整日线数据获取K线")
```

### 每只股票 — 带版本标签的指标日志

```python
# 老版本
if ok_old:
    logger.info(f"    ✅ [老版本] {s['name']}({s['code']}) 通过! RSI={rsi:.1f} CCI={cci:.1f} MACD金叉={macd_gold} 量比={vol_ratio:.2f} MA20={ma20:.2f}")
else:
    logger.info(f"    ❌ [老版本] {s['name']}({s['code']}) 不通过: {', '.join(reasons_old)} | RSI={rsi:.1f} CCI={cci:.1f} MACD金叉={macd_gold}")

# 新版本
if ok_new:
    logger.info(f"    ✅ [新版本] {s['name']}({s['code']}) 通过! RSI={rsi:.1f} CCI={cci:.1f} MACD金叉={macd_gold} 量比={vol_ratio:.2f} MA20={ma20:.2f}")
else:
    logger.info(f"    ❌ [新版本] {s['name']}({s['code']}) 不通过: {', '.join(reasons_new)} | RSI={rsi:.1f} CCI={cci:.1f} MACD金叉={macd_gold}")

# K线数据不足
if kline_old_count < 20:
    logger.info(f"    ⚠️ [老版本] {s['name']}({s['code']}) K线数据不足: {kline_old_count}根 (需要≥20)")
```

### 扫描结束 — 汇总统计

```python
logger.info(f"")
logger.info(f"{'='*60}")
logger.info(f"📊 双版本扫描结果汇总")
logger.info(f"{'='*60}")
logger.info(f"  扫描ID: {scan_id_base}")
logger.info(f"  耗时: {int(duration)}秒")
logger.info(f"  扫描股票总数: {total_scanned}只")
logger.info(f"")
logger.info(f"  📈 老版本 (smplmt=460):")
logger.info(f"    分析股票: {len(results_old)}只")
logger.info(f"    通过筛选: {total_passed_old}只")
passed_old = [r for r in results_old if r.get('pass')]
if passed_old:
    logger.info(f"    通过列表:")
    for r in passed_old:
        logger.info(f"      ✅ {r['name']}({r['code']}) RSI={r.get('rsi',0):.1f} CCI={r.get('cci',0):.1f}")
# 同样输出新版本...
```

**为什么需要版本标注**：双版本同时运行，日志交织在一起。没有 `[老版本]`/`[新版本]` 前缀的话，用户无法区分哪条日志属于哪个版本。
