#!/usr/bin/env python3
"""
清仓自动化脚本 — 一键完成全部6步更新
用法: python3 clear_position.py <ts_code> <sell_price> <sell_shares> [target_buy] [target_buy_shares] [stock_name]

示例: python3 clear_position.py 600114 25.50 500 25.00 400 东睦股份
      python3 clear_position.py 159599 2.859 2800 2.90 2800 芯片ETF
"""
import sys, json, os, re
from datetime import datetime

SCRIPT_PATH = "/home/jmy/.hermes/profiles/eastmoney-bot/scripts/price_monitor.py"
STATE_PATH = "/home/jmy/.hermes/profiles/eastmoney-bot/.monitor_state.json"
REPO_PATH = "/home/jmy/.hermes/profiles/eastmoney-bot"

def main():
    if len(sys.argv) < 4:
        print("用法: clear_position.py <ts_code> <sell_price> <sell_shares> [target_buy] [target_buy_shares] [name]")
        sys.exit(1)
    
    ts_code = sys.argv[1]
    sell_price = float(sys.argv[2])
    sell_shares = int(sys.argv[3])
    target_buy = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] != "None" else None
    target_buy_shares = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] != "None" else None
    name = sys.argv[6] if len(sys.argv) > 6 else ts_code
    
    # 读取脚本
    with open(SCRIPT_PATH, 'r') as f:
        lines = f.readlines()
    
    # 解析当前成本和股数
    old_cost, old_shares, cost_line_idx, shares_line_idx = None, None, None, None
    found_ts = False
    for i, line in enumerate(lines):
        if f'"ts_code": "{ts_code}"' in line:
            found_ts = True
        if found_ts and i < len(lines):
            for j in range(i, min(i+15, len(lines))):
                if '"cost":' in lines[j]:
                    m = re.search(r'[\d.]+', lines[j].split('"cost":')[1]) if '"cost":' in lines[j] else None
                    if m:
                        old_cost = float(m.group())
                        cost_line_idx = j
                if '"shares":' in lines[j]:
                    m = re.search(r'(\d+)', lines[j].split('"shares":')[1])
                    if m:
                        old_shares = int(m.group())
                        shares_line_idx = j
                if old_cost is not None and old_shares is not None:
                    break
        if old_cost is not None and old_shares is not None:
            break
    
    if old_cost is None:
        old_cost = 0  # 已经清仓的，用0
    
    # 计算
    realized_loss = sell_shares * (sell_price - old_cost) if old_cost else sell_shares * sell_price
    remain = old_shares - sell_shares if old_shares else 0
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 更新cost/shares行
    if cost_line_idx:
        new_cost = round((old_shares * old_cost - sell_shares * sell_price) / remain, 3) if remain > 0 else "None"
        if remain > 0:
            lines[cost_line_idx] = f'        "cost": {new_cost},\n'
            lines[shares_line_idx] = f'        "shares": {remain},\n'
        else:
            lines[cost_line_idx] = f'        "cost": None,\n'
            if shares_line_idx:
                lines[shares_line_idx] = f'        "shares": 0,\n'
            # 找buy_date行
            for j in range(cost_line_idx, min(cost_line_idx+10, len(lines))):
                if '"buy_date":' in lines[j]:
                    lines[j] = f'        "buy_date": None,\n'
                if '"type":' in lines[j]:
                    lines[j] = f'        "type": "观察"\n'
                    break
    
    # 更新target_buy/target_buy_shares
    if target_buy is not None:
        for j in range(cost_line_idx or 0, min((cost_line_idx or 0)+15, len(lines))):
            if '"target_buy":' in lines[j]:
                lines[j] = f'        "target_buy": {target_buy},\n'
            if '"target_buy_shares":' in lines[j]:
                lines[j] = f'        "target_shares": {target_buy_shares},\n'
    
    # 更新注释
    for j in range(max(0, (cost_line_idx or 20) - 10), cost_line_idx or 20):
        if lines[j].strip().startswith("#"):
            if remain > 0:
                lines[j] = f"        # {today} 减仓{sell_shares}@{sell_price:.2f}({realized_loss:+.0f})，剩{remain}股\n"
            else:
                lines[j] = f"        # {today} 清仓{sell_shares}@{sell_price:.2f}({realized_loss:+.0f})\n"
            break
    
    # 更新LOSS_HISTORY
    for i, line in enumerate(lines):
        if f'"{ts_code}"' in line and '"loss"' in line and ts_code in line:
            m = re.search(r'"loss":\s*(\d+)', line)
            old_loss = int(m.group(1)) if m else 0
            new_loss = old_loss + abs(int(realized_loss))
            lines[i] = re.sub(r'"loss":\s*\d+', f'"loss": {new_loss}', line)
            break
    
    # 更新TOTAL_CAPITAL
    for i, line in enumerate(lines):
        if "TOTAL_CAPITAL =" in line:
            m = re.search(r'TOTAL_CAPITAL\s*=\s*(\d+)', line)
            old_cap = int(m.group(1))
            new_cap = old_cap + int(realized_loss)
            lines[i] = re.sub(r'TOTAL_CAPITAL\s*=\s*\d+', f'TOTAL_CAPITAL = {new_cap}', line)
            break
    
    # 写回
    with open(SCRIPT_PATH, 'w') as f:
        f.writelines(lines)
    
    # 清理状态文件 + pending_trades
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, 'r') as f:
            state = json.load(f)
        for key in ["alerted", "prev_limit_up", "prev_limit_down"]:
            if ts_code in state.get(key, {}):
                del state[key][ts_code]
        for k in list(state.keys()):
            if k.startswith(f"prev_pct_{ts_code}"):
                del state[k]
        msg = f"🔴 【{name} {ts_code} {'清仓' if remain==0 else '减仓'}】\n\n{sell_shares}股 @ {sell_price:.3f}\n已实现: {realized_loss:+.0f}元"
        state.setdefault('pending_trades', []).append({"msg": msg})
        with open(STATE_PATH, 'w') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    # 语法验证
    import ast
    try:
        ast.parse(open(SCRIPT_PATH).read())
    except SyntaxError as e:
        print(f"❌ 语法错误: {e}")
        sys.exit(1)
    
    # Git
    import subprocess
    subprocess.run(["git", "add", "scripts/price_monitor.py", ".monitor_state.json"], cwd=REPO_PATH, capture_output=True)
    subprocess.run(["git", "commit", "-m", 
        f"交易: {name} {ts_code} {'清' if remain==0 else '减'}{sell_shares}@{sell_price:.2f}({realized_loss:+.0f})"],
        cwd=REPO_PATH, capture_output=True)
    subprocess.run(["git", "push"], cwd=REPO_PATH, capture_output=True)
    
    # 汇总
    print(f"\n✅ {name} {'全清' if remain==0 else f'减仓剩{remain}股'}")
    print(f"   卖出: {sell_shares}@{sell_price:.2f}  实亏: {realized_loss:+.0f}")
    if target_buy and target_buy_shares:
        be = target_buy + abs(realized_loss) / target_buy_shares
        print(f"   回本价: {be:.2f} (需涨{(be/target_buy-1)*100:.1f}%)")
    print(f"   pending_trades已写入 | Git已推送")

if __name__ == "__main__":
    main()
