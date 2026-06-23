#!/usr/bin/env python3
"""
科安达价格监控脚本 v4
功能：定时汇报 + 涨跌播报 + 开盘收盘 + 止盈止损 + 盘口分析 + 挂单提醒
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
CIRCULATING_SHARES = 134646315  # 流通股本(f85)

# 触发条件
TAKE_PROFIT = 18.00    # 止盈价（+9.5%）
STOP_LOSS = 15.13      # 止损价（-8%）
WARN_HIGH = 17.50      # 接近止盈提醒
WARN_LOW = 16.00       # 接近止损提醒
CHANGE_THRESHOLD = 1.0 # 涨跌幅超过1%推送

# 挂单价格（可调整）
LIMIT_SELL_1 = 18.00   # 第一档止盈卖出
LIMIT_SELL_2 = 18.50   # 第二档止盈卖出
LIMIT_SELL_3 = 18.91   # 第三档止盈卖出（原目标价）
LIMIT_BUY_1 = 17.00    # 第一档回调买入
LIMIT_BUY_2 = 16.50    # 第二档回调买入（接近成本）

STATE_FILE = "/home/jmy/.hermes/profiles/eastmoney-bot/scripts/.monitor_state.json"

def send_wx(content):
    """推送企业微信群"""
    data = json.dumps({"msgtype": "text", "text": {"content": content}}).encode()
    req = urllib.request.Request(WX_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"推送失败: {e}")

def get_price():
    """获取实时行情数据"""
    url = f"http://push2delay.eastmoney.com/api/qt/stock/get?secid={STOCK_CODE}&fields=f43,f44,f45,f46,f47,f48,f49,f50,f60,f161,f170,f85"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())["data"]
            
            # 正确解析字段
            price = data["f43"] / 100
            high = data["f44"] / 100
            low = data["f45"] / 100
            open_p = data["f46"] / 100
            yesterday = data["f60"] / 100
            volume = data["f47"]           # 成交量(手)
            amount = data["f48"]           # 成交额(元)
            outer = data["f49"]            # 外盘(手)
            inner = data["f161"]           # 内盘(手)
            change_pct = data["f170"] / 100  # 涨跌幅
            circ_shares = data["f85"]      # 流通股本
            
            # 计算指标
            amplitude = (high - low) / yesterday * 100  # 振幅
            turnover = volume * 100 / circ_shares * 100 if circ_shares > 0 else 0  # 换手率
            
            # 内外盘比
            total_vol = outer + inner
            outer_ratio = outer / total_vol * 100 if total_vol > 0 else 50
            
            return {
                "price": price,
                "high": high,
                "low": low,
                "open": open_p,
                "yesterday": yesterday,
                "change_pct": change_pct,
                "volume": volume,
                "amount": amount,
                "outer": outer,
                "inner": inner,
                "outer_ratio": outer_ratio,
                "amplitude": amplitude,
                "turnover": turnover,
            }
    except Exception as e:
        print(f"获取数据失败: {e}")
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
            "close_sent": False,
            "order_reminder_sent": False,
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

def get_order_suggestions(price):
    """根据当前价格生成挂单建议"""
    profit_pct = (price - AVG_COST) / AVG_COST * 100
    suggestions = []
    
    # 止盈挂单建议
    if price < LIMIT_SELL_1:
        distance = (LIMIT_SELL_1 - price) / price * 100
        suggestions.append(f"📌 卖出挂单：{LIMIT_SELL_1}元（距{distance:.1f}%）")
        suggestions.append(f"   └ 卖出{SHARES//2}股，回收{SHARES//2*LIMIT_SELL_1:.0f}元")
    
    if price < LIMIT_SELL_2:
        suggestions.append(f"📌 卖出挂单：{LIMIT_SELL_2}元")
    
    if price < LIMIT_SELL_3:
        suggestions.append(f"📌 卖出挂单：{LIMIT_SELL_3}元（原目标价）")
    
    # 止损挂单建议
    if price > STOP_LOSS:
        distance = (price - STOP_LOSS) / price * 100
        suggestions.append(f"📌 止损挂单：{STOP_LOSS}元（距{distance:.1f}%）")
        suggestions.append(f"   └ 清仓{SHARES}股，亏损{(STOP_LOSS-AVG_COST)*SHARES:.0f}元")
    
    # 回调买入建议（如果仓位不满）
    if price > LIMIT_BUY_1:
        suggestions.append(f"📌 回调买入：{LIMIT_BUY_1}元（补仓机会）")
    
    return suggestions

def format_status(price_data, tag=""):
    """格式化状态信息（含盘口分析+挂单建议）"""
    price = price_data["price"]
    profit_pct = (price - AVG_COST) / AVG_COST * 100
    profit_amount = (price - AVG_COST) * SHARES
    total_value = price * SHARES
    
    emoji = "📈" if profit_pct >= 0 else "📉"
    change_emoji = "🔺" if price_data["change_pct"] >= 0 else "🔻"
    
    msg = f"{tag}{emoji} {STOCK_NAME} {price:.2f} ({'+' if profit_pct>=0 else ''}{profit_pct:.1f}%)\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"💰 持仓：{SHARES}股 | 市值：{total_value:.0f}元\n"
    msg += f"📊 盈亏：{'+' if profit_amount>=0 else ''}{profit_amount:.0f}元\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"{change_emoji} 今日：{'+' if price_data['change_pct']>=0 else ''}{price_data['change_pct']:.2f}%\n"
    msg += f"📏 振幅：{price_data['amplitude']:.2f}%\n"
    msg += f"🔄 换手：{price_data['turnover']:.2f}%\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"🟢 外盘：{price_data['outer']}手 ({price_data['outer_ratio']:.0f}%)\n"
    msg += f"🔴 内盘：{price_data['inner']}手 ({100-price_data['outer_ratio']:.0f}%)\n"
    
    # 盘口判断
    if price_data['outer_ratio'] > 60:
        msg += f"📊 判断：买方强势 ✅\n"
    elif price_data['outer_ratio'] < 40:
        msg += f"📊 判断：卖方强势 ⚠️\n"
    else:
        msg += f"📊 判断：买卖均衡\n"
    
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"🎯 止盈：{TAKE_PROFIT} (+{(TAKE_PROFIT-AVG_COST)/AVG_COST*100:.0f}%)\n"
    msg += f"🚨 止损：{STOP_LOSS} ({(STOP_LOSS-AVG_COST)/AVG_COST*100:.0f}%)"
    
    return msg

def format_order_reminder(price_data):
    """格式化挂单提醒"""
    price = price_data["price"]
    profit_pct = (price - AVG_COST) / AVG_COST * 100
    
    msg = f"📋 【挂单提醒】\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"当前价：{price:.2f} ({'+' if profit_pct>=0 else ''}{profit_pct:.1f}%)\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    
    suggestions = get_order_suggestions(price)
    for s in suggestions:
        msg += f"{s}\n"
    
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"💡 建议在券商APP设置条件单\n"
    msg += f"   价格到自动执行，不用盯盘"
    
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
                msg += f"\n\n{format_order_reminder(price_data)}"
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
        state["order_reminder_sent"] = False
        state["last_price"] = price
    
    # 9:30开盘推送（含挂单提醒）
    if now.hour == 9 and now.minute == 30 and not state.get("open_sent"):
        msg = f"🔔 【开盘播报】\n" + format_status(price_data)
        msg += f"\n\n{format_order_reminder(price_data)}"
        send_wx(msg)
        state["open_sent"] = True
        state["last_price"] = price
        save_state(state)
        return
    
    # 10:30 挂单提醒（每天一次）
    if now.hour == 10 and now.minute == 30 and not state.get("order_reminder_sent"):
        msg = format_order_reminder(price_data)
        send_wx(msg)
        state["order_reminder_sent"] = True
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
            msg += f"{STOCK_NAME} {last_price:.2f} → {price:.2f} ({'+' if change_from_last>0 else ''}{change_from_last:.1f}%)\n"
            msg += format_status(price_data)
            send_wx(msg)
            state["alerted_types"].append(f"change_{int(change_from_last)}")
            state["last_price"] = price
            save_state(state)
            return
    
    # 接近关键价位时推送挂单提醒
    if price >= WARN_HIGH and "warn_high" not in state["alerted_types"]:
        msg = f"📈 【接近止盈】\n"
        msg += f"{STOCK_NAME} 现价{price:.2f} (+{profit_pct:.1f}%)\n"
        msg += f"距止盈{TAKE_PROFIT}还差{(TAKE_PROFIT-price)/price*100:.1f}%\n\n"
        msg += format_order_reminder(price_data)
        send_wx(msg)
        state["alerted_types"].append("warn_high")
        save_state(state)
        return
    
    if price <= WARN_LOW and "warn_low" not in state["alerted_types"]:
        msg = f"📉 【接近止损】\n"
        msg += f"{STOCK_NAME} 现价{price:.2f} ({profit_pct:.1f}%)\n"
        msg += f"距止损{STOP_LOSS}还差{(price-STOP_LOSS)/price*100:.1f}%\n\n"
        msg += format_order_reminder(price_data)
        send_wx(msg)
        state["alerted_types"].append("warn_low")
        save_state(state)
        return
    
    # 止盈止损触发
    if price >= TAKE_PROFIT and "take_profit" not in state["alerted_types"]:
        msg = f"🎯 【止盈触发！】\n"
        msg += f"{STOCK_NAME} 现价{price:.2f} (+{profit_pct:.1f}%)\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"✅ 建议立即卖出{SHARES//2}股\n"
        msg += f"   回收：{SHARES//2*price:.0f}元\n"
        msg += f"   盈利：{SHARES//2*(price-AVG_COST):.0f}元\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"📌 剩余{SHARES//2}股挂单：\n"
        msg += f"   {LIMIT_SELL_2}元（再赚{(LIMIT_SELL_2-price)*SHARES//2:.0f}元）\n"
        msg += f"   {LIMIT_SELL_3}元（原目标价）"
        send_wx(msg)
        state["alerted_types"].append("take_profit")
        save_state(state)
        return
    
    if price <= STOP_LOSS and "stop_loss" not in state["alerted_types"]:
        msg = f"🚨 【止损触发！】\n"
        msg += f"{STOCK_NAME} 现价{price:.2f} ({profit_pct:.1f}%)\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"❌ 建议立即清仓{SHARES}股\n"
        msg += f"   亏损：{(price-AVG_COST)*SHARES:.0f}元\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"⚠️ 不要幻想回本，止损第一！"
        send_wx(msg)
        state["alerted_types"].append("stop_loss")
        save_state(state)
        return

if __name__ == "__main__":
    main()
