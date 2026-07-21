#!/usr/bin/env python3
"""
股票价格监控脚本模板 v8
功能：整数涨跌幅提醒 + 定时汇报 + 止盈止损 + 盘口分析 + 双重价格对比

⚠️ 关键修复：
- 收盘判断要在交易时间检查之前
- 整数涨跌幅用round()，包括0%
- f49是外盘，不是f162
"""

import urllib.request
import json
import datetime
import sys
import os

# ========== 配置区域（修改这里）==========

# 企业微信Webhook（从环境变量读取）
WX_WEBHOOK = os.environ.get("WX_WEBHOOK", "")

# 股票配置
STOCK_CODE = "0.002972"    # 东财secid格式
STOCK_NAME = "科安达"
DB_TS_CODE = "002972"      # 数据库中的股票代码

# 买入信息
AVG_COST = 16.443          # 持仓均价
SHARES = 400               # 持仓数量

# 止盈止损（固定，基于买入价）
TAKE_PROFIT_PCT = 15
STOP_LOSS_PCT = 8
HOLD_DAYS = "3-5天"

# 计算止盈止损价
COST_TP = AVG_COST * (1 + TAKE_PROFIT_PCT / 100)
COST_SL = AVG_COST * (1 - STOP_LOSS_PCT / 100)

STATE_FILE = ".monitor_state.json"

# 扫描发现信息（从数据库读取）
SCAN_INFO = {
    "first_price": 15.80,
    "first_time": "2026-06-16",
    "first_rsi": 70.10,
    "loaded": False,
}

# ========== 以下代码一般不改 ==========

def load_scan_info():
    """从数据库加载扫描发现信息"""
    global SCAN_INFO
    if SCAN_INFO["loaded"]:
        return
    try:
        import pymysql
        from config import MYSQL_CONFIG
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            SELECT latest_price, rsi14, scan_time
            FROM stock_scan_results 
            WHERE ts_code = %s 
            ORDER BY scan_time ASC 
            LIMIT 1
        ''', (DB_TS_CODE,))
        first_scan = cursor.fetchone()
        cursor.close()
        conn.close()
        if first_scan:
            SCAN_INFO["first_price"] = float(first_scan["latest_price"])
            SCAN_INFO["first_time"] = str(first_scan["scan_time"])[:10]
            SCAN_INFO["first_rsi"] = float(first_scan["rsi14"])
            SCAN_INFO["loaded"] = True
    except Exception as e:
        print(f"加载扫描信息失败: {e}")

def send_wx(content):
    """推送企业微信群"""
    if not WX_WEBHOOK:
        print("未配置WX_WEBHOOK环境变量")
        return
    data = json.dumps({"msgtype": "text", "text": {"content": content}}).encode()
    req = urllib.request.Request(WX_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"推送失败: {e}")

def get_price():
    """获取实时行情数据"""
    url = f"http://push2delay.eastmoney.com/api/qt/stock/get?secid={STOCK_CODE}&fields=f43,f44,f45,f46,f47,f48,f49,f60,f161,f170,f85"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())["data"]
            price = data["f43"] / 100
            high = data["f44"] / 100
            low = data["f45"] / 100
            yesterday = data["f60"] / 100
            outer = data["f49"]        # ⚠️ 外盘是f49，不是f162
            inner = data["f161"]
            change_pct = data["f170"] / 100
            volume = data["f47"]
            circ_shares = data["f85"]
            amplitude = (high - low) / yesterday * 100
            turnover = volume * 100 / circ_shares * 100 if circ_shares > 0 else 0
            total_vol = outer + inner
            outer_ratio = outer / total_vol * 100 if total_vol > 0 else 50
            return {
                "price": price, "yesterday": yesterday, "change_pct": change_pct,
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
            "open_sent": False, "close_sent": False, "pct_alerts": [],
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
    """格式化状态信息"""
    load_scan_info()
    price = price_data["price"]
    scan_price = SCAN_INFO["first_price"]
    scan_time = SCAN_INFO["first_time"]
    SCAN_TP = scan_price * 1.15
    SCAN_SL = scan_price * 0.92
    
    profit_from_cost = (price - AVG_COST) / AVG_COST * 100
    profit_from_scan = (price - scan_price) / scan_price * 100
    profit_amount = (price - AVG_COST) * SHARES
    total_value = price * SHARES
    cost_premium = (AVG_COST - scan_price) / scan_price * 100
    change_pct = price_data["change_pct"]
    
    sign1 = "+" if profit_from_cost >= 0 else ""
    sign2 = "+" if profit_from_scan >= 0 else ""
    sign3 = "+" if change_pct >= 0 else ""
    sign4 = "+" if profit_amount >= 0 else ""
    
    outer_ratio = price_data["outer_ratio"]
    if outer_ratio > 60:
        pan判断 = "买方强势 ✅"
    elif outer_ratio < 40:
        pan判断 = "卖方强势 ⚠️"
    else:
        pan判断 = "买卖均衡"
    
    msg = f"{tag}📈 {STOCK_NAME} 002972\n"
    msg += f"\n"
    msg += f"💰 现价 {price:.2f}  |  今日 {sign3}{change_pct:.2f}%\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"\n"
    msg += f"📊 持仓盈亏\n"
    msg += f"   持仓 {SHARES}股  市值 {total_value:.0f}元\n"
    msg += f"   盈亏 {sign4}{profit_amount:.0f}元（{sign1}{profit_from_cost:.1f}%）\n"
    msg += f"\n"
    msg += f"🔍 双重对比\n"
    msg += f"   扫描发现价 {scan_price:.2f}（{scan_time}）\n"
    msg += f"   └ 现价涨幅 {sign2}{profit_from_scan:.1f}%\n"
    msg += f"   实际买入价 {AVG_COST:.3f}\n"
    msg += f"   └ 买入溢价 +{cost_premium:.1f}%\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"\n"
    msg += f"📈 盘口数据\n"
    msg += f"   振幅 {price_data['amplitude']:.2f}%  |  换手 {price_data['turnover']:.2f}%\n"
    msg += f"   外盘 {price_data['outer']//10000}万手（{outer_ratio:.0f}%）\n"
    msg += f"   内盘 {price_data['inner']//10000}万手（{100-outer_ratio:.0f}%）\n"
    msg += f"   {pan判断}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"\n"
    msg += f"🎯 止盈参考\n"
    msg += f"   买入价 {AVG_COST:.3f}  →  {COST_TP:.2f}（+{TAKE_PROFIT_PCT}%）\n"
    msg += f"   发现价 {scan_price:.2f}  →  {SCAN_TP:.2f}（+15%）\n"
    msg += f"\n"
    msg += f"🚨 止损参考\n"
    msg += f"   买入价 {AVG_COST:.3f}  →  {COST_SL:.2f}（-{STOP_LOSS_PCT}%）\n"
    msg += f"   发现价 {scan_price:.2f}  →  {SCAN_SL:.2f}（-8%）\n"
    msg += f"\n"
    msg += f"⏰ 建议持仓 {HOLD_DAYS}"
    return msg

def main():
    now = datetime.datetime.now()
    state = load_state()
    
    load_scan_info()
    
    # ⚠️ 收盘判断要在交易时间检查之前！
    if now.hour == 15 and now.minute == 0 and not state.get("close_sent"):
        price_data = get_price()
        if price_data:
            msg = f"📊 【收盘总结】\n\n" + format_status(price_data)
            send_wx(msg)
            state["close_sent"] = True
            save_state(state)
        return
    
    if not is_trading_time():
        return
    
    price_data = get_price()
    if not price_data:
        return
    
    price = price_data["price"]
    change_pct = price_data["change_pct"]
    
    # 每天9:30重置状态
    if now.hour == 9 and now.minute >= 25 and now.minute <= 30:
        state = {
            "alerted_types": [], "last_hourly": None, "last_price": price,
            "open_sent": False, "close_sent": False, "pct_alerts": [],
        }
    
    # 9:30开盘播报
    if now.hour == 9 and now.minute == 30 and not state.get("open_sent"):
        msg = f"🔔 【开盘播报】\n\n" + format_status(price_data)
        send_wx(msg)
        state["open_sent"] = True
        state["last_price"] = price
        save_state(state)
        return
    
    # 整点播报
    current_hour = now.strftime("%H:00")
    if current_hour != state.get("last_hourly") and now.minute == 0:
        msg = f"⏰ 【整点播报】\n\n" + format_status(price_data)
        send_wx(msg)
        state["last_hourly"] = current_hour
        save_state(state)
        return
    
    # ⚠️ 整数涨跌幅提醒（用round，包括0%）
    current_pct_int = round(change_pct)
    if -10 <= current_pct_int <= 10:
        if current_pct_int not in state.get("pct_alerts", []):
            if current_pct_int == 0:
                emoji = "➡️"
                direction = "平盘"
            elif current_pct_int > 0:
                emoji = "📈"
                direction = "涨"
            else:
                emoji = "📉"
                direction = "跌"
            
            msg = f"{emoji} 【{direction}幅提醒】\n"
            msg += f"{STOCK_NAME} 现价 {price:.2f}（{change_pct:+.2f}%）\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"今日{direction}幅达到 {current_pct_int}%\n"
            msg += f"\n"
            msg += format_status(price_data)
            
            send_wx(msg)
            if "pct_alerts" not in state:
                state["pct_alerts"] = []
            state["pct_alerts"].append(current_pct_int)
            state["last_price"] = price
            save_state(state)
            return
    
    state["last_price"] = price
    
    # 止盈触发
    if price >= COST_TP and "take_profit" not in state["alerted_types"]:
        msg = f"🎯 【止盈触发！】\n"
        msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"✅ 建议卖出 {SHARES//2}股\n"
        msg += f"   回收 {SHARES//2*price:.0f}元  盈利 {SHARES//2*(price-AVG_COST):.0f}元"
        send_wx(msg)
        state["alerted_types"].append("take_profit")
        save_state(state)
        return
    
    # 止损触发
    if price <= COST_SL and "stop_loss" not in state["alerted_types"]:
        msg = f"🚨 【止损触发！】\n"
        msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"❌ 建议清仓 {SHARES}股\n"
        msg += f"   亏损 {(price-AVG_COST)*SHARES:.0f}元\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"⚠️ 止损第一，不要幻想回本！"
        send_wx(msg)
        state["alerted_types"].append("stop_loss")
        save_state(state)
        return
    
    save_state(state)

if __name__ == "__main__":
    main()
