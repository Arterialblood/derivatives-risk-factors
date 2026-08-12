"""Generate HTML chart: V3 strategy buy/sell points + 科创50 & 沪深300 price trends"""
import json
from pathlib import Path

BACKTEST_DIR = Path(__file__).parent
DATA_DIR = BACKTEST_DIR / "data"

# ── Load raw price data ──
with open(DATA_DIR / "kechuang50_etf.json") as f:
    kc_raw = json.load(f)
with open(DATA_DIR / "hs300_etf.json") as f:
    hs_raw = json.load(f)

kc_nodes = list(reversed(kc_raw['data']['nodes']))
hs_nodes = list(reversed(hs_raw['data']['nodes']))

# Normalize to 100 at start
kc_base = kc_nodes[0]['last']
hs_base = hs_nodes[0]['last']

kc_prices = [round(n['last'] / kc_base * 100, 2) for n in kc_nodes]
hs_prices = [round(n['last'] / hs_base * 100, 2) for n in hs_nodes]
dates = [n['date'] for n in kc_nodes]

# ── Load strategy NAV (sampled) ──
with open(BACKTEST_DIR / "backtest_v3_results.json") as f:
    v3 = json.load(f)

# Build nav lookup by date
nav_lookup = {}
for p in v3['sampled_nav']:
    nav_lookup[p['date']] = p

# Interpolate strategy NAV for all dates (sampled is every ~2-3 days)
strat_nav = []
last_nav = 100.0
for d in dates:
    if d in nav_lookup:
        last_nav = round(nav_lookup[d]['nav'] / 1000, 2)  # normalize to 100 base (100000 → 100)
    strat_nav.append(last_nav)

# ── Trades ──
trades = v3['trades']

# Build trade markers
# For each trade, find the index in dates array
buy_markers = []  # {date, price_normalized, label}
sell_markers = []

for t in trades:
    entry_date = t['entry_date']
    exit_date = t['exit_date']
    symbol = '科创50' if t['symbol'] == 'kechuang' else '中证1000'
    pnl = t['pnl_pct']
    reason = t['exit_reason']

    # Find the normalized price on entry/exit dates
    # For kechuang trades, use kc_prices; for zz1000, use strat_nav as proxy
    if entry_date in dates:
        idx = dates.index(entry_date)
        buy_markers.append({
            'date': entry_date,
            'idx': idx,
            'nav': strat_nav[idx],
            'kc': kc_prices[idx],
            'hs': hs_prices[idx],
            'symbol': symbol,
            'price': t['entry_price'],
            'label': f'买入{symbol}\n@{t["entry_price"]}'
        })

    if exit_date in dates:
        idx = dates.index(exit_date)
        sell_markers.append({
            'date': exit_date,
            'idx': idx,
            'nav': strat_nav[idx],
            'kc': kc_prices[idx],
            'hs': hs_prices[idx],
            'symbol': symbol,
            'price': t['exit_price'],
            'pnl': pnl,
            'reason': reason,
            'label': f'卖出{symbol}\n@{t["exit_price"]}\n{pnl:+.1f}%'
        })

# ── Generate HTML ──
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>V3策略买卖点位 vs 科创50 & 沪深300 走势</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
    background: #f5f5f5; color: #333; padding: 20px;
}}
.container {{ max-width: 1400px; margin: 0 auto; }}
h1 {{ font-size: 22px; margin-bottom: 8px; color: #1a1a2e; }}
.subtitle {{ font-size: 14px; color: #666; margin-bottom: 20px; }}
.chart-wrapper {{
    background: #fff; border-radius: 12px; padding: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 20px;
}}
canvas {{ max-height: 600px; }}
.legend-bar {{
    display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 16px;
    padding: 12px 16px; background: #fafafa; border-radius: 8px;
}}
.legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 13px; }}
.legend-dot {{ width: 16px; height: 3px; border-radius: 2px; }}
.legend-arrow {{ font-size: 18px; }}
.trade-table {{
    width: 100%; border-collapse: collapse; font-size: 13px;
    background: #fff; border-radius: 8px; overflow: hidden;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
}}
.trade-table th {{
    background: #1a1a2e; color: #fff; padding: 10px 12px;
    text-align: left; font-weight: 600;
}}
.trade-table td {{
    padding: 8px 12px; border-bottom: 1px solid #eee;
}}
.trade-table tr:hover {{ background: #f9f9f9; }}
.positive {{ color: #e74c3c; font-weight: 600; }}
.negative {{ color: #27ae60; font-weight: 600; }}
.tag {{
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 600;
}}
.tag-kc {{ background: #e8f4fd; color: #1890ff; }}
.tag-zz {{ background: #fff7e6; color: #fa8c16; }}
.tag-stop {{ background: #fce4ec; color: #e91e63; }}
.tag-trail {{ background: #e8f5e9; color: #4caf50; }}
.summary-cards {{
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 12px; margin-bottom: 20px;
}}
.card {{
    background: #fff; padding: 16px; border-radius: 10px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06); text-align: center;
}}
.card-value {{ font-size: 24px; font-weight: 700; margin: 4px 0; }}
.card-label {{ font-size: 12px; color: #999; }}
.card-strat {{ border-top: 3px solid #7c3aed; }}
.card-kc {{ border-top: 3px solid #1890ff; }}
.card-hs {{ border-top: 3px solid #fa8c16; }}
.card-dd {{ border-top: 3px solid #e91e63; }}
</style>
</head>
<body>
<div class="container">
<h1>V3策略买卖点位 vs 科创50ETF & 沪深300ETF 走势</h1>
<p class="subtitle">回测区间: 2025-08-01 ~ 2026-08-12 | 所有价格归一化为100基准 | 紫线=策略净值, 蓝线=科创50, 橙线=沪深300</p>

<div class="summary-cards">
    <div class="card card-strat">
        <div class="card-label">V3策略收益</div>
        <div class="card-value positive">+47.3%</div>
        <div class="card-label">7笔交易 | 胜率71.4%</div>
    </div>
    <div class="card card-kc">
        <div class="card-label">科创50买入持有</div>
        <div class="card-value positive">+68.3%</div>
        <div class="card-label">最大回撤 -29.9%</div>
    </div>
    <div class="card card-hs">
        <div class="card-label">沪深300买入持有</div>
        <div class="card-value positive">+18.4%</div>
        <div class="card-label">最大回撤 -9.8%</div>
    </div>
    <div class="card card-dd">
        <div class="card-label">V3最大回撤</div>
        <div class="card-value negative">-13.3%</div>
        <div class="card-label">夏普 1.76</div>
    </div>
</div>

<div class="chart-wrapper">
<div class="legend-bar">
    <div class="legend-item"><div class="legend-dot" style="background:#7c3aed;"></div> V3策略净值</div>
    <div class="legend-item"><div class="legend-dot" style="background:#1890ff;"></div> 科创50ETF (归一化)</div>
    <div class="legend-item"><div class="legend-dot" style="background:#fa8c16;"></div> 沪深300ETF (归一化)</div>
    <div class="legend-item"><span class="legend-arrow">▲</span> 买入信号</div>
    <div class="legend-item"><span class="legend-arrow">▼</span> 卖出信号</div>
</div>
<canvas id="mainChart"></canvas>
</div>

<table class="trade-table">
<thead>
<tr><th>#</th><th>买入日期</th><th>标的</th><th>买入价</th><th>卖出日期</th><th>卖出价</th><th>收益</th><th>退出原因</th></tr>
</thead>
<tbody>
"""

for i, t in enumerate(trades):
    sym_label = '科创50ETF' if t['symbol'] == 'kechuang' else '中证1000ETF'
    tag_class = 'tag-kc' if t['symbol'] == 'kechuang' else 'tag-zz'
    pnl_class = 'positive' if t['pnl_pct'] > 0 else 'negative'
    reason_class = 'tag-trail' if t['exit_reason'] == 'trailing_stop' else 'tag-stop'
    reason_text = '跟踪止损' if t['exit_reason'] == 'trailing_stop' else '硬止损-8%'
    html += f"""<tr>
<td>{i+1}</td>
<td>{t['entry_date']}</td>
<td><span class="tag {tag_class}">{sym_label}</span></td>
<td>{t['entry_price']:.2f}</td>
<td>{t['exit_date']}</td>
<td>{t['exit_price']:.2f}</td>
<td class="{pnl_class}">{t['pnl_pct']:+.1f}%</td>
<td><span class="tag {reason_class}">{reason_text}</span></td>
</tr>"""

html += """
</tbody>
</table>
</div>

<script>
// Register annotation plugin
Chart.register(window['chartjs-plugin-annotation']);

const dates = """ + json.dumps(dates) + """;
const kcPrices = """ + json.dumps(kc_prices) + """;
const hsPrices = """ + json.dumps(hs_prices) + """;
const stratNav = """ + json.dumps(strat_nav) + """;

const buyMarkers = """ + json.dumps(buy_markers) + """;
const sellMarkers = """ + json.dumps(sell_markers) + """;

// Build point styles for strategy line (default circle, triangle for buys, inverted triangle for sells)
const pointRadius = new Array(dates.length).fill(0);
const pointStyle = new Array(dates.length).fill('circle');
const pointBgColor = new Array(dates.length).fill('#7c3aed');
const pointBorderColor = new Array(dates.length).fill('#7c3aed');

// Mark buy points on strategy line
buyMarkers.forEach(m => {
    pointRadius[m.idx] = 10;
    pointStyle[m.idx] = 'triangle';
    pointBgColor[m.idx] = '#e74c3c';
    pointBorderColor[m.idx] = '#fff';
});

// Mark sell points on strategy line
sellMarkers.forEach(m => {
    pointRadius[m.idx] = 10;
    pointStyle[m.idx] = 'triangle';
    pointBgColor[m.idx] = '#27ae60';
    pointBorderColor[m.idx] = '#fff';
});

// Build annotations for trade zones
const annotations = {};
const tradeColors = ['rgba(231,76,60,0.06)', 'rgba(39,174,96,0.06)', 'rgba(241,196,15,0.06)', 
                     'rgba(52,152,219,0.06)', 'rgba(155,89,182,0.06)', 'rgba(230,126,34,0.06)', 'rgba(231,76,60,0.06)'];

const trades = """ + json.dumps(trades) + """;

trades.forEach((t, i) => {
    const entryIdx = dates.indexOf(t.entry_date);
    const exitIdx = dates.indexOf(t.exit_date);
    if (entryIdx >= 0 && exitIdx >= 0) {
        const color = t.symbol === 'kechuang' ? 'rgba(24,144,255,0.05)' : 'rgba(250,140,22,0.05)';
        annotations['trade' + i] = {
            type: 'box',
            xMin: entryIdx,
            xMax: exitIdx,
            backgroundColor: color,
            borderColor: t.symbol === 'kechuang' ? 'rgba(24,144,255,0.15)' : 'rgba(250,140,22,0.15)',
            borderWidth: 1,
            label: {
                display: true,
                content: (t.symbol === 'kechuang' ? '科创50' : '中证1000') + ' ' + (t.pnl_pct > 0 ? '+' : '') + t.pnl_pct.toFixed(1) + '%',
                position: 'start',
                font: { size: 10, weight: 'bold' },
                color: t.symbol === 'kechuang' ? '#1890ff' : '#fa8c16',
                backgroundColor: 'rgba(255,255,255,0.8)',
                padding: 4,
                borderRadius: 4
            }
        };
    }
});

const ctx = document.getElementById('mainChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: dates,
        datasets: [
            {
                label: 'V3策略净值',
                data: stratNav,
                borderColor: '#7c3aed',
                backgroundColor: 'rgba(124,58,237,0.05)',
                borderWidth: 2.5,
                fill: false,
                tension: 0.1,
                pointRadius: pointRadius,
                pointStyle: pointStyle,
                pointBackgroundColor: pointBgColor,
                pointBorderColor: pointBorderColor,
                pointBorderWidth: 2,
                pointRotation: function(ctx) {
                    // Rotate triangles: buy=0 (up), sell=180 (down)
                    const idx = ctx.dataIndex;
                    const isSell = sellMarkers.some(m => m.idx === idx);
                    return isSell ? 180 : 0;
                },
                order: 1
            },
            {
                label: '科创50ETF (归一化=100)',
                data: kcPrices,
                borderColor: '#1890ff',
                backgroundColor: 'rgba(24,144,255,0.03)',
                borderWidth: 1.5,
                fill: false,
                tension: 0.1,
                pointRadius: 0,
                borderDash: [],
                order: 2
            },
            {
                label: '沪深300ETF (归一化=100)',
                data: hsPrices,
                borderColor: '#fa8c16',
                backgroundColor: 'rgba(250,140,22,0.03)',
                borderWidth: 1.5,
                fill: false,
                tension: 0.1,
                pointRadius: 0,
                borderDash: [5, 3],
                order: 3
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: { font: { size: 12 } }
            },
            tooltip: {
                callbacks: {
                    title: function(items) {
                        return items[0].label;
                    },
                    label: function(item) {
                        const label = item.dataset.label || '';
                        const val = item.parsed.y;
                        return label + ': ' + val.toFixed(2);
                    },
                    afterBody: function(items) {
                        const idx = items[0].dataIndex;
                        const buy = buyMarkers.find(m => m.idx === idx);
                        const sell = sellMarkers.find(m => m.idx === idx);
                        let extra = [];
                        if (buy) {
                            extra.push('▲ 买入 ' + buy.symbol + ' @ ' + buy.price);
                        }
                        if (sell) {
                            extra.push('▼ 卖出 ' + sell.symbol + ' @ ' + sell.price + ' (' + (sell.pnl > 0 ? '+' : '') + sell.pnl.toFixed(1) + '%)');
                        }
                        return extra;
                    }
                }
            },
            annotation: {
                annotations: annotations
            }
        },
        scales: {
            x: {
                ticks: {
                    maxTicksLimit: 20,
                    font: { size: 10 },
                    maxRotation: 45
                },
                grid: { display: false }
            },
            y: {
                title: { display: true, text: '归一化净值 (起点=100)', font: { size: 12 } },
                grid: { color: 'rgba(0,0,0,0.05)' },
                ticks: { font: { size: 11 } }
            }
        }
    }
});
</script>
</body>
</html>"""

output_path = Path("/Users/Bohong/WorkBuddy/2026-08-10-12-12-25/deliverables/report/V3买卖点位对比图.html")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Chart generated: {output_path}")
print(f"Data points: {len(dates)}")
print(f"Buy markers: {len(buy_markers)}")
print(f"Sell markers: {len(sell_markers)}")
for i, t in enumerate(trades):
    sym = '科创50' if t['symbol'] == 'kechuang' else '中证1000'
    print(f"  Trade {i+1}: {t['entry_date']} → {t['exit_date']} | {sym} | {t['pnl_pct']:+.1f}%")
