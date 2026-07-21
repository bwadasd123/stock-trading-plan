# 价格监控设置指南

## 企业微信Webhook

企业微信群机器人webhook格式：
```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx-xxx-xxx
```

POST请求：
```python
import json, urllib.request

url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
data = json.dumps({
    "msgtype": "text",
    "text": {"content": "消息内容"}
}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=10)
# 返回 {"errcode":0,"errmsg":"ok"} 表示成功
```

## CronJob创建步骤

1. 写监控脚本到 `~/.hermes/profiles/eastmoney-bot/scripts/xxx.py`
2. 创建cronjob：
   - `no_agent: true`（纯脚本执行，不需要AI）
   - `deliver: origin`（推送到当前聊天）
   - `schedule: */5 9-15 * * 1-5`（交易日每5分钟）
3. 脚本内直接调用企业微信webhook推送

## 状态文件

避免重复提醒，用JSON文件记录已触发的条件：
```python
STATE_FILE = "~/.hermes/profiles/eastmoney-bot/scripts/.monitor_state.json"
# 每天9:30重置状态
```

## 用户偏好

- 用户喜欢**频繁推送**，不要只推触发条件
- 定时汇报 + 涨跌播报 + 开盘收盘 都要
- 推送到企业微信群（非Telegram）
