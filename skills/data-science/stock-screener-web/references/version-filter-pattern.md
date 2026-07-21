# Version Filter Pattern (历史信号页面)

## Pattern: Adding a filter dropdown to an existing page

When adding a new filter dimension (version, type, category, etc.) to a data table page:

### 1. HTML (templates/index.html)
Add `<select>` in the `.page-controls` div:
```html
<select id="hist_version" class="select">
  <option value="">全部版本</option>
  <option value="normal">普通扫描</option>
  <option value="old">老版本 (smplmt=460)</option>
  <option value="new">新版本 (日线)</option>
</select>
```

### 2. JS (static/js/app.js)
Read the value and append to API URL:
```javascript
const version = document.getElementById('hist_version')?.value || '';
if (version) url += '&version=' + version;
```

Display badge in table:
```javascript
let versionTag = '—';
if (s.scan_id) {
  if (s.scan_id.endsWith('_old')) {
    versionTag = '<span class="badge badge-orange">老版本</span>';
  } else if (s.scan_id.endsWith('_new')) {
    versionTag = '<span class="badge badge-blue">新版本</span>';
  }
}
```

### 3. API (api/history.py)
Add parameter parsing and SQL condition:
```python
version = request.args.get("version", "")

version_condition = ""
if version == "old":
    version_condition = "AND scan_id LIKE '%_old'"
elif version == "new":
    version_condition = "AND scan_id LIKE '%_new'"
elif version == "normal":
    version_condition = "AND scan_id NOT LIKE '%_old' AND scan_id NOT LIKE '%_new'"
```
Append `{version_condition}` to all SQL queries (count + data).

### 4. CSS
Use existing badge classes: `.badge-orange`, `.badge-blue`, `.badge-green`, `.badge-red`.

### Dual Version Scan Storage
- `scan_id` format: `YYYYMMDD_HHMMSS_old` or `YYYYMMDD_HHMMSS_new`
- Stored in same `stock_scan_results` table as normal scans
- Distinguished by `_old`/`_new` suffix
