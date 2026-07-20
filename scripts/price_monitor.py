#!/usr/bin/env python3
"""
股票价格监控脚本 v14
监控持仓+扫描结果
功能：仓位管理 + 持仓天数提醒 + 整数涨跌幅提醒 + 止盈止损 + 盘口分析
+ 交易通知（买卖推送）
"""

import urllib.request
import json
import datetime
import os

# ========== 加载.env文件 ==========
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

# ========== 配置区域 ==========
WX_WEBHOOK = os.environ.get("WX_WEBHOOK", "")

# ========== 仓位管理配置 ==========
TOTAL_CAPITAL = 73390  # 7/15 东睦清仓330@31.27(+228)，空仓
SINGLE_POSITION_PCT = 20  # 单只股票仓位比例20%
SINGLE_POSITION_AMOUNT = TOTAL_CAPITAL * SINGLE_POSITION_PCT / 100  # 单只股票金额14575元
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
        # 2026-07-09 清仓: 减半1800@3.707(±0) + 清仓1800@3.730(+41) = +41
        # 2026-07-16 买入2600@3.237 → 7/17 补200@2.974 → 2800股 加权3.218
        "code": "0.159599",
        "name": "芯片ETF",
        "ts_code": "159599",
        "cost": 3.218,
        "shares": 2800,
        "buy_date": "2026-07-16",
        "tp_pct": 10,
        "sl_pct": 3,
        "target_buy": None,
        "target_shares": None,
        "type": "持仓"
    },
    {
        # 2026-07-14 清仓: 1000@8.312（止损），买入8.585，亏-273（-3.18%）
        "code": "1.518880",
        "name": "黄金ETF",
        "ts_code": "518880",
        "cost": None,
        "shares": 0,
        "buy_date": None,
        "tp_pct": 10,
        "sl_pct": 3,  # ETF止损3%
        "target_buy": 8.25,
        "target_shares": 1000,
        "type": "观察"
    },
    {
        # 2026-07-08 清仓@33.22 (-854)
        # 2026-07-14 买入300@30.58 → 7/15 清仓330@31.27(+228)，净亏626
        # 2026-07-16 买入400@30.40 + 补200@29.44 → 7/17 补300@27.19 → T卖200@27.85 → 700股 加权29.479
        "code": "1.600114",
        "name": "东睦股份",
        "ts_code": "600114",
        "cost": 28.435,
        "shares": 1000,
        "buy_date": "2026-07-16",
        "tp_pct": 15,
        "sl_pct": 8,
        "target_buy": None,
        "target_shares": None,
        "type": "持仓"
    },
    {
        "code": "1.600888",
        "name": "新疆众和",
        "ts_code": "600888",
        "cost": 10.297,
        "shares": 1200,
        "buy_date": "2026-07-16",
        "tp_pct": 15,
        "sl_pct": 8,
        "target_buy": None,
        "target_shares": None,
        "type": "持仓"
    },
]

STATE_FILE = "/home/jmy/.hermes/profiles/eastmoney-bot/.monitor_state.json"

# 历史累计亏损（用于计算回本价）
LOSS_HISTORY = {
    "600114": {"loss": 626, "name": "东睦股份"},  # 7/8亏854 + 7/15赚228 = 净亏626
    "518880": {"loss": 273, "name": "黄金ETF"},    # 7/14 止损亏273
}

# ========== 核心函数 ==========

def send_wx(msg):
    """发送企业微信通知"""
    if not WX_WEBHOOK:
        return
    try:
        data = json.dumps({"msgtype": "text", "text": {"content": msg}}).encode()
        req = urllib.request.Request(WX_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        pass

def load_state():
    """加载状态文件"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_state(state):
    """保存状态文件"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, ensure_ascii=False)
    except:
        pass

def get_price(code):
    """获取股票实时价格"""
    os.environ['NO_PROXY'] = '*'
    try:
        url = f"http://push2delay.eastmoney.com/api/qt/stock/get?secid={code}&fltt=2&fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f169,f170,f60"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        d = data.get("data", {})
        return {
            "price": d.get("f43", 0),
            "high": d.get("f44", 0),
            "low": d.get("f45", 0),
            "open": d.get("f46", 0),
            "volume": d.get("f47", 0),
            "amount": d.get("f48", 0),
            "change_pct": d.get("f170", 0),
            "yesterday_close": d.get("f60", 0),
        }
    except:
        return None

def get_rsi(code):
    """获取RSI"""
    try:
        secid_map = {"0.002167": "0.002167", "0.159599": "0.159599", "1.518880": "1.518880", "1.600114": "1.600114", "1.600888": "1.600888"}
        secid = secid_map.get(code, code)
        url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=30"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        
        klines = data.get("data", {}).get("klines", [])
        if len(klines) < 15:
            return None
        
        closes = [float(k.split(",")[2]) for k in klines[-30:]]
        
        # RSI计算
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        period = 14
        if len(deltas) < period:
            return None
        
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
    except:
        return None

def get_kline_analysis(code):
    """获取K线技术分析：RSI + MA + 近期高低点"""
    try:
        secid_map = {"0.002167": "0.002167", "0.159599": "0.159599", "1.518880": "1.518880", "1.600114": "1.600114", "1.600888": "1.600888"}
        secid = secid_map.get(code, code)
        url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=30"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        
        klines = data.get("data", {}).get("klines", [])
        if len(klines) < 15:
            return None
        
        closes = [float(k.split(",")[2]) for k in klines]
        highs = [float(k.split(",")[3]) for k in klines]
        lows = [float(k.split(",")[4]) for k in klines]
        
        n = len(closes)
        result = {}
        
        # RSI
        deltas = [closes[i] - closes[i-1] for i in range(1, n)]
        period = 14
        if len(deltas) >= period:
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            for i in range(period, len(deltas)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss > 0:
                result["rsi"] = 100 - (100 / (1 + avg_gain / avg_loss))
            else:
                result["rsi"] = 100
        else:
            result["rsi"] = None
        
        # MA
        if n >= 5:
            result["ma5"] = sum(closes[-5:]) / 5
        if n >= 10:
            result["ma10"] = sum(closes[-10:]) / 10
        if n >= 20:
            result["ma20"] = sum(closes[-20:]) / 20
        
        # 近期高低点
        result["low_10d"] = min(lows[-10:])
        result["high_10d"] = max(highs[-10:])
        result["low_20d"] = min(lows[-20:]) if n >= 20 else result.get("low_10d")
        
        # 周涨跌（5个交易日）
        if n >= 6:
            result["week_chg"] = (closes[-1] / closes[-6] - 1) * 100
        
        return result
    except:
        return None

def is_trading_time():
    """判断是否在交易时间"""
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (datetime.time(9, 25) <= t <= datetime.time(11, 31)) or \
           (datetime.time(12, 55) <= t <= datetime.time(15, 1))


def check_monitor_changes(state):
    """检测监控列表变更（新增/移除），首次运行不报警"""
    # 构建当前监控快照：{ts_code: (name, type)}
    current = {}
    for s in STOCKS:
        current[s["ts_code"]] = (s["name"], s["type"])
    
    snapshot = state.get("stocks_snapshot", {})
    
    # 首次运行：保存快照，不报警
    if not snapshot:
        state["stocks_snapshot"] = current
        save_state(state)
        return None
    
    # 对比差异
    added = {}    # 新增的
    removed = {}  # 移除的
    changed = {}  # type变化的（观察→持仓 或 持仓→观察）
    
    for code, (name, stype) in current.items():
        if code not in snapshot:
            added[code] = (name, stype)
        elif snapshot[code] != (name, stype):
            old_name, old_type = snapshot[code]
            if old_type != stype:
                changed[code] = (name, old_type, stype)
    
    for code, (name, stype) in snapshot.items():
        if code not in current:
            removed[code] = (name, stype)
    
    # 更新快照
    state["stocks_snapshot"] = current
    save_state(state)
    
    # 有变更才推送
    if not added and not removed and not changed:
        return None
    
    msg = "📋 【监控列表变更】\n\n"
    
    for code, (name, stype) in added.items():
        emoji = "🔴" if stype == "持仓" else "🟡"
        msg += f"  ➕ {emoji} 新增{stype}: {name} ({code})\n"
    
    for code, (name, stype) in removed.items():
        emoji = "🔴" if stype == "持仓" else "🟡"
        msg += f"  ➖ {emoji} 移除{stype}: {name} ({code})\n"
    
    for code, (name, old_type, new_type) in changed.items():
        msg += f"  🔄 {name} ({code}): {old_type} → {new_type}\n"
    
    return msg

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
        
        if stock['cost']:
            has_position = True
            cost_pct = (price - stock['cost']) / stock['cost'] * 100
            tp = stock['cost'] * (1 + stock['tp_pct'] / 100)
            sl = stock['cost'] * (1 - stock['sl_pct'] / 100)
            dist_tp = (tp - price) / price * 100
            dist_sl = (price - sl) / price * 100
            
            msg += f"🎯 {stock['name']}:\n"
            if price >= tp:
                msg += "🚨 已到止盈位！建议立即减仓\n"
            elif price <= sl:
                msg += "🔴 已到止损位！建议清仓\n"
            elif dist_tp <= 5:
                msg += f"🎯 逼近止盈(距{dist_tp:.1f}%)，冲高减仓\n"
            elif cost_pct >= 8:
                msg += "💰 浮盈8%+，可考虑锁定利润\n"
            elif cost_pct <= -3:
                msg += f"⚠️ 浮亏3%+，注意风险\n"
            
            # T+1检查
            if stock.get('buy_date'):
                holding_days = get_trading_days(stock['buy_date'])
                if holding_days >= MAX_HOLD_DAYS:
                    msg += f"⏰ 持仓{holding_days}天超限！建议减仓\n"
        else:
            # 观察股票建议
            if change_pct >= 8:
                msg += f"📈 {stock['name']}: 大涨中，不追高\n"
            elif change_pct <= -5:
                msg += f"📉 {stock['name']}: 大跌中，关注机会\n"
    
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
            "today": today_str,
            "prev_limit_up": {},
            "prev_limit_down": {},
            "market_warned": False,
            "pending_trades": state.get("pending_trades", []),  # 保留跨日未发送的交易通知
            "t_targets": state.get("t_targets", {}),            # 保留做T目标
            "stocks_snapshot": state.get("stocks_snapshot", {}), # 保留监控快照
        }
        save_state(state)
    
    # ======== 交易通知（pending_trades队列）========
    pending = state.get("pending_trades", [])
    if pending:
        for trade in pending:
            send_wx(trade["msg"])
        state["pending_trades"] = []
        save_state(state)
    
    # ======== 监控列表变更检测 ========
    change_msg = check_monitor_changes(state)
    if change_msg:
        send_wx(change_msg)
    
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
    
    # ========== 大盘风控（每天检查一次）==========
    if "market_warned" not in state:
        try:
            mkt_url = "http://push2delay.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f4,f12,f14&secids=1.000001,0.399001,0.399006"
            mkt_req = urllib.request.Request(mkt_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(mkt_req, timeout=5) as resp:
                mkt_data = json.loads(resp.read())
            indices = mkt_data.get("data", {}).get("diff", [])
            max_drop = 0
            max_drop_name = ""
            for idx in indices:
                pct = idx.get("f3", 0)
                if pct < max_drop:
                    max_drop = pct
                    max_drop_name = idx.get("f14", "")
            
            if max_drop <= -3:
                msg = f"🚨 【大盘暴跌警告！】\n"
                msg += f"{max_drop_name} 跌幅 {max_drop:.2f}%\n"
                msg += f"⚠️ 系统性风险！建议暂停买入\n"
                msg += f"📋 持仓注意止损\n━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["market_warned"] = True
                save_state(state)
            elif max_drop <= -2:
                msg = f"⚠️ 【大盘下跌警告】\n"
                msg += f"{max_drop_name} 跌幅 {max_drop:.2f}%\n"
                msg += f"📋 市场偏弱，控制仓位\n━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["market_warned"] = True
                save_state(state)
        except:
            pass
    
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
                msg += stock_msg
                # 做T目标距离
                t_targets = state.get("t_targets", {})
                if stock['ts_code'] in t_targets and stock.get("cost"):
                    t = t_targets[stock['ts_code']]
                    dist = (price_data['price'] - t['target']) / t['target'] * 100
                    emoji = "✅" if dist >= 0 else "⏳"
                    msg += f"🎯 做T卖出 {t['target']:.2f} {emoji}距{dist:+.1f}%  {t['shares']}股\n"
                if stock.get("target_buy") and stock.get("cost"):
                    tb = stock['target_buy']
                    dist_tb = (price_data['price'] - tb) / tb * 100
                    emoji = "🔔" if dist_tb <= 0 else "⏳"
                    msg += f"🔻 补仓目标 {tb:.2f} {emoji}距{dist_tb:+.1f}%  {stock.get('target_shares',0)}股\n"
                msg += "\n"
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
        
        # ========== RSI极端值预警 ==========
        if stock["cost"]:
            rsi = get_rsi(stock["code"])
            if rsi is not None:
                if rsi > 90 and "rsi_overbought_90" not in state["alerted"][key]:
                    profit = (price - stock["cost"]) * stock["shares"]
                    msg = f"🔴 【{stock['name']} RSI极度超买！】\n"
                    msg += f"RSI(14) = {rsi:.1f}\n"
                    msg += f"现价 {price:.3f}  |  盈亏 {profit:+.0f}元\n"
                    msg += f"⚠️ 极度超买信号，回调概率极大\n"
                    msg += f"🎯 建议立即减仓！\n━━━━━━━━━━━━━━━━━━━━"
                    send_wx(msg)
                    state["alerted"][key].append("rsi_overbought_90")
                    save_state(state)
                    continue
                elif rsi > 80 and "rsi_overbought_80" not in state["alerted"][key]:
                    profit = (price - stock["cost"]) * stock["shares"]
                    msg = f"⚠️ 【{stock['name']} RSI超买】\n"
                    msg += f"RSI(14) = {rsi:.1f}\n"
                    msg += f"现价 {price:.3f}  |  盈亏 {profit:+.0f}元\n"
                    msg += f"📋 超买区域，注意回调风险\n━━━━━━━━━━━━━━━━━━━━"
                    send_wx(msg)
                    state["alerted"][key].append("rsi_overbought_80")
                    save_state(state)
                    continue
                elif rsi < 20 and "rsi_oversold" not in state["alerted"][key]:
                    msg = f"🟢 【{stock['name']} RSI超卖】\n"
                    msg += f"RSI(14) = {rsi:.1f}\n"
                    msg += f"现价 {price:.3f}\n"
                    msg += f"💡 超卖区域，可关注反弹机会\n━━━━━━━━━━━━━━━━━━━━"
                    send_wx(msg)
                    state["alerted"][key].append("rsi_oversold")
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
        
        # ========== 整数涨跌幅提醒（穿越即推，离开再回来也推，中间整数不漏）==========
        current_pct_int = round(change_pct)
        prev_key = f"prev_pct_{key}"
        prev_pct = state.get(prev_key)
        
        if prev_pct is not None and -10 <= current_pct_int <= 10 and current_pct_int != prev_pct:
            # 遍历prev到current之间所有整数（升序或降序）
            step = 1 if current_pct_int > prev_pct else -1
            for p in range(prev_pct + step, current_pct_int + step, step):
                if -10 <= p <= 10:
                    direction = "📈" if p > 0 else ("📉" if p < 0 else "➡️")
                    msg = f"{direction} 【{stock['name']} {p:+d}%】\n"
                    msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                    msg += f"━━━━━━━━━━━━━━━━━━━━"
                    send_wx(msg)
            state[prev_key] = current_pct_int
            save_state(state)
        elif prev_pct is None and -10 <= current_pct_int <= 10:
            # 首次记录，不推送
            state[prev_key] = current_pct_int
            save_state(state)
        
        # ========== 成本线提醒（0.5%间隔）==========
        if stock["cost"]:
            cost_pct = (price - stock["cost"]) / stock["cost"] * 100
            cost_pct_rounded = round(cost_pct * 2) / 2  # 四舍五入到0.5%
            
            # 检查是否在提醒范围内
            if -13 <= cost_pct_rounded <= 10:
                alert_key = f"cost_{cost_pct_rounded:.1f}"
                if alert_key not in state["alerted"].get(key, []):
                    direction = "📈" if cost_pct_rounded > 0 else ("📉" if cost_pct_rounded < 0 else "➡️")
                    msg = f"{direction} 【{stock['name']} 成本{cost_pct_rounded:+.1f}%】\n"
                    msg += f"现价 {price:.3f}  |  成本 {stock['cost']:.3f}\n"
                    msg += f"盈亏 {(price - stock['cost']) * stock['shares']:+.0f}元\n"
                    msg += f"━━━━━━━━━━━━━━━━━━━━"
                    send_wx(msg)
                    state["alerted"][key].append(alert_key)
                    save_state(state)
        
        # ========== 持仓天数提醒 ==========
        if stock.get("buy_date") and stock["cost"]:
            holding_days = get_trading_days(stock["buy_date"])
            if holding_days >= MAX_HOLD_DAYS and "hold_days" not in state["alerted"].get(key, []):
                msg = f"⏰ 【{stock['name']} 持仓超{MAX_HOLD_DAYS}天！】\n"
                msg += f"现价 {price:.3f}  |  持仓 {holding_days}天\n"
                msg += f"建议减仓或清仓\n━━━━━━━━━━━━━━━━━━━━"
                send_wx(msg)
                state["alerted"][key].append("hold_days")
                save_state(state)
        
        # ========== 做T目标价检查 ==========
        t_targets = state.get("t_targets", {})
        if key in t_targets and stock.get("cost"):
            t_info = t_targets[key]
            t_target_price = t_info["target"]
            alert_key = f"t_sell_{t_target_price}"
            if price >= t_target_price and alert_key not in state["alerted"].get(key, []):
                t_shares = t_info["shares"]
                msg = f"🎯 【{stock['name']} 做T目标到达！】\n\n"
                msg += f"💰 现价 {price:.3f}  ≥  目标 {t_target_price:.2f}\n"
                msg += f"📋 {t_info['note']}\n"
                msg += f"💡 卖出旧持仓中 {t_shares} 股"
                send_wx(msg)
                state["alerted"][key].append(alert_key)
                save_state(state)
        
        # ========== 观察/持仓股票目标买入价提醒（首次立即推送，之后每5分钟重复）==========
        target = stock.get("target_buy")
        if target and price <= target:
                existing = [a for a in state["alerted"].get(key, []) if a.startswith("target_buy_")]
                should_alert = False
                if not existing:
                    should_alert = True
                else:
                    try:
                        last_time = existing[-1].replace("target_buy_", "")
                        last_h, last_m = map(int, last_time.split(":"))
                        minutes_passed = (now.hour - last_h) * 60 + (now.minute - last_m)
                        if minutes_passed >= 5:
                            should_alert = True
                    except:
                        should_alert = True
                
                if should_alert:
                    # 获取技术分析数据
                    tech = get_kline_analysis(stock["code"])
                    rsi = tech.get("rsi") if tech else None
                    ma5 = tech.get("ma5") if tech else None
                    ma10 = tech.get("ma10") if tech else None
                    ma20 = tech.get("ma20") if tech else None
                    low_10d = tech.get("low_10d") if tech else None
                    high_10d = tech.get("high_10d") if tech else None
                    week_chg = tech.get("week_chg") if tech else None
                    
                    target_shares = stock.get("target_shares", 0)
                    if not target_shares:
                        target_shares = int(SINGLE_POSITION_AMOUNT / price / 100) * 100
                    position_amount = target_shares * price
                    
                    # 构建消息
                    msg = f"🎯 【{stock['name']} 触发买入信号！】\n\n"
                    msg += f"💰 现价 {price:.3f}  ≤  目标 {target:.2f}\n"
                    msg += f"   今日 {change_pct:+.2f}%  |  最高 {price_data['high']:.3f}  最低 {price_data['low']:.3f}\n\n"
                    
                    # 技术面
                    msg += "📈 技术面\n"
                    if rsi is not None:
                        rsi_label = "🔴极度超卖" if rsi < 30 else ("🟡偏低" if rsi < 40 else ("✅正常" if rsi < 70 else "⚠️偏高"))
                        msg += f"   RSI(14) = {rsi:.1f}  {rsi_label}\n"
                    if ma5 and ma10 and ma20:
                        msg += f"   MA5={ma5:.3f}  MA10={ma10:.3f}  MA20={ma20:.3f}\n"
                        dist_ma20 = (price / ma20 - 1) * 100
                        msg += f"   距MA20: {dist_ma20:+.1f}%\n"
                    if low_10d is not None and high_10d is not None:
                        msg += f"   10日区间: {low_10d:.3f} ~ {high_10d:.3f}\n"
                    if week_chg is not None:
                        msg += f"   近5日: {week_chg:+.1f}%\n"
                    
                    msg += "\n💵 买入计划\n"
                    msg += f"   仓位: {target_shares}股 × {price:.3f} = {position_amount:.0f}元\n"
                    
                    # 止损止盈
                    tp_pct = stock.get("tp_pct", 15)
                    sl_pct = stock.get("sl_pct", 8)
                    tp_price = price * (1 + tp_pct / 100)
                    sl_price = price * (1 - sl_pct / 100)
                    msg += f"   止盈: {tp_price:.3f} (+{tp_pct}%)  |  止损: {sl_price:.3f} (-{sl_pct}%)\n"
                    
                    # 回本价（如有历史亏损）
                    loss_info = LOSS_HISTORY.get(key)
                    if loss_info and target_shares > 0:
                        breakeven = price + loss_info["loss"] / target_shares
                        be_pct = (breakeven / price - 1) * 100
                        msg += f"   🔁 回本价: {breakeven:.2f} (需涨{be_pct:.1f}%，累计亏{loss_info['loss']}元)\n"
                    
                    # T+1判断
                    weekday = now.weekday()
                    weekday_names = ["周一","周二","周三","周四","周五","周六","周日"]
                    if weekday == 4:  # 周五
                        msg += f"\n⚠️ T+1: 今天是周五，买入后下周一才能卖出（锁仓3天），注意周末风险！\n"
                    elif weekday < 4:  # 周一~周四
                        next_day = weekday_names[weekday + 1]
                        msg += f"\n📅 T+1: 今天{weekday_names[weekday]}，{next_day}即可卖出\n"
                    
                    # 买入理由总结
                    reasons = []
                    if rsi is not None and rsi < 30:
                        reasons.append("RSI极度超卖")
                    if ma20 and price < ma20:
                        dist = (1 - price / ma20) * 100
                        if dist > 10:
                            reasons.append(f"跌破MA20达{dist:.0f}%")
                    if week_chg is not None and week_chg < -5:
                        reasons.append(f"近5日跌{abs(week_chg):.0f}%")
                    if reasons:
                        msg += f"\n💡 买入理由: {' + '.join(reasons)}，技术性反弹概率大\n"
                    
                    msg += "━━━━━━━━━━━━━━━━━━━━"
                    send_wx(msg)
                    time_key = f"target_buy_{now.hour:02d}:{now.minute:02d}"
                    state.setdefault("alerted", {}).setdefault(key, []).append(time_key)
                    save_state(state)

        # ========== 观察股票买入信号 ==========
        if not stock["cost"]:
            # 信号1: 从大跌中恢复
            if change_pct >= -2 and change_pct <= 0:
                has_big_drop = any(k.startswith("pct_down_") and int(k.split("_")[2]) >= 5 
                                 for k in state["alerted"].get(key, []))
                if has_big_drop and "buy_recovery" not in state["alerted"].get(key, []):
                    msg = f"💡 【{stock['name']} 企稳信号】\n"
                    msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                    msg += f"从大跌中恢复，可考虑建仓\n"
                    suggested_shares = int(SINGLE_POSITION_AMOUNT / price / 100) * 100
                    if suggested_shares > 0:
                        msg += f"建议仓位: {suggested_shares}股({suggested_shares * price:.0f}元)\n"
                    msg += f"━━━━━━━━━━━━━━━━━━━━"
                    send_wx(msg)
                    state.setdefault("alerted", {}).setdefault(key, []).append("buy_recovery")
                    save_state(state)
            
            # 信号2: 跌幅收窄
            if change_pct >= -3 and change_pct <= 0:
                prev_pcts = [k for k in state["alerted"].get(key, []) if k.startswith("pct_down_")]
                if prev_pcts:
                    max_drop = max(int(k.split("_")[2]) for k in prev_pcts)
                    if max_drop >= 5 and "buy_narrow" not in state["alerted"].get(key, []):
                        msg = f"📉➡️📈 【{stock['name']} 跌幅收窄】\n"
                        msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                        msg += f"从-{max_drop}%收窄，关注反弹机会\\n"
                        msg += f"━━━━━━━━━━━━━━━━━━━━"
                        send_wx(msg)
                        state.setdefault("alerted", {}).setdefault(key, []).append("buy_narrow")
                        save_state(state)
            
            # 信号3: 转涨信号
            if change_pct > 0 and "buy_turn_up" not in state["alerted"].get(key, []):
                has_drop = any(k.startswith("pct_down_") for k in state["alerted"].get(key, []))
                if has_drop:
                    msg = f"📈 【{stock['name']} 转涨！】\n"
                    msg += f"现价 {price:.3f}（{change_pct:+.2f}%）\n"
                    msg += f"止跌反弹，可考虑入场\n"
                    msg += f"━━━━━━━━━━━━━━━━━━━━"
                    send_wx(msg)
                    state.setdefault("alerted", {}).setdefault(key, []).append("buy_turn_up")
                    save_state(state)

if __name__ == "__main__":
    main()
