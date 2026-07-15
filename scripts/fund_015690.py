#!/usr/bin/env python3
"""015690 基金估值 → 企微推送"""
import urllib.request, json, re, os

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

msg = f"""📊 {name} 015690

昨日净值({jzrq})  {dwjz}
今日估算        {gsz}
涨跌            {gszzl}%"""

send_wx(msg)
