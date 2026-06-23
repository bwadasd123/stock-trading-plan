#!/usr/bin/env python3
"""
股票价格监控脚本模板
使用说明：修改下方配置参数，部署到服务器运行
"""

import urllib.request
import json
import datetime

# ========== 配置区域（修改这里）==========

# 企业微信Webhook（替换为你的key）
WX_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key"

# 股票配置
STOCK_CODE = "0.002972"    # 东财secid格式：0.代码(深市) 1.代码(沪市)
STOCK_NAME = "科安达"       # 股票名称
AVG_COST = 16.443           # 持仓均价
SHARES = 400                # 持仓数量

# 价格触发条件
TAKE_PROFIT = 18.91         # 止盈价（+15%）
STOP_LOSS = 15.13           # 止损价（-8%）
WARN_HIGH = 18.00           # 接近止盈提醒
WARN_LOW = 16.00            # 接近止损提醒
CHANGE_THRESHOLD = 2.0      # 涨跌幅超过X%推送

# 状态文件路径
STATE_FILE = ".monitor_state.json"

# ========== 代码区域（一般不改）==========

def send_wx(content):
    """推送企业微信群"""
    data = json.dumps({"msgtype": "text", "text": {"content": content}}).encode()
    req = urllib.request.Request(WX_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"推送失败: {e}")

def get_price():
    """获取实时价格"""
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
    """判断是否在交易时间"""
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (datetime.time(9, 25) <= t <= datetime.time(11, 31)) or \
           (datetime.time(12, 55) <= t <= datetime.time(15, 1))

def format_status(price_data, tag=""):
    """格式化状态信息"""
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
        # 15:00收盘推送
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
    
    # 每小时定时汇报
    current_hour = now.strftime("%H:00")
    if current_hour != state.get("last_hourly") and now.minute == 0:
        msg = f"⏰ 【整点播报】\n" + format_status(price_data)
        send_wx(msg)
        state["last_hourly"] = current_hour
        save_state(state)
        return
    
    # 涨跌超过阈值推送
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
        msg = f"🎯 【止盈触发！】\n{STOCK_NAME} 现价{price} (+{profit_pct:.1f}%)\n建议卖出一半，回收{SHARES//2*price:.0f}元"
        send_wx(msg)
        state["alerted_types"].append("take_profit")
        save_state(state)
        return
    
    if price <= STOP_LOSS and "stop_loss" not in state["alerted_types"]:
        msg = f"🚨 【止损触发！】\n{STOCK_NAME} 现价{price} ({profit_pct:.1f}%)\n建议清仓{SHARES}股，亏损{(price-AVG_COST)*SHARES:.0f}元"
        send_wx(msg)
        state["alerted_types"].append("stop_loss")
        save_state(state)
        return
    
    if price >= WARN_HIGH and "warn_high" not in state["alerted_types"]:
        msg = f"📈 【接近止盈】\n{STOCK_NAME} 现价{price} (+{profit_pct:.1f}%)\n距止盈{TAKE_PROFIT}还差{(TAKE_PROFIT-price)/price*100:.1f}%"
        send_wx(msg)
        state["alerted_types"].append("warn_high")
        save_state(state)
        return
    
    if price <= WARN_LOW and "warn_low" not in state["alerted_types"]:
        msg = f"📉 【接近止损】\n{STOCK_NAME} 现价{price} ({profit_pct:.1f}%)\n距止损{STOP_LOSS}还差{(price-STOP_LOSS)/price*100:.1f}%"
        send_wx(msg)
        state["alerted_types"].append("warn_low")
        save_state(state)
        return

if __name__ == "__main__":
    main()
