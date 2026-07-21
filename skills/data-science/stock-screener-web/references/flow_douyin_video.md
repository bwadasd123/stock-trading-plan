# flow_douyin.py 视频制作与发送

## 输出
- **用户指定路径**: `/mnt/c/Users/Administrator/Desktop/工作室/抖音小韭菜/stock_flow_douyin_YYYYMMDD.mp4`
- 大小: ~8.3MB (skip=1), ~3MB (skip=3), 时长: 30秒 (skip=1) / 10秒 (skip=3), FPS: 8
- 分辨率: 1080x1920 (抖音竖屏)

## 命令
```bash
mkdir -p "/mnt/c/Users/Administrator/Desktop/工作室/抖音小韭菜/"
cd /home/jmy && /home/jmy/.hermes/hermes-agent/venv/bin/python flow_douyin.py \
  -o "/mnt/c/Users/Administrator/Desktop/工作室/抖音小韭菜/stock_flow_douyin_$(date +%Y%m%d).mp4"
```

## 监控进度
Python stdout在后台进程中被缓冲，`process log` 返回空。用以下方法：
- `process poll` — 返回 `output_preview` 字段，包含最近的缓冲输出
- `ls /tmp/flow_douyin_*/frame_*.png | wc -l` — 检查已渲染帧数（共240帧）

## 数据源
- 东方财富板块资金流向API
- TOP10流入 + BOTTOM10流出
- 每板块240个时间点 (9:31-15:00)

## 视频发送
**Telegram上传问题**: 8MB+视频经常超时（实测8.3MB多次超时）

**解决方案**:
1. 先尝试Telegram MEDIA标签发送
2. 若超时，文件已在Windows桌面: `/mnt/c/Users/Administrator/Desktop/工作室/抖音小韭菜/`
3. **文件大小**: 默认参数(skip=1, fps=8)生成~8.3MB，用 `--skip 3` 可降到~3MB

## 启动方式
```bash
cd /home/jmy && /home/jmy/.hermes/hermes-agent/venv/bin/python flow_douyin.py
```
**⚠️ 必须用 venv python**，系统 python 缺少依赖。

## 依赖
- anti_crawl模块 (Playwright cookies)
- matplotlib, ffmpeg
- 字体: WenQuanYi Zen Hei
