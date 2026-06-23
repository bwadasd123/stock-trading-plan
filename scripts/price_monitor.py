#!/usr/bin/env python3
"""
股票价格监控脚本 v8
功能：整数涨跌幅提醒 + 定时汇报 + 止盈止损 + 盘口分析
特色：-10%到+10%每个整数百分比都提醒（包括0%）
"""

import urllib.request
import json
import datetime
import sys
import os

sys.path.insert(0, '/home/jmy/stock-screener')

WX_WEBHOOK = os.environ.get("WX_WEBHOOK", "")

# ========== 股票配置 ==========
STOCK_CODE = "0.002972"
STOCK_NAME = "科安达"
DB_TS_CODE = "002972"

AVG_COST = 16.443
SHARES = 400

TAKE_PROFIT_PCT = 15
STOP_LOSS_PCT = 8
HOLD_DAYS = "3-5天"

COST_TP = AVG_COST * (1 + TAKE_PROFIT_PCT / 100)
COST_SL = AVG_COST * (1 - STOP_LOSS_PCT / 100)

STATE_FILE = "/home/jmy/.hermes/profiles/eastmoney-bot/scripts/.monitor_state.json"

# 扫描发现信息
SCAN_INFO = {
    "first_price": 15.80,
    "first_time": "2026-06-16",
    "first_rsi": 70.10,
    "loaded": False,
}

def load_scan_info():
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

# 技术指标缓存
TECH_CACHE = {"last_update": None, "rsi": 70, "ma10": 15.00, "ma20": 13.50}

def get_tech_indicators():
    global TECH_CACHE
    today = datetime.date.today().isoformat()
    if TECH_CACHE["last_update"] == today:
        return TECH_CACHE
    try:
        import pymysql
        from config import MYSQL_CONFIG
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
        from services.kline import get_kline_data
        result = get_kline_data('002972', limit=30)
        if result and 'klines' in result:
            klines = result['klines']
            closes = [k['close'] for k in klines]
            TECH_CACHE["ma10"] = sum(closes[-10:]) / 10
            TECH_CACHE["ma20"] = sum(closes[-20:]) / 20
        TECH_CACHE["last_update"] = today
    except Exception as e:
        print(f"获取技术指标失败: {e}")
    return TECH_CACHE

def calculate_rsi(closes, period=14):
    """实时计算RSI"""
    if len(closes) < period + 1:
        return None
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_realtime_rsi():
    """获取实时RSI"""
    try:
        from services.kline import get_kline_data
        result = get_kline_data('002972', limit=30)
        if result and 'klines' in result:
            klines = result['klines']
            closes = [k['close'] for k in klines]
            rsi = calculate_rsi(closes)
            if rsi is not None:
                return rsi
    except Exception as e:
        print(f"实时RSI计算失败: {e}")
    
    # 回退到缓存的RSI
    tech = get_tech_indicators()
    return tech.get("rsi", 70)

def send_wx(content):
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
    url = f"http://push2delay.eastmoney.com/api/qt/stock/get?secid={STOCK_CODE}&fields=f43,f44,f45,f46,f47,f48,f49,f60,f161,f170,f85"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())["data"]
            price = data["f43"] / 100
            high = data["f44"] / 100
            low = data["f45"] / 100
            yesterday = data["f60"] / 100
            outer = data["f49"]
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
            "open_sent": False, "close_sent": False,
            "pct_alerts": [],  # 已提醒的整数百分比
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
    load_scan_info()
    tech = get_tech_indicators()
    
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
    
    msg = f"{tag}📈 {STOCK_NAME} {STOCK_CODE}\n"
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
    get_tech_indicators()
    
    # 收盘总结（15:00推送）
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
    profit_pct = (price - AVG_COST) / AVG_COST * 100
    
    # 每天9:30重置状态
    if now.hour == 9 and now.minute >= 25 and now.minute <= 30:
        state = {
            "alerted_types": [], "last_hourly": None, "last_price": price,
            "open_sent": False, "close_sent": False, "pct_alerts": [],
            "rsi_alerts": [],  # RSI预警每日重置
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
    
    # ========== 整数涨跌幅提醒 ==========
    # 四舍五入到最近的整数
    current_pct_int = round(change_pct)
    
    # 检查是否在-10到+10之间（包括0）
    if -10 <= current_pct_int <= 10:
        # 检查这个整数百分比是否已经提醒过
        if current_pct_int not in state.get("pct_alerts", []):
            # 发送提醒
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
            
            # 记录已提醒的百分比
            if "pct_alerts" not in state:
                state["pct_alerts"] = []
            state["pct_alerts"].append(current_pct_int)
            state["last_price"] = price
            save_state(state)
            return
    
    # ========== RSI预警 ==========
    current_rsi = get_realtime_rsi()
    if current_rsi is not None:
        # RSI > 90 极度超买
        if current_rsi > 90 and "rsi_extreme_overbought" not in state.get("alerted_types", []):
            msg = f"🔴 【RSI极度超买警告！】\n"
            msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"📊 RSI(14) = {current_rsi:.1f}\n"
            msg += f"⚠️ 极度超买信号！历史上很少见\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🎯 建议立即减仓 {SHARES//2}股\n"
            msg += f"   回调概率极大，落袋为安\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"📊 当前持仓盈亏\n"
            msg += f"   盈利 {(price-AVG_COST)*SHARES:.0f}元（+{(price-AVG_COST)/AVG_COST*100:.1f}%）"
            send_wx(msg)
            state["alerted_types"].append("rsi_extreme_overbought")
            save_state(state)
            return
        
        # RSI > 80 超买警告
        elif current_rsi > 80 and "rsi_overbought" not in state.get("alerted_types", []):
            msg = f"⚠️ 【RSI超买警告】\n"
            msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"📊 RSI(14) = {current_rsi:.1f}\n"
            msg += f"📈 处于超买区间（>80）\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"💡 建议：考虑减仓或设置止盈\n"
            msg += f"   当前盈利 {(price-AVG_COST)/AVG_COST*100:+.1f}%"
            send_wx(msg)
            state["alerted_types"].append("rsi_overbought")
            save_state(state)
            return
        
        # RSI < 20 超卖机会
        elif current_rsi < 20 and "rsi_oversold" not in state.get("alerted_types", []):
            msg = f"🟢 【RSI超卖机会】\n"
            msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"📊 RSI(14) = {current_rsi:.1f}\n"
            msg += f"📉 处于超卖区间（<20）\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"💡 建议：可考虑补仓或建仓\n"
            msg += f"   当前盈利 {(price-AVG_COST)/AVG_COST*100:+.1f}%"
            send_wx(msg)
            state["alerted_types"].append("rsi_oversold")
            save_state(state)
            return
    
    # 更新last_price
    state["last_price"] = price
    
    # 止盈触发
    if price >= COST_TP and "take_profit" not in state["alerted_types"]:
        profit_from_scan = (price - SCAN_INFO["first_price"]) / SCAN_INFO["first_price"] * 100
        msg = f"🎯 【止盈触发！】\n"
        msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"✅ 建议卖出 {SHARES//2}股\n"
        msg += f"   回收 {SHARES//2*price:.0f}元  盈利 {SHARES//2*(price-AVG_COST):.0f}元\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 收益对比\n"
        msg += f"   买入价 {AVG_COST:.3f}  →  +{profit_pct:.1f}%\n"
        msg += f"   发现价 {SCAN_INFO['first_price']:.2f}  →  +{profit_from_scan:.1f}%"
        send_wx(msg)
        state["alerted_types"].append("take_profit")
        save_state(state)
        return
    
    # 止损触发
    if price <= COST_SL and "stop_loss" not in state["alerted_types"]:
        profit_from_scan = (price - SCAN_INFO["first_price"]) / SCAN_INFO["first_price"] * 100
        msg = f"🚨 【止损触发！】\n"
        msg += f"{STOCK_NAME} 现价 {price:.2f}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"❌ 建议清仓 {SHARES}股\n"
        msg += f"   亏损 {(price-AVG_COST)*SHARES:.0f}元\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 收益对比\n"
        msg += f"   买入价 {AVG_COST:.3f}  →  {profit_pct:.1f}%\n"
        msg += f"   发现价 {SCAN_INFO['first_price']:.2f}  →  +{profit_from_scan:.1f}%\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"⚠️ 止损第一，不要幻想回本！"
        send_wx(msg)
        state["alerted_types"].append("stop_loss")
        save_state(state)
        return
    
    # 接近止盈
    if price >= COST_TP * 0.97 and "warn_high" not in state["alerted_types"]:
        msg = f"📈 【接近止盈】\n"
        msg += f"{STOCK_NAME} 现价 {price:.2f}（买入+{profit_pct:.1f}%）\n"
        msg += f"距止盈 {COST_TP:.2f} 还差 {(COST_TP-price)/price*100:.1f}%\n\n"
        msg += format_status(price_data)
        send_wx(msg)
        state["alerted_types"].append("warn_high")
        save_state(state)
        return
    
    # 接近止损
    if price <= COST_SL * 1.03 and "warn_low" not in state["alerted_types"]:
        msg = f"📉 【接近止损】\n"
        msg += f"{STOCK_NAME} 现价 {price:.2f}（买入{profit_pct:.1f}%）\n"
        msg += f"距止损 {COST_SL:.2f} 还差 {(price-COST_SL)/price*100:.1f}%\n\n"
        msg += format_status(price_data)
        send_wx(msg)
        state["alerted_types"].append("warn_low")
        save_state(state)
        return
    
    save_state(state)

if __name__ == "__main__":
    main()
