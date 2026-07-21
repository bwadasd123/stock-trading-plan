#!/usr/bin/env python3
"""015690 基金估值 → 企微推送（v3: 东财API + 净值变化追踪）"""
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

def get_fund_data():
    url = "https://api.fund.eastmoney.com/f10/lsjz?fundCode=015690&pageIndex=1&pageSize=3"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://fund.eastmoney.com/f10/jjjz_015690.html"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        items = data.get("Data", {}).get("LSJZList", [])
        return items
    except: return []

# 获取数据
items = get_fund_data()
if not items:
    exit(0)

now = datetime.datetime.now()
state = load_state()

# 最新净值
latest = items[0]
dwjz = float(latest.get("DWJZ", 0))
jzrq = latest.get("FSRQ", "N/A")
jzzzl = float(latest.get("JZZZL", 0))

# 计算盈亏
today_value = FUND_SHARES * dwjz
total_pnl = today_value - TOTAL_INVEST
pnl_pct = (dwjz / COST_NAV - 1) * 100

# ========== 净值变化追踪 ==========
change_msg = ""
prev_nav = state.get("last_nav")
prev_date = state.get("last_date")

if prev_nav and prev_date and jzrq != prev_date:
    nav_change = dwjz - prev_nav
    nav_change_pct = (dwjz / prev_nav - 1) * 100
    change_msg = f"\n📉 净值变动（{prev_date}→{jzrq}）: {nav_change:+.4f} ({nav_change_pct:+.2f}%)"

# 5日净值趋势
trend_msg = ""
if len(items) >= 5:
    recent = [float(i["DWJZ"]) for i in items[:5]]
    chg5 = (recent[0] / recent[4] - 1) * 100
    trend_msg = f"\n📊 近5日: {chg5:+.1f}%  [{recent[0]:.4f} ← {recent[4]:.4f}]"

# ========== 推送 ==========
hour, minute = now.hour, now.minute
if hour == 11 and minute >= 30: title = "⏸️ 午间休市"
elif hour == 13 and minute <= 5: title = "🔔 下午开盘"
elif hour == 14 and minute >= 30: title = "⏳ 尾盘30分钟"
elif hour >= 15: title = "📊 收盘确认"
else: title = "📊 基金估值"

msg = f"{title} — 015690 富国中小盘\n"
msg += f"\n📅 {jzrq}  净值 {dwjz:.4f} ({jzzzl:+.2f}%)"
msg += f"\n📊 {FUND_SHARES:.0f}份 × 成本{COST_NAV:.4f}"
msg += f"\n💰 市值 {today_value:,.0f}  盈亏 {total_pnl:+,.0f} ({pnl_pct:+.1f}%)"
msg += f"\n🔁 回本需 {COST_NAV:.4f} (+{(COST_NAV/dwjz-1)*100:.1f}%)"

if change_msg:
    msg += change_msg
if trend_msg:
    msg += trend_msg

send_wx(msg)

# 保存状态
state["last_nav"] = dwjz
state["last_date"] = jzrq
save_state(state)
