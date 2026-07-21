#!/usr/bin/env python3
"""015690 基金估值 → 企微推送（修复：旧API已301，换东财官方API）"""
import urllib.request, json, os, datetime

def load_env():
    env_paths = [
        "/home/jmy/.hermes/profiles/eastmoney-bot/.env",
        ".env",
    ]
    for env_path in env_paths:
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
TOTAL_INVEST = 22500        # 累计投入（含7/17加仓）
FUND_SHARES = 2912.9        # 份额
COST_NAV = 7.7242           # 加权成本

def send_wx(msg):
    if not WX_WEBHOOK:
        return
    data = json.dumps({"msgtype": "text", "text": {"content": msg}}).encode()
    req = urllib.request.Request(WX_WEBHOOK, data=data,
        headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except:
        pass

def get_fund_data():
    """从东财API获取最新净值"""
    url = "https://api.fund.eastmoney.com/f10/lsjz?fundCode=015690&pageIndex=1&pageSize=2"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://fund.eastmoney.com/f10/jjjz_015690.html"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        items = data.get("Data", {}).get("LSJZList", [])
        if items:
            return items[0], items[1] if len(items) > 1 else None
    except Exception as e:
        pass
    return None, None

def get_valuation():
    """尝试获取盘中估值（可能不可用）"""
    url = "https://api.fund.eastmoney.com/f10/FundEstimateData?fundCode=015690"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://fund.eastmoney.com/015690.html"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        est = data.get("Data", {})
        if est:
            return est.get("gsz"), est.get("gszzl")
    except:
        pass
    return None, None

# 获取数据
latest, prev = get_fund_data()
gsz, gszzl = get_valuation()

if not latest:
    exit(0)

now = datetime.datetime.now()

# 净值数据
dwjz = latest.get("DWJZ", "N/A")
jzrq = latest.get("FSRQ", "N/A")
jzzzl = latest.get("JZZZL", "N/A")

# 估值
if gsz:
    est_nav = gsz
    est_chg = gszzl if gszzl else "N/A"
else:
    # 用昨日净值+涨幅估算
    try:
        est_nav = float(dwjz) * (1 + float(jzzzl.replace("%","")) / 100)
        est_chg = "估算"
    except:
        est_nav = dwjz
        est_chg = "N/A"

# 计算盈亏
try:
    dwjz_val = float(dwjz)
    today_value = FUND_SHARES * dwjz_val
    total_pnl = today_value - TOTAL_INVEST
    cost_value = FUND_SHARES * COST_NAV
    pnl_pct = (dwjz_val / COST_NAV - 1) * 100
except:
    total_pnl = 0
    pnl_pct = 0

# 判断推送类型
hour = now.hour
minute = now.minute

if hour == 11 and minute >= 30:
    title = "⏸️ 午间休市"
elif hour == 13 and minute == 0:
    title = "🔔 下午开盘"
elif hour == 14 and minute >= 30:
    title = "⏳ 尾盘30分钟"
elif hour >= 15:
    title = "📊 收盘确认"
else:
    title = "📊 基金估值"

# 构建消息
msg = f"{title} — 015690 富国中小盘\n"
msg += f"\n📅 净值日期: {jzrq}"
msg += f"\n📌 单位净值: {dwjz}  ({jzzzl}%)"
msg += f"\n📊 持仓 {FUND_SHARES:.0f}份 × 成本{COST_NAV:.4f}"
msg += f"\n💰 当前市值: {today_value:,.2f}"
msg += f"\n   累计盈亏: {total_pnl:+,.2f} ({pnl_pct:+.1f}%)"

send_wx(msg)
