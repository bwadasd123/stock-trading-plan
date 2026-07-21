#!/usr/bin/env python3
"""015690 基金估值 → 企微推送（v5: 按季报权重加权估算）"""
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

# 最新季报前10大重仓股（权重% → 归一化到88%总仓位）
HOLDINGS_RAW = [
    ("0.002384", "东山精密", 9.33),
    ("0.300502", "新易盛", 8.06),
    ("0.300308", "中际旭创", 6.58),
    ("0.002916", "深南电路", 5.92),
    ("1.688347", "华虹公司", 5.86),
    ("0.002463", "沪电股份", 5.21),
    ("1.603986", "兆易创新", 4.76),
    ("0.000657", "中钨高新", 3.63),
    ("0.002436", "兴森科技", 3.40),
    ("0.002938", "鹏鼎控股", 2.91),
]
TOTAL_WEIGHT = sum(w for _,_,w in HOLDINGS_RAW)  # 55.66%
STOCK_RATIO = 0.88  # 股票总仓位

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
    secids = ",".join(s for s,_,_ in HOLDINGS_RAW)
    url = f"http://push2delay.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f14&secids={secids}"
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        items = json.loads(resp.read()).get("data", {}).get("diff", [])
        # 按secid索引
        return {i.get("f12",""): i for i in items}
    except: return {}

def get_latest_nav():
    url = "https://api.fund.eastmoney.com/f10/lsjz?fundCode=015690&pageIndex=1&pageSize=5"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0", "Referer": "https://fund.eastmoney.com/"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        items = json.loads(resp.read()).get("Data", {}).get("LSJZList", [])
        return items
    except: return []

# 获取数据
prices = get_holding_prices()
nav_items = get_latest_nav()
if not nav_items: exit(0)

now = datetime.datetime.now()
state = load_state()
latest = nav_items[0]
dwjz = float(latest.get("DWJZ", 0))
jzrq = latest.get("FSRQ", "N/A")

# 加权估算
weighted_chg = 0
holding_details = []
for secid, name, weight in HOLDINGS_RAW:
    code = secid.split(".")[1]  # "0.002384" → "002384"
    info = prices.get(code, {})
    chg = info.get("f3", 0)
    contrib = weight * chg / 100  # 对基金的贡献
    weighted_chg += contrib
    holding_details.append((name, weight, chg, contrib))

# 归一化：top10占55.66%，剩余仓位(88-55.66)=32.34%用等权估计
remaining_ratio = STOCK_RATIO * 100 - TOTAL_WEIGHT
if remaining_ratio > 0:
    remaining_chg = sum(d[2] for d in holding_details) / len(holding_details)  # 平均涨跌
    weighted_chg += remaining_chg * remaining_ratio / 100

est_nav = dwjz * (1 + weighted_chg / 100)

# 计算盈亏
today_value = FUND_SHARES * est_nav
total_pnl = today_value - TOTAL_INVEST
yesterday_value = FUND_SHARES * dwjz
today_pnl = today_value - yesterday_value

# 净值变化追踪
change_msg = ""
prev_nav = state.get("last_nav"); prev_date = state.get("last_date")
if prev_nav and prev_date and jzrq != prev_date:
    nc = dwjz - prev_nav; ncp = (dwjz/prev_nav-1)*100
    change_msg = f"\n📉 净值变动: {nc:+.4f} ({ncp:+.2f}%)"

trend_msg = ""
if len(nav_items) >= 5:
    recent = [float(i["DWJZ"]) for i in nav_items[:5]]
    chg5 = (recent[0]/recent[4]-1)*100
    trend_msg = f"\n📊 近5日: {chg5:+.1f}%"

# 推送标题
hour, minute = now.hour, now.minute
if hour == 11 and minute >= 30: title = "⏸️ 午间休市"
elif hour == 13 and minute <= 5: title = "🔔 下午开盘"
elif hour == 14 and minute >= 30: title = "⏳ 尾盘30分钟"
elif hour >= 15: title = "📊 收盘确认"
else: title = "📊 基金估值"

msg = f"{title} — 015690 富国中小盘\n"
msg += f"\n📅 {jzrq} 净值 {dwjz:.4f}"
msg += f"\n📈 今日估算 {est_nav:.4f} ({weighted_chg:+.2f}%)"
msg += f"\n💰 {FUND_SHARES:.0f}份  市值 {today_value:,.0f}"
msg += f"\n   盈亏 {total_pnl:+,.0f}  今日 {today_pnl:+,.0f}"
msg += f"\n🔁 回本需 {COST_NAV:.4f}"

if change_msg: msg += change_msg
if trend_msg: msg += trend_msg

# 持仓明细（按权重排序）
msg += f"\n\n📋 重仓股（权重→贡献）:"
for name, weight, chg, contrib in sorted(holding_details, key=lambda x: x[1], reverse=True):
    bar = "🟢" if chg > 3 else ("🔴" if chg < -3 else "⚪")
    msg += f"\n   {bar} {name} {weight:.1f}%  {chg:+.1f}%"

send_wx(msg)
state["last_nav"] = dwjz; state["last_date"] = jzrq
save_state(state)
