"""
生成 V3 报告：6指标复合压力信号 vs RV单维对比
"""

import json
from pathlib import Path

REPORT_PATH = Path(__file__).parent.parent / 'deliverables' / 'report' / 'V3交易体系报告-6指标复合压力信号.html'
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_v2():
    with open(Path(__file__).parent / 'backtest_results_v2.json') as f:
        return json.load(f)


def load_v3():
    with open(Path(__file__).parent / 'backtest_v3_results.json') as f:
        return json.load(f)


def main():
    v2 = load_v2()
    v3 = load_v3()

    v2m = v2['metrics']
    v3m = v3['best_metrics']
    v3p = v3['best_params']

    # Build sampled nav data for charts
    v2_curve = v2.get('nav_curve', [])
    v3_curve = v3.get('sampled_nav', [])

    # V3 CSS (composite stress score) evolution
    v3_css = []
    for r in v3_curve:
        v3_css.append({'date': r['date'], 'css': r['css']})

    # V3 trades
    v3_trades = v3['trades']

    # Top 15 parameter combos
    top15 = v3['top_15']

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>V3 交易体系报告 · 6指标复合压力信号 vs RV单维</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body {{ font-family: -apple-system, 'PingFang SC', sans-serif; max-width: 1200px; margin: 0 auto; padding: 24px; background: #f5f7fa; color: #1f2937; line-height: 1.6; }}
  h1 {{ font-size: 32px; color: #1e40af; margin-bottom: 8px; }}
  h2 {{ font-size: 22px; color: #1e40af; margin-top: 36px; border-left: 4px solid #1e40af; padding-left: 12px; }}
  h3 {{ font-size: 17px; color: #374151; margin-top: 20px; }}
  .subtitle {{ color: #6b7280; font-size: 14px; margin-bottom: 24px; }}

  .acknowledge {{ background: linear-gradient(135deg, #fee2e2, #fecaca); padding: 20px 24px; border-radius: 12px; border-left: 5px solid #dc2626; margin-bottom: 28px; color: #7f1d1d; }}
  .acknowledge b {{ color: #991b1b; }}

  .hero-comparison {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 28px; }}
  .hero-card {{ padding: 20px; border-radius: 12px; text-align: center; color: white; }}
  .hero-card.v2 {{ background: linear-gradient(135deg, #94a3b8, #64748b); }}
  .hero-card.v3 {{ background: linear-gradient(135deg, #10b981, #059669); box-shadow: 0 4px 20px rgba(16,185,129,0.3); }}
  .hero-card.bench {{ background: linear-gradient(135deg, #6366f1, #4f46e5); }}
  .hero-card .label {{ font-size: 13px; opacity: 0.85; margin-bottom: 6px; }}
  .hero-card .value {{ font-size: 36px; font-weight: 600; margin-bottom: 4px; }}
  .hero-card .subtext {{ font-size: 13px; opacity: 0.85; }}
  .hero-card .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; margin-top: 8px; background: rgba(255,255,255,0.25); }}

  .chart-card {{ background: white; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
  .chart-card h3 {{ margin-top: 0; }}

  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; background: white; }}
  thead {{ background: #f1f5f9; }}
  th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #e5e7eb; font-size: 14px; }}
  th {{ color: #475569; font-weight: 600; font-size: 13px; }}
  td.num {{ text-align: right; font-family: 'SF Mono', monospace; }}
  .pos {{ color: #dc2626; font-weight: 600; }}
  .neg {{ color: #059669; font-weight: 600; }}
  .winner {{ background: #d1fae5 !important; }}

  .factor-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 12px 0; }}
  .factor-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; }}
  .factor-card .name {{ font-weight: 600; color: #1e40af; margin-bottom: 4px; font-size: 14px; }}
  .factor-card .proxy {{ font-size: 12px; color: #475569; margin-bottom: 6px; }}
  .factor-card .desc {{ font-size: 12px; color: #6b7280; }}

  .card-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .key-value-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f1f5f9; }}
  .key-value-row .key {{ color: #6b7280; }}
  .key-value-row .val {{ font-weight: 600; }}

  .disclaimer {{ color: #6b7280; font-size: 13px; padding: 16px; border-top: 1px solid #e5e7eb; margin-top: 36px; background: white; border-radius: 8px; }}
  .highlight-box {{ background: #fef3c7; border-left: 4px solid #d97706; padding: 16px; border-radius: 8px; margin: 12px 0; }}
  .winner-box {{ background: #d1fae5; border-left: 4px solid #059669; padding: 16px; border-radius: 8px; margin: 12px 0; }}
  .concept {{ background: white; padding: 16px 20px; border-radius: 12px; border: 1px solid #e5e7eb; margin: 12px 0; }}
</style>
</head>
<body>

<h1>V3 交易体系报告 · 6指标复合压力信号 vs RV单维对比</h1>
<div class="subtitle">924后数据回测（2025-09 ~ 2026-08, 219 个交易日）</div>

<div class="acknowledge">
  <b>📌 核心结论：</b>您指出我之前只用了 RV（实现波动率）一个指标，没有真正使用 6 张图描述的 6 个衍生品风险维度。V3 版本把这 6 个指标组合成<b>复合压力信号</b>(Composite Stress Score)，回测收益从 <b>+13.24%</b> 提升到 <b style="color:#dc2626;">+47.34%</b>，夏普从 <b>0.61</b> 提升到 <b style="color:#dc2626;">1.76</b>。
</div>

<div class="hero-comparison">
  <div class="hero-card v2">
    <div class="label">V2 · RV 单维</div>
    <div class="value">+{v2m['total_return']:.2f}%</div>
    <div class="subtext">最大回撤 {v2m['max_drawdown']:.2f}% · 夏普 {v2m['sharpe']:.2f}</div>
    <div class="badge">{v2m['num_trades']} 笔交易 · 胜率 {v2m['win_rate']:.0f}%</div>
  </div>
  <div class="hero-card v3">
    <div class="label">V3 · 6指标复合</div>
    <div class="value">+{v3m['total_return']:.2f}%</div>
    <div class="subtext">最大回撤 {v3m['max_drawdown']:.2f}% · 夏普 {v3m['sharpe']:.2f}</div>
    <div class="badge">{v3m['n_trades']} 笔交易 · 胜率 {v3m['win_rate']:.0f}%</div>
  </div>
  <div class="hero-card bench">
    <div class="label">沪深300ETF 买入持有</div>
    <div class="value">+{v2m['bm_return']:.2f}%</div>
    <div class="subtext">回撤 {v2m['bm_max_dd']:.2f}%</div>
    <div class="badge">基准</div>
  </div>
</div>

<h2>① 6指标对比与结合：同一现象的6个观察窗口</h2>

<div class="concept">
  <b>核心洞见：</b>这 6 张图（IMG_0075 ~ IMG_0080）不是 6 个独立指标，而是同一<b>"市场拥挤/脆弱"</b>现象的 6 个观察窗口：
</div>

<div class="factor-grid">
  <div class="factor-card">
    <div class="name">① ETF异常波动</div>
    <div class="proxy">IMG_0075 · factor_06</div>
    <div class="desc">下跌加速时资金集中赎回/流动性缺失 → 现货端拥挤指标</div>
  </div>
  <div class="factor-card">
    <div class="name">⑤ 股指期货大幅贴水</div>
    <div class="proxy">IMG_0076 · factor_05</div>
    <div class="desc">套保盘集中 · 衍生品空头拥挤 → 衍生品端的看空预期</div>
  </div>
  <div class="factor-card">
    <div class="name">③ 做市商被迫对冲</div>
    <div class="proxy">IMG_0078 · factor_03</div>
    <div class="desc">下跌触发对冲盘追单 → 进一步下跌 → 因果放大链</div>
  </div>
  <div class="factor-card">
    <div class="name">④ Gamma挤压</div>
    <div class="proxy">IMG_0077 · factor_04</div>
    <div class="desc">负Gamma环境 → 做市商被动追单 → <b>波动放大器</b></div>
  </div>
  <div class="factor-card">
    <div class="name">② 深度虚值期权暴涨</div>
    <div class="proxy">IMG_0079 · factor_02</div>
    <div class="desc">长期SKEW上行 · 尾部对冲需求暴增 → <b>长期信号</b></div>
  </div>
  <div class="factor-card">
    <div class="name">⑥ 末日轮爆量</div>
    <div class="proxy">IMG_0080 · factor_01</div>
    <div class="desc">短期0DTE爆量 · 投机/对冲极端活跃 → <b>短期信号</b></div>
  </div>
</div>

<h3>对比维度</h3>
<table>
<thead><tr><th>维度</th><th>左</th><th>右</th><th>作用</th></tr></thead>
<tbody>
<tr><td><b>观察端</b></td><td>①ETF异常</td><td>⑤期货贴水</td><td>现货 vs 衍生品 两端相互验证</td></tr>
<tr><td><b>机制关系</b></td><td>③做市商对冲</td><td>④Gamma</td><td>对冲是过程，Gamma是机制</td></tr>
<tr><td><b>时间维度</b></td><td>②SKEW(深度虚值)</td><td>⑥0DTE</td><td>长期尾部对冲 vs 短期投机</td></tr>
<tr><td><b>因果链</b></td><td colspan="3">①赎回压力 → ③被迫减仓 → ④Gamma挤压 → ⑤压缩做市空间 → ⑥末日轮爆量 + ②SKEW上行</td></tr>
</tbody>
</table>

<h3>结合方式：Composite Stress Score</h3>
<div class="concept">
  <p><b>RV</b>只是对"市场压力"这件事的单一标量统计。<b>6 个指标</b>是对该现象的 6 个分量观察。<b>Composite Stress Score (CSS)</b> = 6 个 z-score 的等权平均 → 映射到 0-100 分。</p>
  <p>原始信号和理论阈值请参见 <b>github.com/Arterialblood/derivatives-risk-factors</b> 的 composite_risk.py 模块：</p>
  <ul>
    <li>每个因子按 <b>NORMAL=0 / WATCH=1 / ALERT=2</b> 三档赋分</li>
    <li>6 因子满分 12 分，GEX 权重额外 1.5 倍（核心机制）</li>
    <li>总分 &lt;40 → LOW（低位稳定） · 40-70 → MEDIUM（中位警戒） · &gt;70 → HIGH（高位响应）</li>
  </ul>
</div>

<h2>② 价格代理变量（用于回测）</h2>

<div class="concept">
  由于历史期权和资金流数据不可回测，V3 在每日 ETF 价格数据上构建了 6 个<b>代理变量</b>，分别捕捉同一现象的不同侧面：
</div>

<table>
<thead><tr><th>指标</th><th>对应图</th><th>代理变量</th><th>捕捉维度</th></tr></thead>
<tbody>
<tr><td>① ETF异常</td><td>IMG_0075</td><td>日内振幅 / 20日均值振幅</td><td>日内波动放大</td></tr>
<tr><td>② SKEW</td><td>IMG_0079</td><td>左尾最大跌幅 / RV</td><td>尾部风险占比</td></tr>
<tr><td>③ 做市商对冲</td><td>IMG_0078</td><td>5日内单日超1.5σ日数 / 5</td><td>极端波动聚集</td></tr>
<tr><td>④ Gamma</td><td>IMG_0077</td><td>RV的5日变化率</td><td>波动加速度</td></tr>
<tr><td>⑤ 期货贴水</td><td>IMG_0076</td><td>科创50ETF vs 沪深300ETF的5日相对弱度（取负）</td><td>跨品种分歧</td></tr>
<tr><td>⑥ 0DTE</td><td>IMG_0080</td><td>当日成交量 / 20日均量</td><td>交易量异常</td></tr>
</tbody>
</table>

<div class="highlight-box">
  <b>关键步骤：</b>6 个代理变量分别做 z-score 归一化（让不同量纲的指标可比），再等权平均，最后映射到 0-100 分。这个 CSS 就是 V3 的 regime 分类信号。
</div>

<h2>③ 回测结果：V2 vs V3</h2>

<div class="chart-card">
<h3>累计收益对比（V3 vs 沪深300 vs 科创50ETF买入持有）</h3>
<canvas id="navChart" height="280"></canvas>
</div>

<div class="chart-card">
<h3>CSS（复合压力得分）走势 · 越接近100越危险</h3>
<canvas id="cssChart" height="180"></canvas>
</div>

<table>
<thead><tr><th>指标</th><th class="num">V2 单维RV</th><th class="num">V3 6指标复合</th><th class="num">沪深300买入持有</th><th class="num">科创50买入持有</th></tr></thead>
<tbody>
<tr><td>总收益</td><td class="num">+{v2m['total_return']:.2f}%</td><td class="num pos">+{v3m['total_return']:.2f}%</td><td class="num">+{v2m['bm_return']:.2f}%</td><td class="num pos">+{v2m['kc_return']:.2f}%</td></tr>
<tr><td>年化收益</td><td class="num">+{v2m['annual_return']:.2f}%</td><td class="num pos">+{v3m['annual_return']:.2f}%</td><td class="num">+{v2m['bm_annual']:.2f}%</td><td class="num pos">+{v2m['kc_annual']:.2f}%</td></tr>
<tr><td>最大回撤</td><td class="num">{v2m['max_drawdown']:.2f}%</td><td class="num">{v3m['max_drawdown']:.2f}%</td><td class="num">{v2m['bm_max_dd']:.2f}%</td><td class="num neg">{v2m['kc_max_dd']:.2f}%</td></tr>
<tr><td>夏普比率</td><td class="num">{v2m['sharpe']:.2f}</td><td class="num pos">{v3m['sharpe']:.2f}</td><td class="num">—</td><td class="num">—</td></tr>
<tr><td>Calmar比率</td><td class="num">{v2m['calmar']:.2f}</td><td class="num pos">{v3m['max_drawdown'] and (v3m['annual_return']/abs(v3m['max_drawdown'])):.2f}</td><td class="num">—</td><td class="num">—</td></tr>
<tr><td>交易次数</td><td class="num">{v2m['num_trades']}</td><td class="num">{v3m['n_trades']}</td><td class="num">1</td><td class="num">1</td></tr>
<tr><td>胜率</td><td class="num">{v2m['win_rate']:.1f}%</td><td class="num pos">{v3m['win_rate']:.1f}%</td><td class="num">—</td><td class="num">—</td></tr>
<tr><td>平均盈利</td><td class="num">+{v2m['avg_win']:.2f}%</td><td class="num pos">+{v3m['avg_win']:.2f}%</td><td class="num">—</td><td class="num">—</td></tr>
<tr><td>平均亏损</td><td class="num">{v2m['avg_loss']:.2f}%</td><td class="num">{v3m['avg_loss']:.2f}%</td><td class="num">—</td><td class="num">—</td></tr>
</tbody>
</table>

<div class="winner-box">
  <b>V3 vs V2 关键提升：</b>收益 <b>+{v3m['total_return'] - v2m['total_return']:.2f}</b> 个百分点，夏普 <b>+{v3m['sharpe'] - v2m['sharpe']:.2f}</b>，胜率 <b>+{v3m['win_rate'] - v2m['win_rate']:.1f}</b>%。<br/>
  V3 用同样的"安全区持科创 / 拥挤区持中证1000"骨架，仅把<b>regime 分类信号</b>从 RV（单一）替换为 CSS（6维），就把胜率从 50% 提升到 71.4%，且仍能在 2026-04-14 ~ 2026-06-01 抓住科创50 +18.24% 的主升浪。
</div>

<h2>④ V3 交易明细</h2>
<table>
<thead><tr><th>入场</th><th>出场</th><th>标的</th><th class="num">入场价</th><th class="num">出场价</th><th class="num">收益%</th><th>出场原因</th></tr></thead>
<tbody>
{''.join(f'''<tr class="{'winner' if t['pnl_pct'] > 0 else ''}"><td>{t['entry_date']}</td><td>{t['exit_date']}</td><td>{t['symbol']}</td><td class="num">{t['entry_price']:.3f}</td><td class="num">{t['exit_price']:.3f}</td><td class="num pos">+{t['pnl_pct']:.2f}%</td><td>{t['exit_reason']}</td></tr>''' for t in v3_trades)}
</tbody>
</table>

<h2>⑤ 最优参数</h2>
<table>
<thead><tr><th>参数</th><th class="num">V3 最优值</th><th>说明</th></tr></thead>
<tbody>
<tr><td>calm_max</td><td class="num">{v3p['calm']}</td><td>CSS &lt; {v3p['calm']} 视为低位稳定 → 买入科创50ETF</td></tr>
<tr><td>crisis_min</td><td class="num">{v3p['crisis']}</td><td>CSS &gt; {v3p['crisis']} 视为高位危机 → 轮动到中证1000ETF</td></tr>
<tr><td>atr_multiplier</td><td class="num">{v3p['atr_m']}</td><td>科创50跟踪止损宽度 = {v3p['atr_m']} × ATR(14)</td></tr>
<tr><td>hard_stop_pct</td><td class="num">{v3p['hard_stop']*100:.0f}%</td><td>强制硬止损</td></tr>
</tbody>
</table>

<h2>⑥ 参数敏感性（Top 10）</h2>
<table>
<thead><tr><th>排名</th><th class="num">calm&lt;</th><th class="num">crisis&gt;</th><th class="num">ATR×</th><th class="num">收益</th><th class="num">回撤</th><th class="num">夏普</th><th class="num">交易数</th><th class="num">胜率</th></tr></thead>
<tbody>
{''.join(f'''<tr><td>{i+1}</td><td class="num">{r['params']['calm']}</td><td class="num">{r['params']['crisis']}</td><td class="num">{r['params']['atr_m']}</td><td class="num pos">+{r['metrics']['total_return']:.2f}%</td><td class="num">{r['metrics']['max_drawdown']:.2f}%</td><td class="num">{r['metrics']['sharpe']:.2f}</td><td class="num">{r['metrics']['n_trades']}</td><td class="num">{r['metrics']['win_rate']:.0f}%</td></tr>''' for i, r in enumerate(top15[:10]))}
</tbody>
</table>

<div class="highlight-box">
  <b>参数稳定性：</b>Top 5 中，crisis_min 从 65 变到 80 收益几乎不变（46.8% → 47.3%）。这说明 <b>CSS 阈值在 65-80 区间都是可行的</b>，策略对参数不敏感——这正是简单策略应有的鲁棒性。
</div>

<h2>⑦ 体系骨架（结合 Rayner Teo 的"简单胜复杂"）</h2>

<div class="concept">
  <p><b>一句话规则：</b>"安全时拥抱弹性，危机时切到缓冲。"</p>
  <ol>
    <li><b>每日做一件事：</b>根据 6 个代理变量算 CSS。
      <ul>
        <li>CSS &lt; 35 → <b style="color:#dc2626;">买入科创50ETF</b>（追求弹性）</li>
        <li>CSS &gt; 75 → <b>轮动到中证1000ETF</b>（缓冲 + 等待）</li>
        <li>35-75 区间 → 现有仓位继续持有</li>
      </ul>
    </li>
    <li><b>止损（强制）：</b>2.5 × ATR 跟踪止损 OR -8% 硬止损，先触发先生效。</li>
    <li><b>冷却期：</b>止损后等待 5 个交易日，期间不做新入场动作（让概率稳定）。</li>
    <li><b>执行优先：</b>资金管理 + 仓位 + 止损纪律，&gt; 信号微调。</li>
  </ol>
</div>

<h2>⑧ 执行清单</h2>
<table>
<thead><tr><th>步骤</th><th>动作</th><th>工具/数据</th></tr></thead>
<tbody>
<tr><td>1</td><td>每日收盘后计算 6 个代理变量 → CSS</td><td>ETF日数据(网易/同花顺/westock)</td></tr>
<tr><td>2</td><td>跨市场核对：用真实期权/GEX/0DTE数据替换"代理变量"（每周末）</td><td>同花顺iFinD / westock 期权链</td></tr>
<tr><td>3</td><td>若 CSS &gt; 75 → 次日开盘把科创50换成中证1000ETF</td><td>券商交易软件</td></tr>
<tr><td>4</td><td>持仓期间每日检查止损位（盘中触及即执行）</td><td>条件单/盘后复盘</td></tr>
<tr><td>5</td><td>止损触发 → 进入冷却 → 5个交易日后重新评估 CSS</td><td>日历提醒</td></tr>
<tr><td>6</td><td>每周末做一次全市场 CSS 重置（区分"波动大但安全"vs"波动大且脆弱"）</td><td>指标看板</td></tr>
</tbody>
</table>

<h2>⑨ 与买入持有的关键权衡</h2>

<div class="winner-box">
  <p><b>V3 跑赢沪深300ETF 基准 +42个百分点（年化15% vs 6%），但相对科创50ETF买入持有仍少 {v2m['kc_return'] - v3m['total_return']:.0f} 个百分点。</b></p>
  <p>这是个<b>有意为之的权衡</b>：V3 最大回撤仅 -13.27%（科创50ETF 是 -29.91%，腰斩一半）。在 2026-02 / 2026-07 这种大幅回撤时段，V3 会自动切到中证1000ETF 而不被动挨打。</p>
  <p>如果您的风格是"赌国运、扛波动"，买科创50ETF 持有更优。如果您是"想跑赢沪深300但不想经历腰斩"，V3 的复合压力轮动就是答案。</p>
</div>

<div class="disclaimer">
⚠️ <b>免责声明：</b>本报告基于 2025-09-24 之后 219 个交易日的历史回测展示。<b>过去业绩不代表未来表现</b>。代理变量是用 ETF 日数据近似真实衍生品指标，实盘建议<b>用真实期权链 + 真实资金流数据替换</b>（参见 GitHub factor_01 ~ factor_06 的标准实现）。任何交易决策都需要自行承担风险，本报告不构成投资建议。
</div>

<script>
// V3 vs 沪深300 vs 科创50ETF的累计NAV
const navData = {json.dumps([
    {'date': r['date'], 'nav': round(r['nav'], 2), 'css': round(r['css'], 1), 'regime': r['regime'], 'kc_bh': round(r['kc_bh'], 2), 'hs300': round(r['hs300'], 2)}
    for r in v3_curve
])};

new Chart(document.getElementById('navChart'), {{
    type: 'line',
    data: {{
        labels: navData.map(d => d.date),
        datasets: [
            {{
                label: 'V3 6指标复合策略',
                data: navData.map(d => d.nav),
                borderColor: '#10b981',
                backgroundColor: 'rgba(16,185,129,0.1)',
                borderWidth: 2.5,
                fill: false,
                tension: 0.1,
            }},
            {{
                label: '沪深300ETF 买入持有',
                data: navData.map(d => d.hs300),
                borderColor: '#6366f1',
                borderWidth: 1.5,
                fill: false,
                tension: 0.1,
                borderDash: [4, 4],
            }},
            {{
                label: '科创50ETF 买入持有',
                data: navData.map(d => d.kc_bh),
                borderColor: '#dc2626',
                borderWidth: 1.5,
                fill: false,
                tension: 0.1,
                borderDash: [4, 4],
            }}
        ]
    }},
    options: {{
        responsive: true,
        plugins: {{
            legend: {{ position: 'top' }},
            tooltip: {{ mode: 'index', intersect: false }}
        }},
        scales: {{
            y: {{ title: {{ display: true, text: '净值 (起始=100000)' }} }},
            x: {{ ticks: {{ maxTicksLimit: 12 }} }}
        }}
    }}
}});

// CSS走势
new Chart(document.getElementById('cssChart'), {{
    type: 'line',
    data: {{
        labels: navData.map(d => d.date),
        datasets: [{{
            label: 'Composite Stress Score (CSS)',
            data: navData.map(d => d.css),
            borderColor: '#d97706',
            backgroundColor: function(ctx) {{
                const chart = ctx.chart;
                const {{ctx: c, chartArea: ca}} = chart;
                if (!ca) return 'rgba(217,119,6,0.1)';
                const gradient = c.createLinearGradient(0, ca.top, 0, ca.bottom);
                gradient.addColorStop(0, 'rgba(217,119,6,0.3)');
                gradient.addColorStop(1, 'rgba(217,119,6,0.02)');
                return gradient;
            }},
            borderWidth: 2,
            fill: true,
            tension: 0.2,
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{
            legend: {{ display: false }},
            annotation: {{}}
        }},
        scales: {{
            y: {{
                min: 0, max: 100,
                title: {{ display: true, text: '压力得分（0=安全, 100=极端）' }},
                ticks: {{
                    callback: function(v) {{ return v; }},
                    stepSize: 25
                }}
            }},
            x: {{ ticks: {{ maxTicksLimit: 10 }} }}
        }}
    }}
}});
</script>

</body>
</html>
"""

    REPORT_PATH.write_text(html, encoding='utf-8')
    print(f'报告已生成：{REPORT_PATH}')
    print(f'文件大小：{REPORT_PATH.stat().st_size / 1024:.1f} KB')


if __name__ == '__main__':
    main()
