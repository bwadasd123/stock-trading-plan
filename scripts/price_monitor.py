#!/usr/bin/env python3
"""
股票价格监控脚本 v13
监控持仓+扫描结果
功能：仓位管理 + 持仓天数提醒 + 整数涨跌幅提醒 + 止盈止损 + 盘口分析
"""

import urllib.request
import json
import datetime
import os

# ========== 加载.env文件 ==========
def load_env():
    env_paths = [
        os.path.expanduser("~/.hermes/profiles/eastmoney-bot/.env"),
        ".env",
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
            break

load_env()

# ========== 配置区域 ==========
WX_WEBHOOK = os.environ.get("WX_WEBHOOK", "")

# ========== 仓位管理配置 ==========
TOTAL_CAPITAL = 32319  # 3万本金 + 盈利2319  # 总资金3万
SINGLE_POSITION_PCT = 20  # 单只股票仓位比例20%
SINGLE_POSITION_AMOUNT = TOTAL_CAPITAL * SINGLE_POSITION_PCT / 100  # 单只股票金额6000元
MAX_HOLD_DAYS = 5  # 持仓天数上限

# 交易日列表（用于计算持仓天数，排除周末和节假日）
def get_trading_days(buy_date_str):
    """计算从买入日期到今天的交易日数"""
    from datetime import date, timedelta
    buy_date = datetime.datetime.strptime(buy_date_str, "%Y-%m-%d").date()
    today = date.today()
    if buy_date >= today:
        return 0
    
    # 已知的节假日（可扩展）
    holidays = {
        # 2026年节假日
        "2026-01-01", "2026-01-02", "2026-01-03",  # 元旦
        "2026-02-15", "2026-02-16", "2026-02-17", "2026-02-18",  # 春节
        "2026-04-05", "2026-04-06", "2026-04-07",  # 清明
        "2026-05-01", "2026-05-02", "2026-05-03",  # 劳动节
        "2026-06-14", "2026-06-15", "2026-06-16",  # 端午
        "2026-09-21", "2026-09-22", "2026-09-23",  # 中秋
        "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07",  # 国庆
    }
    
    trading_days = 0
    current = buy_date + timedelta(days=1)
    while current <= today:
        # 排除周末和节假日
        if current.weekday() < 5 and current.isoformat() not in holidays:
            trading_days += 1
        current += timedelta(days=1)
    return trading_days

# 监控列表：持仓 + 扫描结果
# type: "持仓" = 已买入, "观察" = 未买入
# buy_date: 买入日期（仅持仓类型需要）
STOCKS = [
    {
        "code": "0.002167",
        "name": "东方锆业",
        "ts_code": "002167",
        "cost": 21.247,
        "shares": 300,
        "buy_date": "2026-06-26",  # 买入日期
        "tp_pct": 15,
        "sl_pct": 8,
        "type": "持仓"
    },
    {
        "code": "0.159599",
        "name": "芯片ETF",
        "ts_code": "159599",
        "cost": None,  # 未买入
        "shares": 0,
        "buy_date": None,
        "tp_pct": 10,
        "sl_pct": 5,
        "type": "观察"
    },
    {
        "code": "1.513100",
        "name": "纳指ETF",
        "ts_code": "513100",
        "cost": None,  # 未买入
        "shares": 0,
        "buy_date": None,
        "tp_pct": 10,
        "sl_pct": 5,
        "type": "观察"
    },
    {
        "code": "0.002141",
        "name": "贤丰控股",
        "ts_code": "002141",
        "cost": 5.265,
        "shares": 1100,
        "buy_date": "2026-06-29",
        "tp_pct": 15,
        "sl_pct": 8,
        "type": "持仓"
    }
]

STATE_FILE = "/home/jmy/.hermes/profiles/eastmoney-bot/.monitor_state.json"

# ========== 核心函数 ==========

def send_wx(content):
    if not WX_WEBHOOK:
        return False
    data = json.dumps({"msgtype": "text", "text": {"content": content}}).encode()
    req = urllib.request.Request(WX_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except:
        return False

def calculate_rsi(closes, period=14):
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
    return 100 - (100 / (1 + rs))

def get_rsi(secid):
    try:
        url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=30"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("data") and data["data"].get("klines"):
                klines = data["data"]["klines"]
                closes = [float(k.split(",")[2]) for k in klines]
                return calculate_rsi(closes)
    except:
        pass
    return None

def get_price(secid):
    url = f"http://push2delay.eastmoney.com/api/qt/stock/get?secid={secid}&fltt=2&fields=f43,f44,f45,f46,f47,f48,f49,f60,f161,f170,f85"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())["data"]
            price = data["f43"]
            high = data["f44"]
            low = data["f45"]
            yesterday = data["f60"]
            change_pct = data["f170"]
            outer = data["f49"]
            inner = data["f161"]
            total_vol = outer + inner
            outer_ratio = outer / total_vol * 100 if total_vol > 0 else 50
            return {
                "price": price, "high": high, "low": low,
                "yesterday": yesterday, "change_pct": change_pct,
                "outer_ratio": outer_ratio
            }
    except:
        return None

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"alerted": {}, "open_sent": False, "close_sent": False}

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

def format_stock(stock, price_data):
    price = price_data["price"]
    change_pct = price_data["change_pct"]
    
    msg = f"📈 {stock['name']} {stock['ts_code']}\n"
    msg += f"💰 现价 {price:.3f}  |  今日 {change_pct:+.2f}%\n"
    
    if stock["cost"]:
        cost_pct = (price - stock["cost"]) / stock["cost"] * 100
        profit = (price - stock["cost"]) * stock["shares"]
        tp = stock["cost"] * (1 + stock["tp_pct"] / 100)
        sl = stock["cost"] * (1 - stock["sl_pct"] / 100)
        
        msg += f"📊 成本 {stock['cost']:.3f}  |  涨幅 {cost_pct:+.1f}%\n"
        msg += f"💼 盈亏 {'+' if profit >= 0 else ''}{profit:.0f}元\n"
        msg += f"🎯 止盈 {tp:.3f}  |  🚨 止损 {sl:.3f}\n"
        
        # 持仓天数
        if stock.get("buy_date"):
            holding_days = get_trading_days(stock["buy_date"])
            msg += f"📅 持仓 {holding_days}天"
            if holding_days >= MAX_HOLD_DAYS:
                msg += f" ⚠️已超{MAX_HOLD_DAYS}天上限！"
            msg += "\n"
        
        # 仓位管理
        position_value = stock["cost"] * stock["shares"]
        position_pct = position_value / TOTAL_CAPITAL * 100
        msg += f"💼 仓位 {position_value:.0f}元({position_pct:.0f}%)"
        if position_value > SINGLE_POSITION_AMOUNT:
            msg += f" ⚠️超仓"
        msg += "\n"
        
        # 预警
        if price >= tp:
            msg += f"⚠️ 【已到止盈位！】\n"
        elif price <= sl:
            msg += f"🔴 【已到止损位！】\n"
        elif cost_pct >= 5:
            msg += f"💰 成本涨幅+5%以上\n"
        elif cost_pct <= -3:
            msg += f"⚠️ 成本跌幅-3%以上\n"
    else:
        # 观察股票
        tp = price * 1.10
        sl = price * 0.93
        msg += f"👀 观察中  |  止盈 {tp:.3f}  |  止损 {sl:.3f}\n"
        
        # 仓位建议
        if price > 0:
            suggested_shares = int(SINGLE_POSITION_AMOUNT / price / 100) * 100
            if suggested_shares > 0:
                msg += f"💡 建议仓位 {suggested_shares}股({suggested_shares * price:.0f}元)\n"
        
        # 预警
        if change_pct >= 9.9:
            msg += f"🚀 涨停！\n"
        elif change_pct >= 5:
            msg += f"📈 大涨5%+\n"
        elif change_pct <= -5:
            msg += f"📉 大跌5%+\n"
    
    msg += f"━━━━━━━━━━━━━━━━━━━━"
    return msg, price, change_pct

def generate_advice():
    """生成持仓分析和操作建议"""
    import urllib.request
    
    # 获取大盘数据
    try:
        url = 'http://push2delay.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f14&secids=1.000001,0.399001,0.399006'
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            indices = data.get('data', {}).get('diff', [])
            market_trend = "偏暖" if any(i.get('f3', 0) > 1 for i in indices) else "震荡"
    except:
        market_trend = "未知"
    
    msg = "\n📊 【持仓分析与建议】\n"
    msg += f"市场情绪: {market_trend}\n"
    msg += f"总资金: {TOTAL_CAPITAL}元 | 单股上限: {SINGLE_POSITION_AMOUNT:.0f}元\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    
    has_position = False
    for stock in STOCKS:
        price_data = get_price(stock['code'])
        if not price_data:
            continue
        
        price = price_data['price']
        change_pct = price_data['change_pct']
        
        if stock['type'] == '持仓' and stock['cost']:
            has_position = True
            cost = stock['cost']
            shares = stock['shares']
            profit_pct = (price - cost) / cost * 100
            profit_amount = (price - cost) * shares
            tp = cost * (1 + stock['tp_pct'] / 100)
            sl = cost * (1 - stock['sl_pct'] / 100)
            dist_tp = (tp / price - 1) * 100
            dist_sl = (1 - sl / price) * 100
            
            # 持仓天数
            holding_days = 0
            if stock.get('buy_date'):
                holding_days = get_trading_days(stock['buy_date'])
            
            # 仓位占比
            position_value = cost * shares
            position_pct = position_value / TOTAL_CAPITAL * 100
            
            msg += f"\n🎯 {stock['name']}:\n"
            
            # 生成建议
            if price >= tp:
                msg += "🚨 【已到止盈位！建议立即减仓】\n"
            elif price <= sl:
                msg += "🔴 【已到止损位！建议清仓】\n"
            elif holding_days >= MAX_HOLD_DAYS:
                msg += f"⏰ 【持仓超{MAX_HOLD_DAYS}天！建议减仓或清仓】\n"
            elif position_value > SINGLE_POSITION_AMOUNT:
                msg += f"💼 【超仓！当前{position_pct:.0f}%，建议减到{SINGLE_POSITION_PCT}%】\n"
            elif dist_tp <= 3:
                msg += "🎯 逼近止盈！冲高减半仓\n"
            elif profit_pct >= 6:
                msg += "💰 浮盈6%+，可考虑减仓锁定利润\n"
            elif profit_pct >= 5:
                msg += "💰 浮盈5%+，继续持有等止盈\n"
            elif profit_pct >= 3:
                msg += "✅ 浮盈3%+，趋势向好\n"
            elif profit_pct <= -3:
                msg += "⚠️ 浮亏3%+，注意风险\n"
            else:
                msg += "📊 持有中，观望\n"
        else:
            msg += f"\n👀 {stock['name']} 观察:\n"
            msg += f"现价 {price:.3f} | 今日 {change_pct:+.2f}%\n"
            
            # 仓位建议
            if price > 0:
                suggested_shares = int(SINGLE_POSITION_AMOUNT / price / 100) * 100
                if suggested_shares > 0:
                    msg += f"💡 建议仓位 {suggested_shares}股({suggested_shares * price:.0f}元)\n"
            
            if change_pct >= 5:
                msg += "🚀 大涨中，不追高\n"
            elif change_pct <= -3:
                msg += "📉 大跌中，可关注建仓机会\n"
            else:
                msg += "📊 等待回调建仓\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
    
    # 如果全部空仓，显示提示
    if not has_position:
        msg += "\n💼 当前全部空仓，等待信号\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
    
    return msg

def main():
    now = datetime.datetime.now()
    state = load_state()
    
    # 每日状态重置（新的一天清空提醒记录）
    today_str = now.strftime("%Y-%m-%d")
    if state.get("today") != today_str:
        state = {
            "alerted": {},
            "open_sent": False,
            "close_sent": False,
            "last_hourly": None,
            "today": today_str
        }
        save_state(state)
    
    # 收盘播报
    if now.hour == 15 and now.minute == 0 and not state.get("close_sent"):
        msg = f"📊 【收盘总结】\n\n"
        for stock in STOCKS:
            price_data = get_price(stock["code"])
            if price_data:
                stock_msg, _, _ = format_stock(stock, price_data)
                msg += stock_msg + "\n"
        send_wx(msg)
        state["close_sent"] = True
        save_state(state)
        return
    
    if not is_trading_time():
        return
    
    # 开盘播报
    if now.hour == 9 and now.minute == 30 and not state.get("open_sent"):
        msg = f"🔔 【开盘播报】\n\n"
        for stock in STOCKS:
            price_data = get_price(stock["code"])
            if price_data:
                stock_msg, _, _ = format_stock(stock, price_data)
                msg += stock_msg + "\n"
        send_wx(msg)
        state["open_sent"] = True
        save_state(state)
        return
    
    # 整点播报（含持仓分析）
    current_hour = now.strftime("%H:00")
    if current_hour != state.get("last_hourly") and now.minute == 0:
        msg = f"⏰ 【{current_hour} 整点播报】\n"
        for stock in STOCKS:
            price_data = get_price(stock['code'])
            if price_data:
                stock_msg, _, _ = format_stock(stock, price_data)
                msg += stock_msg + "\n"
        # 添加持仓分析和建议
        msg += generate_advice()
        send_wx(msg)
        state["last_hourly"] = current_hour
        save_state(state)
        return
    
    # 实时监控每个股票
    for stock in STOCKS:
        price_data = get_price(stock["code"])
        if not price_data:
            continue
        
        price = price_data["price"]
        change_pct = price_data["change_pct"]
        key = stock["ts_code"]
        
        # 初始化股票状态
        if key not in state.get("alerted", {}):
            state.setdefault("alerted", {})[key] = []
        
        # ========== 止盈止损优先检查（不受return影响）==========
        if stock["cost"]:
            tp = stock["cost"] * (1 + stock["tp_pct"] / 100)
            sl = stock["cost"] * (1 - stock["sl_pct"] / 100)
            cost_pct = (price - stock["cost"]) / stock["cost"] * 100
            profit = (price - stock["cost"]) * stock["shares"]
            
            # 止盈触发
            if price >= tp and "tp" not in state["alerted"][key]:
                msg = f"🎯 【{stock['name']} 止盈触发！】\n"
                msg += f"现价 {price:.3f}  |  盈利 {profit:+.0f}元\n"
                msg += f"建议卖出！\n━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append("tp")
                save_state(state)
                continue
            
            # 止损触发
            if price <= sl and "sl" not in state["alerted"][key]:
                msg = f"🚨 【{stock['name']} 止损触发！】\n"
                msg += f"现价 {price:.3f}  |  亏损 {profit:.0f}元\n"
                msg += f"建议清仓！\n━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append("sl")
                save_state(state)
                continue
            
            # 逼近止损（距止损≤3%，每天提醒一次）
            dist_sl = (1 - sl / price) * 100 if price > sl else 0
            if 0 < dist_sl <= 3 and "near_sl" not in state["alerted"][key]:
                msg = f"⚠️ 【{stock['name']} 逼近止损！】\n"
                msg += f"现价 {price:.3f}  |  止损 {sl:.3f}\n"
                msg += f"距止损仅 {dist_sl:.1f}%  |  浮亏 {profit:.0f}元\n"
                msg += f"⚠️ 注意风险！\n━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append("near_sl")
                save_state(state)
                continue
            
            # 逼近止盈（距止盈≤5%）
            dist_tp = (tp / price - 1) * 100
            if 0 < dist_tp <= 5 and "near_tp" not in state["alerted"][key]:
                msg = f"🎯 【{stock['name']} 逼近止盈！】\n"
                msg += f"现价 {price:.3f}  |  止盈 {tp:.3f}\n"
                msg += f"距止盈仅 {dist_tp:.1f}%  |  浮盈 {profit:+.0f}元\n"
                msg += f"准备减仓！\n━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append("near_tp")
                save_state(state)
                continue
        
        # 涨停跌停提醒（支持多次触发）
        # 获取上一次状态
        prev_limit_up = state.get("prev_limit_up", {}).get(key, False)
        prev_limit_down = state.get("prev_limit_down", {}).get(key, False)
        
        is_limit_up = change_pct >= 9.95
        is_limit_down = change_pct <= -9.95
        
        # 涨停状态变化
        if is_limit_up and not prev_limit_up:
            msg = f"🔴 【{stock['name']} 涨停！】\n"
            msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
            if stock["cost"]:
                cost_pct = (price - stock["cost"]) / stock["cost"] * 100
                profit = (price - stock["cost"]) * stock["shares"]
                msg += f"成本涨幅 {cost_pct:+.1f}%  |  盈亏 {profit:+.0f}元\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━"
            send_wx(msg)
        elif not is_limit_up and prev_limit_up:
            msg = f"⚠️ 【{stock['name']} 涨停打开！】\n"
            msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━"
            send_wx(msg)
        
        # 跌停状态变化
        if is_limit_down and not prev_limit_down:
            msg = f"🟢 【{stock['name']} 跌停！】\n"
            msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
            if stock["cost"]:
                cost_pct = (price - stock["cost"]) / stock["cost"] * 100
                profit = (price - stock["cost"]) * stock["shares"]
                msg += f"成本涨幅 {cost_pct:+.1f}%  |  盈亏 {profit:+.0f}元\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━"
            send_wx(msg)
        elif not is_limit_down and prev_limit_down:
            msg = f"⚠️ 【{stock['name']} 跌停打开！】\n"
            msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━"
            send_wx(msg)
        
        # 更新状态
        state.setdefault("prev_limit_up", {})[key] = is_limit_up
        state.setdefault("prev_limit_down", {})[key] = is_limit_down
        save_state(state)
        
        # 逼近涨停跌停提醒（只触发一次）
        if change_pct >= 8 and not is_limit_up:
            alert_key = "near_limit_up"
            if alert_key not in state["alerted"][key]:
                msg = f"📈 【{stock['name']} 逼近涨停！】\n"
                msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append(alert_key)
                save_state(state)
                return
        elif change_pct <= -8 and not is_limit_down:
            alert_key = "near_limit_down"
            if alert_key not in state["alerted"][key]:
                msg = f"📉 【{stock['name']} 逼近跌停！】\n"
                msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append(alert_key)
                save_state(state)
                return
        
        # 今日涨跌幅提醒（整数%）
        pct_int = round(change_pct)
        if -10 <= pct_int <= 10:
            alert_key = f"pct_{pct_int}"
            if alert_key not in state["alerted"][key]:
                msg = f"{'📈' if pct_int > 0 else '📉' if pct_int < 0 else '➡️'} 【{stock['name']} 涨跌幅提醒】\n"
                msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                
                if stock["cost"]:
                    cost_pct = (price - stock["cost"]) / stock["cost"] * 100
                    profit = (price - stock["cost"]) * stock["shares"]
                    msg += f"成本涨幅 {cost_pct:+.1f}%  |  盈亏 {'+' if profit >= 0 else ''}{profit:.0f}元\n"
                
                msg += f"━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append(alert_key)
                save_state(state)
                return
        
        # 成本线提醒（0.5%间隔）
        if stock["cost"]:
            cost_pct = (price - stock["cost"]) / stock["cost"] * 100
            cost_pct_rounded = round(cost_pct * 2) / 2
            
            alert_key = f"cost_{cost_pct_rounded}"
            if alert_key not in state["alerted"][key]:
                profit = (price - stock["cost"]) * stock["shares"]
                emoji = "💰" if cost_pct >= 0 else "⚠️"
                msg = f"{emoji} 【{stock['name']} 成本线提醒】\n"
                msg += f"现价 {price:.3f}  |  成本涨幅 {cost_pct:+.1f}%\n"
                msg += f"盈亏 {'+' if profit >= 0 else ''}{profit:.0f}元\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append(alert_key)
                save_state(state)
                return
        
        # 持仓天数提醒
        if stock["cost"] and stock.get("buy_date"):
            holding_days = get_trading_days(stock["buy_date"])
            if holding_days >= MAX_HOLD_DAYS and "hold_days" not in state["alerted"][key]:
                profit = (price - stock["cost"]) * stock["shares"]
                msg = f"⏰ 【{stock['name']} 持仓超{MAX_HOLD_DAYS}天！】\n"
                msg += f"现价 {price:.3f}  |  盈亏 {profit:+.0f}元\n"
                msg += f"持仓 {holding_days}天  |  建议减仓或清仓\n━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append("hold_days")
                save_state(state)
                return
        
        # 观察股票特殊提醒
        if not stock["cost"]:
            if change_pct >= 9.9 and "limit_up" not in state["alerted"][key]:
                msg = f"🚀 【{stock['name']} 涨停！】\n现价 {price:.3f}"
                send_wx(msg)
                state["alerted"][key].append("limit_up")
                save_state(state)
                return
            
            # 买入信号提醒
            # 信号1: 从大跌中恢复（跌幅收窄到-2%以内）
            if change_pct >= -2 and change_pct <= 0:
                # 检查之前是否大跌过（有pct_-5, -6, -7等记录）
                has_big_drop = any(k.startswith("pct_-") and int(k.split("_")[1]) <= -5 for k in state["alerted"].get(key, []))
                if has_big_drop and "buy_recovery" not in state["alerted"].get(key, []):
                    msg = f"💡 【{stock['name']} 企稳信号】\n"
                    msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                    msg += f"从大跌中恢复，可考虑建仓\n"
                    suggested_shares = int(SINGLE_POSITION_AMOUNT / price / 100) * 100
                    if suggested_shares > 0:
                        msg += f"建议仓位: {suggested_shares}股({suggested_shares * price:.0f}元)"
                    send_wx(msg)
                    state.setdefault("alerted", {}).setdefault(key, []).append("buy_recovery")
                    save_state(state)
                    return
            
            # 信号2: 跌幅收窄（从-5%以上收窄到-3%以内）
            if change_pct >= -3 and change_pct <= 0:
                prev_pcts = [k for k in state["alerted"].get(key, []) if k.startswith("pct_-")]
                if prev_pcts:
                    min_pct = min(int(k.split("_")[1]) for k in prev_pcts)
                    if min_pct <= -5 and "buy_narrow" not in state["alerted"].get(key, []):
                        msg = f"📉➡️📈 【{stock['name']} 跌幅收窄】\n"
                        msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                        msg += f"从{min_pct}%收窄，关注反弹机会"
                        send_wx(msg)
                        state.setdefault("alerted", {}).setdefault(key, []).append("buy_narrow")
                        save_state(state)
                        return
            
            # 信号3: 转涨信号（从跌转涨）
            if change_pct > 0 and "buy_turn_up" not in state["alerted"].get(key, []):
                has_drop = any(k.startswith("pct_-") for k in state["alerted"].get(key, []))
                if has_drop:
                    msg = f"📈 【{stock['name']} 转涨！】\n"
                    msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                    msg += f"止跌反弹，可考虑入场"
                    send_wx(msg)
                    state.setdefault("alerted", {}).setdefault(key, []).append("buy_turn_up")
                    save_state(state)
                    return
    
    save_state(state)

if __name__ == "__main__":
    main()
