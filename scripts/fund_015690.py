#!/usr/bin/env python3
"""015690 基金估值 → 企微推送（v4: 基于持仓股实时估算）"""
import urllib.request, json, os, datetime

def load_env():
    for env_path in ["/home/jmy/.hermes/profiles/eastmoney-bot/.env", ".env"]:
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            break

load_env()
WX_WEBHOOK = os.environ.get("WX_WEBHOOK", "")
STATE_FILE = "/home/jmy/.hermes/profiles/eastmoney-bot/.fund_state.json"
os.environ['NO_PROXY'] = '*'

# ========== 持仓配置 ==========
TOTAL_INVEST = 22500
FUND_SHARES = 2912.9
COST_NAV = 7.7242

# 重仓股（来自 pingzhongdata/015690.js + 688347）
HOLDINGS = [
    "0.300502",  # 新易盛
    "0.002384",  # 东山精密
    "0.002916",  # 深南电路
    "0.300308",  # 中际旭创
    "0.002027",  # 分众传媒
    "1.601869",  # 长飞光纤
    "1.688052",  # 纳芯微
    "0.002463",  # 沪电股份
    "1.600498",  # 烽火通信
    "1.688205",  # 德科立
    "1.688347",  # 华虹公司
]
STOCK_RATIO = 0.88  # 股票仓位约88%（等权估算，实际权重按季报）

def send_wx(msg):
    if not WX_WEBHOOK: return
    data = json.dumps({"msgtype": "text", "text": {"content": msg}}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(WX_WEBHOOK, data=data,
            headers={"Content-Type": "application/json"}), timeout=5)
    except: pass

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f: return json.load(f)
    return {}

def save_state(s):
    with open(STATE_FILE, 'w') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def get_holding_prices():
    """获取重仓股实时涨跌"""
    secids = ",".join(HOLDINGS)
    url = f"http://push2delay.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f14&secids={secids}"
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        return json.loads(resp.read()).get("data", {}).get("diff", [])
    except: return []

def get_latest_nav():
    """获取最新确认净值"""
    url = "https://api.fund.eastmoney.com/f10/lsjz?fundCode=015690&pageIndex=1&pageSize=5"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://fund.eastmoney.com/"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        items = json.loads(resp.read()).get("Data", {}).get("LSJZList", [])
        return items
    except: return []

# 获取数据
holdings = get_holding_prices()
nav_items = get_latest_nav()

if not nav_items:
    exit(0)

now = datetime.datetime.now()
state = load_state()

# 最新净值
latest = nav_items[0]
dwjz = float(latest.get("DWJZ", 0))
jzrq = latest.get("FSRQ", "N/A")
jzzzl = float(latest.get("JZZZL", 0))

# 基于持仓估算今日净值
est_nav = dwjz
est_chg = 0
if holdings and len(holdings) > 0:
    avg_pct = sum(h.get("f3", 0) for h in holdings) / len(holdings)
    est_chg = avg_pct * STOCK_RATIO
    est_nav = dwjz * (1 + est_chg / 100)

# 计算盈亏
today_value = FUND_SHARES * est_nav
total_pnl = today_value - TOTAL_INVEST
pnl_pct = (est_nav / COST_NAV - 1) * 100

# 今日回血
yesterday_value = FUND_SHARES * dwjz
today_pnl = today_value - yesterday_value

# 净值变化追踪
change_msg = ""
prev_nav = state.get("last_nav")
prev_date = state.get("last_date")
if prev_nav and prev_date and jzrq != prev_date:
    nav_change = dwjz - prev_nav
    nav_change_pct = (dwjz / prev_nav - 1) * 100
    change_msg = f"\n📉 净值变动（{prev_date}→{jzrq}）: {nav_change:+.4f} ({nav_change_pct:+.2f}%)"

# 近5日趋势
trend_msg = ""
if len(nav_items) >= 5:
    recent = [float(i["DWJZ"]) for i in nav_items[:5]]
    chg5 = (recent[0] / recent[4] - 1) * 100
    trend_msg = f"\n📊 近5日净值: {chg5:+.1f}%"

# ========== 推送 ==========
hour, minute = now.hour, now.minute
if hour == 11 and minute >= 30: title = "⏸️ 午间休市"
elif hour == 13 and minute <= 5: title = "🔔 下午开盘"
elif hour == 14 and minute >= 30: title = "⏳ 尾盘30分钟"
elif hour >= 15: title = "📊 收盘确认"
else: title = "📊 基金估值"

msg = f"{title} — 015690 富国中小盘\n"
msg += f"\n📅 {jzrq}  确认净值 {dwjz:.4f} ({jzzzl:+.2f}%)"
msg += f"\n📈 今日估算 {est_nav:.4f} ({est_chg:+.2f}%)  ← 持仓加权"
msg += f"\n📊 {FUND_SHARES:.0f}份 × 成本{COST_NAV:.4f}"
msg += f"\n💰 市值 {today_value:,.0f}  盈亏 {total_pnl:+,.0f} ({pnl_pct:+.1f}%)"
if today_pnl != 0:
    msg += f"\n💹 今日回血 {today_pnl:+,.0f}"
msg += f"\n🔁 回本需 {COST_NAV:.4f} (+{(COST_NAV/est_nav-1)*100:.1f}%)"

if change_msg: msg += change_msg
if trend_msg: msg += trend_msg

# 持仓明细（折叠）
msg += f"\n\n📋 重仓股今日:"
for h in holdings:
    msg += f"\n   {h.get('f14','?')}: {h.get('f3',0):+.1f}%"

send_wx(msg)

# 保存状态
state["last_nav"] = dwjz
state["last_date"] = jzrq
save_state(state)
