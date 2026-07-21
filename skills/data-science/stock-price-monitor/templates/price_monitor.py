#!/usr/bin/env python3
"""
股票价格监控脚本模板 v12
功能：整数涨跌幅提醒 + 成本线提醒(0.5%间隔) + 止盈止损 + 盘口分析

⚠️ 关键修复：
- 脚本必须自己加载.env文件（cronjob不会自动加载！）
- STATE_FILE必须用绝对路径（expanduser()会导致路径嵌套）
- 收盘判断要在交易时间检查之前
- 成本线提醒用0.5%间隔，不要四舍五入到整数%
- API必须用fltt=2参数（不用除法，直接返回正确小数）
- 脚本不要有print语句（cronjob会推送给用户，太吵）
"""

import urllib.request
import json
import datetime
import os

# ========== 加载.env文件（关键！cronjob不会自动加载）==========
def load_env():
    """自动加载.env文件"""
    env_paths = [
        "/home/jmy/.hermes/profiles/eastmoney-bot/.env",  # 绝对路径优先
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

# ========== 配置区域（修改这里）==========

# 企业微信Webhook（从环境变量读取）
WX_WEBHOOK = os.environ.get("WX_WEBHOOK", "")

# 股票配置
STOCK_CODE = "0.159599"    # 东财secid格式（ETF用0.开头）
STOCK_NAME = "芯片ETF"
DB_TS_CODE = "159599"      # 数据库中的股票代码

# 买入信息
AVG_COST = 3.528           # 持仓均价
SHARES = 8500              # 持仓数量
BUY_DATE = "2026-06-24"    # 买入日期（用于计算持仓天数）

# 止盈止损（固定，基于买入价）
TAKE_PROFIT_PCT = 10       # 止盈百分比
STOP_LOSS_PCT = 5          # 止损百分比
HOLD_DAYS = "3-5天"

# 计算止盈止损价
COST_TP = AVG_COST * (1 + TAKE_PROFIT_PCT / 100)
COST_SL = AVG_COST * (1 - STOP_LOSS_PCT / 100)

STATE_FILE = "/home/jmy/.hermes/profiles/eastmoney-bot/.monitor_state.json"  # ⚠️ 必须用绝对路径

# 成本线预警配置（0.5%间隔）
COST_ALERTS = [-5.0, -4.5, -4.0, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5,
               0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,
               6.0, 7.0, 8.0, 9.0, 10.0]

# ========== 核心函数（一般不改）==========

def send_wx(content):
    """推送企业微信群"""
    if not WX_WEBHOOK:
        return False
    data = json.dumps({"msgtype": "text", "text": {"content": content}}).encode()
    req = urllib.request.Request(WX_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False

def calculate_rsi(closes, period=14):
    """计算RSI"""
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

def get_realtime_rsi():
    """获取实时RSI"""
    try:
        url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?secid={STOCK_CODE}&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=30"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("data") and data["data"].get("klines"):
                klines = data["data"]["klines"]
                closes = [float(k.split(",")[2]) for k in klines]
                rsi = calculate_rsi(closes)
                if rsi is not None:
                    return rsi
    except Exception:
        pass
    return 50

def get_price():
    """获取实时行情（⚠️ 必须用fltt=2，直接返回正确小数）"""
    url = f"http://push2delay.eastmoney.com/api/qt/stock/get?secid={STOCK_CODE}&fltt=2&fields=f43,f44,f45,f46,f47,f48,f49,f60,f161,f170,f85"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())["data"]
            price = data["f43"]        # fltt=2直接返回小数，无需除法
            high = data["f44"]
            low = data["f45"]
            yesterday = data["f60"]
            outer = data["f49"]        # ⚠️ 外盘是f49，不是f162
            inner = data["f161"]       # 内盘是f161
            change_pct = data["f170"]  # 直接是百分比，如3.11表示+3.11%
            volume = data["f47"]
            circ_shares = data["f85"]
            amplitude = (high - low) / yesterday * 100 if yesterday > 0 else 0
            turnover = volume * 100 / circ_shares * 100 if circ_shares > 0 else 0
            total_vol = outer + inner
            outer_ratio = outer / total_vol * 100 if total_vol > 0 else 50
            return {
                "price": price, "yesterday": yesterday, "change_pct": change_pct,
                "outer": outer, "inner": inner, "outer_ratio": outer_ratio,
                "amplitude": amplitude, "turnover": turnover,
            }
    except Exception:
        return None

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"alerted": {}, "open_sent": False, "close_sent": False, "last_hourly": None, "today": None}

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
    price = price_data["price"]
    change_pct = price_data["change_pct"]

    # 基于成本的涨跌幅（保留1位小数）
    cost_pct = (price - AVG_COST) / AVG_COST * 100
    profit_amount = (price - AVG_COST) * SHARES
    total_value = price * SHARES

    # 持仓天数（按交易日近似计算）
    today = datetime.date.today()
    buy_date_obj = datetime.datetime.strptime(BUY_DATE, "%Y-%m-%d").date()
    holding_days = (today - buy_date_obj).days

    sign_today = "+" if change_pct >= 0 else ""
    sign_cost = "+" if cost_pct >= 0 else ""
    sign_profit = "+" if profit_amount >= 0 else ""

    # 成本线进度条
    if cost_pct >= 0:
        progress = min(cost_pct / TAKE_PROFIT_PCT * 100, 100)
        bar = "▓" * int(progress / 10) + "░" * (10 - int(progress / 10))
        target_info = f"距止盈 {COST_TP:.3f}（{TAKE_PROFIT_PCT-cost_pct:.1f}%）"
    else:
        progress = min(abs(cost_pct) / STOP_LOSS_PCT * 100, 100)
        bar = "▓" * int(progress / 10) + "░" * (10 - int(progress / 10))
        target_info = f"距止损 {COST_SL:.3f}（{STOP_LOSS_PCT-abs(cost_pct):.1f}%）"

    msg = f"{tag}📈 {STOCK_NAME} {DB_TS_CODE}\n"
    msg += f"\n💰 现价 {price:.3f}  |  今日 {sign_today}{change_pct:.2f}%\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 成本分析\n"
    msg += f"   成本价 {AVG_COST:.3f}\n"
    msg += f"   成本涨幅 {sign_cost}{cost_pct:.1f}%\n"
    msg += f"   [{bar}] {'盈利' if cost_pct >= 0 else '亏损'}\n"
    msg += f"   {target_info}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"💼 持仓盈亏\n"
    msg += f"   持仓 {SHARES}股  市值 {total_value:.0f}元\n"
    msg += f"   盈亏 {sign_profit}{profit_amount:.0f}元\n"
    msg += f"   持仓天数 {holding_days}天\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📈 盘口数据\n"
    msg += f"   振幅 {price_data['amplitude']:.2f}%  |  换手 {price_data['turnover']:.2f}%\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🎯 止盈 {COST_TP:.3f}（+{TAKE_PROFIT_PCT}%）\n"
    msg += f"🚨 止损 {COST_SL:.3f}（-{STOP_LOSS_PCT}%）"
    return msg

def main():
    now = datetime.datetime.now()
    state = load_state()
    
    # ⚠️ 每日状态重置（新的一天清空所有提醒记录）
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
    cost_pct = (price - AVG_COST) / AVG_COST * 100
    key = DB_TS_CODE

    # 初始化股票状态
    if key not in state.get("alerted", {}):
        state.setdefault("alerted", {})[key] = []

    # 9:30开盘播报
    if now.hour == 9 and now.minute == 30 and not state.get("open_sent"):
        msg = f"🔔 【开盘播报】\n\n" + format_status(price_data)
        send_wx(msg)
        state["open_sent"] = True
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

    # 今日涨跌幅提醒
    current_pct_int = round(change_pct)
    if -10 <= current_pct_int <= 10:
        alert_key = f"pct_{current_pct_int}"
        if alert_key not in state["alerted"][key]:
            if current_pct_int == 0:
                emoji = "➡️"
                direction = "平盘"
            elif current_pct_int > 0:
                emoji = "📈"
                direction = "涨"
            else:
                emoji = "📉"
                direction = "跌"

            msg = f"{emoji} 【今日{direction}幅提醒】\n"
            msg += f"{STOCK_NAME} 现价 {price:.3f}（{change_pct:+.2f}%）\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"今日{direction}幅达到 {current_pct_int}%\n"
            msg += f"成本涨幅 {cost_pct:+.1f}%\n\n"
            msg += format_status(price_data)

            send_wx(msg)
            state["alerted"][key].append(alert_key)
            save_state(state)
            return

    # ========== 成本线涨跌幅提醒（0.5%间隔）==========
    cost_pct_rounded = round(cost_pct * 2) / 2  # 四舍五入到0.5
    cost_key = f"cost_{cost_pct_rounded}"

    if cost_key not in state["alerted"][key]:
        for alert_pct in COST_ALERTS:
            if abs(cost_pct_rounded - alert_pct) < 0.25:
                if alert_pct == 0:
                    emoji = "➡️"
                    msg_title = "回到成本线"
                elif alert_pct > 0:
                    emoji = "💰"
                    msg_title = f"盈利{alert_pct:.1f}%"
                else:
                    emoji = "⚠️"
                    msg_title = f"亏损{abs(alert_pct):.1f}%"

                profit_amount = (price - AVG_COST) * SHARES

                msg = f"{emoji} 【成本线提醒 - {msg_title}】\n"
                msg += f"{STOCK_NAME} 现价 {price:.3f}\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"📊 成本价 {AVG_COST:.3f}\n"
                msg += f"📊 成本涨幅 {cost_pct:+.1f}%\n"
                msg += f"💼 盈亏 {'+' if profit_amount >= 0 else ''}{profit_amount:.0f}元\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                msg += format_status(price_data)

                send_wx(msg)
                state["alerted"][key].append(cost_key)
                save_state(state)
                return

    # RSI预警
    current_rsi = get_realtime_rsi()
    if current_rsi is not None:
        rsi_key = None
        if current_rsi > 90:
            rsi_key = "rsi_extreme_overbought"
            msg = f"🔴 【RSI极度超买警告！】\n{STOCK_NAME} 现价 {price:.3f}\nRSI={current_rsi:.1f}\n成本涨幅 {cost_pct:+.1f}%"
        elif current_rsi > 80:
            rsi_key = "rsi_overbought"
            msg = f"⚠️ 【RSI超买警告】\n{STOCK_NAME} 现价 {price:.3f}\nRSI={current_rsi:.1f}\n成本涨幅 {cost_pct:+.1f}%"
        elif current_rsi < 20:
            rsi_key = "rsi_oversold"
            msg = f"🟢 【RSI超卖机会】\n{STOCK_NAME} 现价 {price:.3f}\nRSI={current_rsi:.1f}\n成本涨幅 {cost_pct:+.1f}%"
        
        if rsi_key and rsi_key not in state["alerted"][key]:
            send_wx(msg)
            state["alerted"][key].append(rsi_key)
            save_state(state)
            return

    # 持仓天数提醒
    today = datetime.date.today()
    buy_date_obj = datetime.datetime.strptime(BUY_DATE, "%Y-%m-%d").date()
    holding_days = (today - buy_date_obj).days

    hold_key = None
    if holding_days >= 5:
        hold_key = "hold_5days"
        msg = f"⏰ 【持仓第{holding_days}天 - 减仓提醒】\n{STOCK_NAME} 现价 {price:.3f}\n成本涨幅 {cost_pct:+.1f}%\n建议减仓50%"
    elif holding_days == 3:
        hold_key = "hold_3days"
        msg = f"⏰ 【持仓第3天 - 准备减仓】\n{STOCK_NAME} 现价 {price:.3f}\n成本涨幅 {cost_pct:+.1f}%"
    
    if hold_key and hold_key not in state["alerted"][key]:
        send_wx(msg)
        state["alerted"][key].append(hold_key)
        save_state(state)
        return

    # 止盈止损
    if price >= COST_TP and "take_profit" not in state["alerted"][key]:
        msg = f"🎯 【止盈触发！】\n{STOCK_NAME} 现价 {price:.3f}\n成本涨幅 {cost_pct:+.1f}%\n建议卖出"
        send_wx(msg)
        state["alerted"][key].append("take_profit")
        save_state(state)
        return

    if price <= COST_SL and "stop_loss" not in state["alerted"][key]:
        msg = f"🚨 【止损触发！】\n{STOCK_NAME} 现价 {price:.3f}\n成本涨幅 {cost_pct:+.1f}%\n建议清仓"
        send_wx(msg)
        state["alerted"][key].append("stop_loss")
        save_state(state)
        return

    save_state(state)

if __name__ == "__main__":
    main()
