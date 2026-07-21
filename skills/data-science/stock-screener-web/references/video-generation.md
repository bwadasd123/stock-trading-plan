# Video Generation (flow_douyin.py)

## Overview
Douyin-format race chart video generator for sector fund flow (板块资金流向).
- Location: `/home/jmy/flow_douyin.py`
- Output: 1080x1920 MP4 (抖音竖屏)
- Content: TOP10 + BOTTOM10 sectors by net fund flow
- Watermark: @一棵小韭菜

## Anti-Crawl Integration (2026-06-03 Fix)
**Problem**: Original proxy API (ydaili.cn) expired, causing 502 errors.

**Solution**: Integrated with stock-screener's anti_crawl module:
```python
import sys
sys.path.insert(0, '/home/jmy/stock-screener')
from anti_crawl import COOKIE_MANAGER, get_sector_headers, safe_get
```

**Key changes**:
1. Removed `get_fresh_proxy()` function (expired API)
2. Removed `safe_request()` function (proxy-based)
3. Use `get_sector_headers()` for request headers
4. Use `safe_get()` for all API requests (handles Playwright cookies)

## Usage
```bash
cd /home/jmy
python flow_douyin.py --skip 3 --fps 10
```

## Parameters
- `--skip N`: Skip every N frames (default: 1, higher = faster generation)
- `--fps N`: Video frame rate (default: 8)
- `--output PATH`: Custom output path

## Output
- Default: `~/stock_flow_douyin_YYYYMMDD.mp4`
- **用户指定路径**: `/mnt/c/Users/Administrator/Desktop/工作室/抖音小韭菜/` (Windows桌面)
- 命令示例:
  ```bash
  python flow_douyin.py -f 8 -o "/mnt/c/Users/Administrator/Desktop/工作室/抖音小韭菜/stock_flow_$(date +%Y%m%d).mp4"
  ```

## Generation Time
- 240 frames at fps=8 (no skip): **~15 minutes**, output ~5.5MB, duration ~30秒
- 240 frames at fps=8 with skip=3: **~5 minutes**, output ~3MB, duration ~10秒
- Each frame takes ~3-4 seconds to render

## Dependencies
- matplotlib, numpy, requests
- ffmpeg (for video synthesis)
- stock-screener's anti_crawl module

## Pitfalls
1. **Proxy API expired**: ydaili.cn secret expired 2026-06-01. Must use anti_crawl module.
2. **Playwright not installed**: anti_crawl falls back to direct connection (may work)
3. **502 errors**: If Playwright cookie fails, direct connection may still work for some endpoints
4. **Long generation time**: Full 240 frames takes ~15 minutes. Use `--skip 3` for ~5 minutes.
5. **Telegram upload timeout**: Default output (~5.5MB) may timeout on Telegram. Copy to Windows desktop as fallback.
6. **No output during render**: Python buffers stdout in background processes. Two ways to monitor:
   - **`process poll`** (preferred): Returns `output_preview` field with recent buffered output. `process log` often returns empty for buffered Python.
   - **Temp directory frame count**: `ls /tmp/flow_douyin_*/frame_*.png | wc -l` — 240 total frames expected. If count is increasing, rendering is progressing.
   - Frame render rate: ~1 frame/second, so 240 frames ≈ 4 minutes of rendering + ffmpeg encode time.
7. **mkdir -p needed**: First use of Windows output path requires `mkdir -p "/mnt/c/Users/Administrator/Desktop/工作室/抖音小韭菜/"`
