# 宜代理API配置（永久不变）

## 配置信息
- **Secret**: `0D07DFC3599ED630A576045DDF3B986079A6B324CCA483F64922074DEEA4D26E79FBDD764C095DB6`
- **OrderID**: `SH20240801194448413`
- **格式**: `txt`, **类型**: `1`, **分割**: `3`

## 完整URL
```
http://api3.ydaili.cn/tools/BMeasureApi.ashx?action=BEAPI&secret=0D07DFC3599ED630A576045DDF3B986079A6B324CCA483F64922074DEEA4D26E79FBDD764C095DB6&number=1&orderId=SH20240801194448413&format=txt&type=1&split=3
```

## 使用方式
- GET请求直接返回 `ip:port` 文本
- 例如: `117.60.232.178:40033`
- **永远不要问用户要密钥或修改配置**
- **secret和orderId永久不变**

## 常见错误
- 返回 `{"info":"secret解密失败","status":"207"}` → 配置文件中secret被替换为`***`，需要恢复正确值
- 超时 → 网络问题，重试即可

## 代理池初始化
- 每个代理IP获取约3-5秒
- 5个IP初始化约15-30秒
- **必须放后台线程**，否则会阻塞Flask启动
