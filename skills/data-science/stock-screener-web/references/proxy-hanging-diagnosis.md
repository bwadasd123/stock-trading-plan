# Proxy Hanging vs Slow Diagnosis

## Problem Pattern
Proxy failures causing scan to **hang/stuck** (not just slow).

## Symptoms
- Scan starts, processes a few pages, then stops progressing
- Log shows proxy connection errors but no new stock analysis logs
- Only `proxy_status` polling requests continue every 5 seconds
- User reports "卡住了" (stuck) not "太慢了" (too slow)

## Root Cause
- Proxy timeout = 20 seconds × 3 retries = 60 seconds per stock
- 39 stocks × 60 seconds = 2340 minutes = completely stuck
- Even with 5s timeout × 3 retries = 15s per stock × 39 = 10 minutes

## Key Insight
**"卡住" (stuck) ≠ "慢" (slow)**
- Slow = processing but taking long → reduce timeout
- Stuck = not processing at all → check blocking/hanging issues

## Solution
1. **Reduce retries to 1** — proxy fails once → immediate fallback to direct
2. **Reduce timeout to 5s** — don't wait long for bad proxies
3. **Direct fallback with `requests.get`** — not shared SESSION (connection pool issue)

## Configuration (as of 2026-06-16)
```python
# anti_crawl.py
max_retries: int = 1  # was 3, then 5
delay = 2  # retry interval

# services/kline.py
timeout=5  # was 20, then 10
```

## User Feedback Pattern
When user says "又这样了 解决问题" (it's doing it again, solve the problem):
- They're frustrated with incremental fixes (20→10→5)
- They want the ROOT CAUSE fixed, not timeout tuning
- Solution: eliminate the retry loop entirely (max_retries=1)
