# 推送诊断流程

当用户问"推送还正常吗"或"没收到消息"时，按以下顺序排查：

## 1. 直接测试webhook（不依赖.env）
```python
import urllib.request, json
webhook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=完整key'
test_msg = {'msgtype': 'text', 'text': {'content': '🔧 推送测试'}}
req = urllib.request.Request(webhook_url, 
    data=json.dumps(test_msg).encode('utf-8'),
    headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=10) as resp:
    print(json.loads(resp.read()))
# errcode:0=成功, 93000=key无效
```

## 2. 检查.env中的值
```bash
grep WX_WEBHOOK /home/jmy/.hermes/profiles/eastmoney-bot/.env
```
- 显示`key=***` → 可能是**字面量占位符**，不是hermes mask！
- 测试webhook返回93000 → 确认是占位符，需要替换真实key

## 3. 替换key=***占位符
```bash
# ❌ sed处理*会报错："Invalid preceding regular expression"
# ✅ 用grep+v重建：
grep -v "WX_WEBHOOK" /home/jmy/.hermes/profiles/eastmoney-bot/.env > /tmp/env_tmp
echo 'WX_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=真实key' >> /tmp/env_tmp
mv /tmp/env_tmp /home/jmy/.hermes/profiles/eastmoney-bot/.env
```

## 4. 检查脚本是否加载了.env
cronjob不会自动加载.env，脚本需要`load_env()`函数。测试：
```bash
cd /home/jmy/.hermes/profiles/eastmoney-bot/scripts
python3 -c "from price_monitor import WX_WEBHOOK; print(f'WX_WEBHOOK={\"已配置\" if WX_WEBHOOK else \"未配置\"}')"
```

## 5. 手动触发完整推送测试
```python
cd /home/jmy/.hermes/profiles/eastmoney-bot/scripts && python3 -c "
import sys, os
sys.path.insert(0, '.')
os.environ['WX_WEBHOOK'] = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=完整key'
from price_monitor import get_price, STOCKS, send_wx, format_stock
msg = '🔔 【手动测试推送】\n\n'
for stock in STOCKS:
    price_data = get_price(stock['code'])
    if price_data:
        stock_msg, _, _ = format_stock(stock, price_data)
        msg += stock_msg + '\n'
send_wx(msg)
print('推送完成')
"
```

## 6. 检查cronjob状态
```bash
hermes cron list  # 确认enabled且last_status=ok
```

## 常见错误码
| errcode | 含义 | 解决 |
|---------|------|------|
| 0 | 成功 | - |
| 93000 | invalid webhook url | key过期或被替换为***占位符 |
| 93004 | invalid webhook key | key格式错误 |
