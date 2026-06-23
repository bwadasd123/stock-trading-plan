#!/usr/bin/env python3
"""
科安达价格监控脚本 v2
功能：定时汇报 + 涨跌播报 + 开盘收盘 + 止盈止损
推送到企业微信群
"""

import urllib.request
import json
import datetime

# 企业微信Webhook
WX_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=1d5118c7-ef37-4950-9a08-36da78763c7a"

# 配置
STOCK_CODE = "0.002972"
STOCK_NAME = "科安达"
AVG_COST = 16.443
SHARES = 400

# 触发条件
TAKE_PROFIT = 18.91    # +15%
STOP_LOSS = 15.13      # -8%
WARN_HIGH = 18.00
WARN_LOW = 16.00
CHANGE_THRESHOLD = 2.0 # 涨跌幅超过2%推送

STATE_FILE = ".monitor_state.json"

def send_wx(content):
    data = json.dumps({"msgtype": "text", "text": {"content": content}}).encode()
    req = urllib.request.Request(WX_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"推送失败: {e}")

def get_price():
    url = f"http://push2delay.eastmoney.com/api/qt/stock/get?secid={STOCK_CODE}&fields=f43,f170,f44,f45,f46,f60"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())["data"]
            return {
                "price": data["f43"] / 100,
                "change_pct": data["f170"] / 100,
                "high": data["f44"] / 100,
                "low": data["f45"] / 100,
                "open": data["f46"] / 100,
                "yesterday": data["f60"] / 100
            }
    except:
        return None

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "alerted_types": [],
            "last_hourly": None,
            "last_price": None,
            "open_sent": False,
            "close_sent": False
        }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, default=str)

def is_trading_time():
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (datetime.time(9, 25) <= t <= datetime.time(11, 31)) or \
           (datetime.time(12, 55) <= t <= datetime.time(15, 1))

def format_status(price_data, tag=""):
    price = price_data["price"]
    profit_pct = (price - AVG_COST) / AVG_COST * 100
    profit_amount = (price - AVG_COST) * SHARES
    total_value = price * SHARES
    
    emoji = "📈" if profit_pct >= 0 else "📉"
    
    msg = f"{tag}{emoji} {STOCK_NAME} {price} ({'+' if profit_pct>=0 else ''}{profit_pct:.1f}%)\n"
    msg += f"持仓: {SHARES}股 | 盈亏: {'+' if profit_amount>=0 else ''}{profit_amount:.0f}元\n"
    msg += f"市值: {total_value:.0f}元 | 今日: {'+' if price_data['change_pct']>=0 else ''}{price_data['change_pct']:.1f}%\n"
    msg += f"止盈: {TAKE_PROFIT} | 止损: {STOP_LOSS}"
    return msg

def main():
    now = datetime.datetime.now()
    state = load_state()
    
    if not is_trading_time():
        # 15:00收盘推送（每天只推一次）
        if now.hour == 15 and now.minute == 0 and not state.get("close_sent"):
            price_data = get_price()
            if price_data:
                msg = f"📊 【收盘总结】\n" + format_status(price_data)
                send_wx(msg)
                state["close_sent"] = True
                save_state(state)
        return
    
    price_data = get_price()
    if not price_data:
        return
    
    price = price_data["price"]
    profit_pct = (price - AVG_COST) / AVG_COST * 100
    
    # 每天9:30重置状态
    if now.hour == 9 and now.minute >= 25 and now.minute <= 30:
        state["alerted_types"] = []
        state["open_sent"] = False
        state["close_sent"] = False
        state["last_price"] = price
    
    # 9:30开盘推送
    if now.hour == 9 and now.minute == 30 and not state.get("open_sent"):
        msg = f"🔔 【开盘播报】\n" + format_status(price_data)
        send_wx(msg)
        state["open_sent"] = True
        state["last_price"] = price
        save_state(state)
        return
    
    # 每小时定时汇报（整点推送）
    current_hour = now.strftime("%H:00")
    if current_hour != state.get("last_hourly") and now.minute == 0:
        msg = f"⏰ 【整点播报】\n" + format_status(price_data)
        send_wx(msg)
        state["last_hourly"] = current_hour
        save_state(state)
        return
    
    # 涨跌超过2%推送
    last_price = state.get("last_price")
    if last_price:
        change_from_last = (price - last_price) / last_price * 100
        if abs(change_from_last) >= CHANGE_THRESHOLD and f"change_{int(change_from_last)}" not in state["alerted_types"]:
            direction = "拉升" if change_from_last > 0 else "跳水"
            msg = f"⚡ 【{direction}提醒】\n"
            msg += f"{STOCK_NAME} {last_price} → {price} ({'+' if change_from_last>0 else ''}{change_from_last:.1f}%)\n"
            msg += format_status(price_data)
            send_wx(msg)
            state["alerted_types"].append(f"change_{int(change_from_last)}")
            state["last_price"] = price
            save_state(state)
            return
    
    # 止盈止损触发
    if price >= TAKE_PROFIT and "take_profit" not in state["alerted_types"]:
        msg = f"🎯 【止盈触发！】\n{STOCK_NAME} 现价{price} (+{profit_pct:.1f}%)\n建议卖出200股，回收{200*price:.0f}元\n剩余200股继续持有"
        send_wx(msg)
        state["alerted_types"].append("take_profit")
        save_state(state)
        return
    
    if price <= STOP_LOSS and "stop_loss" not in state["alerted_types"]:
        msg = f"🚨 【止损触发！】\n{STOCK_NAME} 现价{price} ({profit_pct:.1f}%)\n建议清仓400股，亏损{(price-AVG_COST)*SHARES:.0f}元"
        send_wx(msg)
        state["alerted_types"].append("stop_loss")
        save_state(state)
        return
    
    if price >= WARN_HIGH and "warn_high" not in state["alerted_types"]:
        msg = f"📈 【接近止盈】\n{STOCK_NAME} 现价{price} (+{profit_pct:.1f}%)\n距止盈18.91还差{(TAKE_PROFIT-price)/price*100:.1f}%"
        send_wx(msg)
        state["alerted_types"].append("warn_high")
        save_state(state)
        return
    
    if price <= WARN_LOW and "warn_low" not in state["alerted_types"]:
        msg = f"📉 【接近止损】\n{STOCK_NAME} 现价{price} ({profit_pct:.1f}%)\n距止损15.13还差{(price-STOP_LOSS)/price*100:.1f}%"
        send_wx(msg)
        state["alerted_types"].append("warn_low")
        save_state(state)
        return

if __name__ == "__main__":
    main()
