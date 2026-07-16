#!/usr/bin/env python3
"""015690 基金估值 → 企微推送（含偏差追踪）"""
import urllib.request, json, re, os, datetime

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

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# 获取基金数据
url = "https://fundgz.1234567.com.cn/js/015690.js"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=10)
raw = resp.read().decode("utf-8")

match = re.search(r'jsonpgz\((.*)\)', raw)
data = json.loads(match.group(1)) if match else {}

name = data.get("name", "未知")
dwjz = data.get("dwjz", "N/A")
gsz = data.get("gsz", "N/A")
gszzl = data.get("gszzl", "N/A")
jzrq = data.get("jzrq", "N/A")
gztime = data.get("gztime", "N/A")

# 加载状态
state = load_state()
now = datetime.datetime.now()
today_str = now.strftime("%Y-%m-%d")

# 检测昨日预测偏差
deviation_msg = ""
prev_est = state.get("prev_estimate")
prev_est_date = state.get("prev_estimate_date")

if prev_est and prev_est_date and jzrq == prev_est_date:
    try:
        est_val = float(prev_est["gsz"])
        actual_val = float(dwjz)
        deviation = est_val - actual_val
        dev_pct = (est_val / actual_val - 1) * 100
        deviation_msg = f"\n⚠️ 昨日预测偏差: {deviation:+.4f} ({dev_pct:+.2f}%)\n"
        deviation_msg += f"   估算 {est_val:.4f} → 实际 {actual_val:.4f}"
    except:
        pass

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
msg = f"{title} — {name} 015690\n\n"
msg += f"📅 净值日期: {jzrq}\n"
msg += f"📌 昨日净值: {dwjz}\n"
msg += f"📈 今日估算: {gsz}\n"
msg += f"📊 估算涨跌: {gszzl}%\n"
msg += f"⏰ 估值时间: {gztime}"

if deviation_msg:
    msg += f"\n{deviation_msg}"

# 收盘时保存今日估算作为下次偏差对比
if hour >= 15:
    state["prev_estimate"] = {"gsz": gsz, "gszzl": gszzl, "time": gztime}
    state["prev_estimate_date"] = today_str
    save_state(state)

send_wx(msg)
