# Daily Digest Caching Pitfalls

Separate file for caching pitfalls. See also: `daily-digest-caching.md` for full implementation details.

## from_cache Bug (2026-06-04)

**Bug:** Front-end cache check `!tabDataCache['daily'].from_cache` caused re-fetch after save.

**Symptom:** Every page load to 今日看点 re-fetches data even after saving, causing a noticeable lag/hang.

**Root cause:** `from_cache` is a SOURCE indicator (MySQL vs real-time), NOT a validity flag. After saving daily digest via `/api/daily/save`, subsequent loads from MySQL set `from_cache: true`. The front-end condition `!tabDataCache['daily'].from_cache` treated this as "invalid cache" and forced re-fetch.

**Fix (daily.js line 14):**
```javascript
// WRONG — treats DB-sourced data as invalid cache
if (!forceRefresh && tabDataCache['daily'] && !tabDataCache['daily'].from_cache) {

// CORRECT — use cache regardless of source
if (!forceRefresh && tabDataCache['daily']) {
```

**Rule:** `from_cache` should only be used for display purposes (showing "📦 已缓存" badge), never for cache validity decisions.

## Cache Layer Summary

| Layer | Scope | Validity |
|-------|-------|----------|
| `tabDataCache['daily']` (JS) | Per browser session | Until page refresh or force refresh |
| `daily_digest_cache` (MySQL) | Per date | Permanent (historical data) |
| `from_cache` field | Data source indicator | NOT a validity flag |
