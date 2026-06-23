#!/usr/bin/env python3
"""
科安达价格监控脚本 v5
功能：定时汇报 + 涨跌播报 + 开盘收盘 + 动态止盈止损 + 盘口分析 + 挂单提醒
基于股票筛选系统的技术指标动态计算止盈止损
"""

import urllib.request
import json
import datetime
import sys
import os

# 添加stock-screener路径
sys.path.insert(0, '/home/jmy/stock-screener')

# 企业微信Webhook
WX_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=1d5118c7-ef37-4950-9a08-36da78763c7a"

# 配置
STOCK_CODE = "0.002972"
STOCK_NAME = "科安达"
AVG_COST = 16.443
SHARES = 400
DB_TS_CODE = "002972"  # 数据库中的股票代码

STATE_FILE = "/home/jmy/.hermes/profiles/eastmoney-bot/scripts/.monitor_state.json"

# 缓存技术指标（每天更新一次）
TECH_CACHE = {
    "last_update": None,
    "rsi": 70,
    "ma10": 15.00,
    "ma20": 13.50,
    "support_5d": 14.30,
    "stop_loss": 14.72,
    "take_profit": 18.42,
    "hold_days": "2-3天",
    "take_profit_pct": 12,
}

def get_tech_indicators():
    """从数据库和K线获取技术指标，计算动态止盈止损"""
    global TECH_CACHE
    
    # 每天只更新一次
    today = datetime.date.today().isoformat()
    if TECH_CACHE["last_update"] == today:
        return TECH_CACHE
    
    try:
        import pymysql
        from config import MYSQL_CONFIG
        
        # 从数据库获取RSI
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            SELECT rsi14, ma10, ma20 
            FROM stock_scan_results 
            WHERE ts_code = %s 
            ORDER BY scan_time DESC 
            LIMIT 1
        ''', (DB_TS_CODE,))
        db_result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if db_result:
            TECH_CACHE["rsi"] = float(db_result["rsi14"]) if db_result["rsi14"] else 70
        
        # 从K线获取最新MA和支撑位
        from services.kline import get_kline_data
        result = get_kline_data('002972', limit=30)
        
        if result and 'klines' in result:
            klines = result['klines']
            closes = [k['close'] for k in klines]
            lows = [k['low'] for k in klines]
            
            TECH_CACHE["ma5"] = sum(closes[-5:]) / 5
            TECH_CACHE["ma10"] = sum(closes[-10:]) / 10
            TECH_CACHE["ma20"] = sum(closes[-20:]) / 20
            TECH_CACHE["support_5d"] = min(lows[-5:])
        
        # 计算动态止盈止损
        rsi = TECH_CACHE["rsi"]
        ma10 = TECH_CACHE["ma10"]
        support_5d = TECH_CACHE["support_5d"]
        
        # 止损：跌破MA10或近5日低点
        TECH_CACHE["stop_loss"] = max(ma10, support_5d) * 0.98
        
        # 止盈：基于RSI动态调整
        if rsi > 80:
            TECH_CACHE["take_profit_pct"] = 8
            TECH_CACHE["hold_days"] = "1-2天"
        elif rsi > 70:
            TECH_CACHE["take_profit_pct"] = 12
            TECH_CACHE["hold_days"] = "2-3天"
        else:
            TECH_CACHE["take_profit_pct"] = 15
            TECH_CACHE["hold_days"] = "3-5天"
        
        TECH_CACHE["take_profit"] = AVG_COST * (1 + TECH_CACHE["take_profit_pct"] / 100)
        TECH_CACHE["last_update"] = today
        
        print(f"技术指标更新: RSI={rsi}, MA10={ma10:.2f}, 止损={TECH_CACHE['stop_loss']:.2f}, 止盈={TECH_CACHE['take_profit']:.2f}")
        
    except Exception as e:
        print(f"获取技术指标失败: {e}")
        # 使用默认值
    
    return TECH_CACHE

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
            
            price = data["f43"] / 100
            high = data["f44"] / 100
            low = data["f45"] / 100
            open_p = data["f46"] / 100
            yesterday = data["f60"] / 100
            volume = data["f47"]
            amount = data["f48"]
            outer = data["f49"]
            inner = data["f161"]
            change_pct = data["f170"] / 100
            circ_shares = data["f85"]
            
            amplitude = (high - low) / yesterday * 100
            turnover = volume * 100 / circ_shares * 100 if circ_shares > 0 else 0
            total_vol = outer + inner
            outer_ratio = outer / total_vol * 100 if total_vol > 0 else 50
            
            return {
                "price": price, "high": high, "low": low, "open": open_p,
                "yesterday": yesterday, "change_pct": change_pct,
                "volume": volume, "amount": amount,
                "outer": outer, "inner": inner, "outer_ratio": outer_ratio,
                "amplitude": amplitude, "turnover": turnover,
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
            "alerted_types": [], "last_hourly": None, "last_price": None,
            "open_sent": False, "close_sent": False, "order_reminder_sent": False,
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

def get_order_suggestions(price, tech):
    """根据当前价格和技术指标生成挂单建议"""
    suggestions = []
    
    # 止盈挂单
    if price < tech["take_profit"]:
        distance = (tech["take_profit"] - price) / price * 100
        suggestions.append(f"📌 止盈挂单：{tech['take_profit']:.2f}元（距{distance:.1f}%）")
        suggestions.append(f"   └ 卖出{SHARES//2}股，回收{SHARES//2*tech['take_profit']:.0f}元")
        suggestions.append(f"   └ 依据：RSI{tech['rsi']:.0f}对应+{tech['take_profit_pct']}%目标")
    
    # 止损挂单
    if price > tech["stop_loss"]:
        distance = (price - tech["stop_loss"]) / price * 100
        suggestions.append(f"📌 止损挂单：{tech['stop_loss']:.2f}元（距{distance:.1f}%）")
        suggestions.append(f"   └ 清仓{SHARES}股，亏损{(tech['stop_loss']-AVG_COST)*SHARES:.0f}元")
        suggestions.append(f"   └ 依据：跌破MA10({tech['ma10']:.2f})或支撑({tech['support_5d']:.2f})")
    
    # MA止损提醒
    suggestions.append(f"📌 动态止损线：")
    suggestions.append(f"   └ MA10 = {tech['ma10']:.2f}（跌破减仓50%）")
    suggestions.append(f"   └ MA20 = {tech['ma20']:.2f}（跌破清仓）")
    
    return suggestions

def format_status(price_data, tag="", show_orders=False):
    """格式化状态信息"""
    tech = get_tech_indicators()
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
    
    if price_data['outer_ratio'] > 60:
        msg += f"📊 判断：买方强势 ✅\n"
    elif price_data['outer_ratio'] < 40:
        msg += f"📊 判断：卖方强势 ⚠️\n"
    else:
        msg += f"📊 判断：买卖均衡\n"
    
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"📈 技术指标（来自筛选系统）\n"
    msg += f"   RSI14：{tech['rsi']:.1f}\n"
    msg += f"   MA10：{tech['ma10']:.2f}\n"
    msg += f"   MA20：{tech['ma20']:.2f}\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"🎯 止盈：{tech['take_profit']:.2f} (+{tech['take_profit_pct']}%)\n"
    msg += f"   └ 依据：RSI{tech['rsi']:.0f}对应策略\n"
    msg += f"🚨 止损：{tech['stop_loss']:.2f}\n"
    msg += f"   └ 依据：跌破MA10或支撑位\n"
    msg += f"⏰ 建议持仓：{tech['hold_days']}"
    
    if show_orders:
        msg += f"\n━━━━━━━━━━━━━━━━\n"
        msg += f"📋 挂单建议\n"
        for s in get_order_suggestions(price, tech):
            msg += f"{s}\n"
    
    return msg

def main():
    now = datetime.datetime.now()
    state = load_state()
    
    # 更新技术指标
    get_tech_indicators()
    
    if not is_trading_time():
        if now.hour == 15 and now.minute == 0 and not state.get("close_sent"):
            price_data = get_price()
            if price_data:
                msg = f"📊 【收盘总结】\n" + format_status(price_data, show_orders=True)
                send_wx(msg)
                state["close_sent"] = True
                save_state(state)
        return
    
    price_data = get_price()
    if not price_data:
        return
    
    price = price_data["price"]
    tech = get_tech_indicators()
    profit_pct = (price - AVG_COST) / AVG_COST * 100
    
    # 每天9:30重置状态
    if now.hour == 9 and now.minute >= 25 and now.minute <= 30:
        state = {"alerted_types": [], "last_hourly": None, "last_price": price,
                 "open_sent": False, "close_sent": False, "order_reminder_sent": False}
    
    # 9:30开盘推送
    if now.hour == 9 and now.minute == 30 and not state.get("open_sent"):
        msg = f"🔔 【开盘播报】\n" + format_status(price_data, show_orders=True)
        send_wx(msg)
        state["open_sent"] = True
        state["last_price"] = price
        save_state(state)
        return
    
    # 10:30挂单提醒
    if now.hour == 10 and now.minute == 30 and not state.get("order_reminder_sent"):
        msg = f"📋 【挂单提醒】\n"
        msg += f"当前价：{price:.2f} ({'+' if profit_pct>=0 else ''}{profit_pct:.1f}%)\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        for s in get_order_suggestions(price, tech):
            msg += f"{s}\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"💡 建议在券商APP设置条件单\n"
        msg += f"   价格到自动执行，不用盯盘"
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
        if abs(change_from_last) >= 1.0 and f"change_{int(change_from_last)}" not in state["alerted_types"]:
            direction = "拉升" if change_from_last > 0 else "跳水"
            msg = f"⚡ 【{direction}提醒】\n"
            msg += f"{STOCK_NAME} {last_price:.2f} → {price:.2f} ({'+' if change_from_last>0 else ''}{change_from_last:.1f}%)\n"
            msg += format_status(price_data)
            send_wx(msg)
            state["alerted_types"].append(f"change_{int(change_from_last)}")
            state["last_price"] = price
            save_state(state)
            return
    
    # 止盈触发
    if price >= tech["take_profit"] and "take_profit" not in state["alerted_types"]:
        msg = f"🎯 【止盈触发！】\n"
        msg += f"{STOCK_NAME} 现价{price:.2f} (+{profit_pct:.1f}%)\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"✅ 建议立即卖出{SHARES//2}股\n"
        msg += f"   回收：{SHARES//2*price:.0f}元\n"
        msg += f"   盈利：{SHARES//2*(price-AVG_COST):.0f}元\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"📊 依据：RSI{tech['rsi']:.0f}对应+{tech['take_profit_pct']}%目标\n"
        msg += f"📌 剩余{SHARES//2}股挂单：\n"
        msg += f"   跌破{tech['ma10']:.2f}（MA10）清仓"
        send_wx(msg)
        state["alerted_types"].append("take_profit")
        save_state(state)
        return
    
    # 止损触发
    if price <= tech["stop_loss"] and "stop_loss" not in state["alerted_types"]:
        msg = f"🚨 【止损触发！】\n"
        msg += f"{STOCK_NAME} 现价{price:.2f} ({profit_pct:.1f}%)\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"❌ 建议立即清仓{SHARES}股\n"
        msg += f"   亏损：{(price-AVG_COST)*SHARES:.0f}元\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"📊 依据：跌破MA10({tech['ma10']:.2f})或支撑({tech['support_5d']:.2f})\n"
        msg += f"⚠️ 不要幻想回本，止损第一！"
        send_wx(msg)
        state["alerted_types"].append("stop_loss")
        save_state(state)
        return
    
    # 接近止盈提醒
    if price >= tech["take_profit"] * 0.97 and "warn_high" not in state["alerted_types"]:
        msg = f"📈 【接近止盈】\n"
        msg += f"{STOCK_NAME} 现价{price:.2f} (+{profit_pct:.1f}%)\n"
        msg += f"距止盈{tech['take_profit']:.2f}还差{(tech['take_profit']-price)/price*100:.1f}%\n\n"
        msg += format_status(price_data, show_orders=True)
        send_wx(msg)
        state["alerted_types"].append("warn_high")
        save_state(state)
        return
    
    # 接近止损提醒
    if price <= tech["stop_loss"] * 1.03 and "warn_low" not in state["alerted_types"]:
        msg = f"📉 【接近止损】\n"
        msg += f"{STOCK_NAME} 现价{price:.2f} ({profit_pct:.1f}%)\n"
        msg += f"距止损{tech['stop_loss']:.2f}还差{(price-tech['stop_loss'])/price*100:.1f}%\n\n"
        msg += format_status(price_data, show_orders=True)
        send_wx(msg)
        state["alerted_types"].append("warn_low")
        save_state(state)
        return

if __name__ == "__main__":
    main()
