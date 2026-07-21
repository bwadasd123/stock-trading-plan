# Dark-Themed Matplotlib Charts for Telegram

## Color Palette (matches style.css)

```python
BG_DARK = '#0f1117'
BG_CARD = '#1a1d29'
BG_ROW1 = '#1a1d29'
BG_ROW2 = '#1e2130'
RED = '#ef5350'
GREEN = '#4CAF50'
BLUE = '#2196F3'
ORANGE = '#ff9800'
WHITE = '#e0e0e0'
GRAY = '#888'
BORDER = '#2a2d3a'
```

## Font Setup

```python
import matplotlib.font_manager as fm

font_candidates = [
    'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
    'Noto Sans CJK SC', 'Noto Sans SC',
    'SimHei', 'Microsoft YaHei', 'PingFang SC',
]
font_name = None
for f in font_candidates:
    if any(f.lower() in fp.name.lower() for fp in fm.fontManager.ttflist):
        font_name = f
        break
if not font_name:
    font_name = 'DejaVu Sans'
plt.rcParams['font.family'] = font_name
plt.rcParams['axes.unicode_minus'] = False
```

## Chart Structure

1. **Title area** — fig.add_axes([0, 0.92, 1, 0.08]) with ax_title.text()
2. **Info cards** — fig.add_axes([0.03, 0.78, 0.94, 0.13]) for metrics
3. **Table area** — fig.add_axes([0.03, 0.08, 0.94, 0.59]) for data
4. **Footer** — fig.add_axes([0, 0, 1, 0.07]) for warnings

## Sending to Telegram

```python
plt.savefig('/home/jmy/chart.png', dpi=150, bbox_inches='tight', 
            facecolor=BG_DARK, edgecolor='none')
plt.close()
# Then: MEDIA:/home/jmy/chart.png
```

## Key Patterns

- Use `ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')` for card areas
- Use `ax.axhspan()` for alternating row backgrounds
- Use `ax.axhline()` for separator lines
- Color code: RED for losses, GREEN for gains, GRAY for neutral
- Font sizes: title 22, section header 14, body 10-11, small 9
- Output: 1080px wide, ~150 DPI, PNG format

## Example: Stock Portfolio Chart

See `/home/jmy/513100_analysis.png` for a working example of:
- Portfolio overview card (shares, cost, current, P&L)
- Quality rating stars
- Holdings table with color-coded gains/losses
- Warning footer
