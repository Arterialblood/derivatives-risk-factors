"""
V3 策略回测：用"6指标复合压力信号"取代V2的单一RV指标。

设计逻辑：
- RV只是对"市场压力"这件事的单一标量统计；
- 6张图（ETF异常/期货贴水/Gamma挤压/做市商对冲/SKEW/0DTE）是对同一现象的6个观察窗口；
- 用价格数据能算出的6个代理变量（z-score归一化）→ 复合压力得分（Composite Stress Score）；
- 复合得分 > 70 → 高位危机 → 轮动到中证1000ETF
- 复合得分 < 40 → 低位稳定 → 持有科创50ETF

对比：V2（仅RV） vs V3（6指标复合得分）
"""

import json
import math
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"

# ────────────────────────────────────────
# 数据加载（复用）
# ────────────────────────────────────────

def load_kline(filename):
    """加载数据并转换为升序（按日期从早到晚）"""
    path = DATA_DIR / filename
    with open(path) as f:
        raw = json.load(f)
    # 数据结构: data.nodes 是降序，最新在前；需要反转
    nodes = raw['data']['nodes']
    # 转换为升序
    nodes = list(reversed(nodes))
    # 字段映射：last → close
    for n in nodes:
        n['close'] = n['last']
    return {'kline': nodes, 'name': filename}

def calc_daily_returns(prices):
    return [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]

def calc_rv(returns, window=20):
    """20日年化RV"""
    import statistics
    out = [None] * len(returns)
    for i in range(window - 1, len(returns)):
        seg = returns[i - window + 1: i + 1]
        std = statistics.stdev(seg)
        out[i] = std * math.sqrt(252)
    return out

def calc_atr(high, low, close, window=14):
    """ATR(14)"""
    n = len(close)
    tr = [0.0] * n
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    atr = [None] * n
    if window <= n:
        prev_sum = sum(tr[:window])
        atr[window - 1] = prev_sum / window
        for i in range(window, n):
            atr[i] = (atr[i-1] * (window - 1) + tr[i]) / window
    return atr

def calc_sma(prices, window):
    n = len(prices)
    sma = [None] * n
    if window <= n:
        s = sum(prices[:window])
        sma[window - 1] = s / window
        for i in range(window, n):
            s = s - prices[i - window] + prices[i]
            sma[i] = s / window
    return sma

# ────────────────────────────────────────
# 6个代理指标（基于可获取的数据）
# ────────────────────────────────────────

def proxy_etf_anomaly(high, low, close, window=20):
    """① ETF异常波动 (IMG_0075)
       代理：日内振幅 / 20日均值振幅 (>1.5为异常)
       含义：日内振幅放大 = 流动性缺失/资金集中赎回时的异常波动
    """
    n = len(close)
    intraday_range = [(high[i] - low[i]) / close[i] for i in range(n)]
    avg_range = [None] * n
    for i in range(window - 1, n):
        seg = intraday_range[i - window + 1: i + 1]
        avg_range[i] = sum(seg) / window
    return [intraday_range[i] / avg_range[i] if avg_range[i] else 1.0 for i in range(n)]

def proxy_futures_basis(kc_close, hs_close, window=20):
    """⑤ 股指期货大幅贴水 (IMG_0076)
       代理：科创50ETF相对沪深300ETF的相对强弱
       当kk大跌时相对强弱=短期现货看空信号 → 类似期货贴水恶化
    """
    n = len(kc_close)
    rel_strength = [None] * n
    for i in range(1, n):
        kc_ret = (kc_close[i] - kc_close[i-1]) / kc_close[i-1]
        hs_ret = (hs_close[i] - hs_close[i-1]) / hs_close[i-1]
        # 当日相对强弱差，负值意味着科创50比沪深300弱
        rel_strength[i] = kc_ret - hs_ret
    # 平滑：5日移动平均（处理None）
    smoothed = [None] * n
    s = 5
    for i in range(s - 1, n):
        valid = [rel_strength[j] for j in range(i - s + 1, i + 1) if rel_strength[j] is not None]
        if valid:
            smoothed[i] = -sum(valid) / len(valid)  # 取负：负相对强弱=贴水恶化
    return smoothed

def proxy_gex(returns, window=20):
    """④ Gamma挤压 (IMG_0077)
       代理：日内已实现波动率的"加速度"
       当RV快速上升 → 类似Gamma从正转负的波动放大效应
    """
    n = len(returns)
    import statistics
    rv = [None] * n
    for i in range(window - 1, n):
        seg = returns[i - window + 1: i + 1]
        rv[i] = statistics.stdev(seg) * math.sqrt(252)
    # 5日RV变化率
    gex_proxy = [None] * n
    for i in range(window + 4, n):
        if rv[i] and rv[i-5] and rv[i-5] > 0:
            gex_proxy[i] = (rv[i] - rv[i-5]) / rv[i-5]
    return gex_proxy

def proxy_dealer_hedge(returns, window=20):
    """③ 做市商被迫对冲 (IMG_0078)
       代理：单日绝对收益 > 2sigma 的次数（5日内）
       含义：极端单日波动聚集 = 强迫对冲盘的迹象
    """
    n = len(returns)
    import statistics
    sigma_count = [None] * n
    for i in range(window - 1, n):
        seg = returns[i - window + 1: i + 1]
        if len(seg) >= 5:
            mu = sum(seg) / len(seg)
            sd = statistics.stdev(seg) if len(seg) > 1 else 0.001
            # 计算5日内绝对值>1.5sigma的天数
            last5 = seg[-5:]
            count = sum(1 for r in last5 if abs(r - mu) > 1.5 * sd)
            sigma_count[i] = count / 5.0  # 比例
    return sigma_count

def proxy_skew(returns, window=20):
    """② 深度虚值期权暴涨 (IMG_0079)
       代理：左尾收益率与RV的比例（max(0, -return) / RV）
       含义：极端左尾事件的占比，类似SKEW上行信号
    """
    n = len(returns)
    import statistics
    skew_proxy = [None] * n
    for i in range(window - 1, n):
        seg = returns[i - window + 1: i + 1]
        rv = statistics.stdev(seg) * math.sqrt(252) if len(seg) > 1 else 0.01
        left_tail = max([-r for r in seg if r < 0] or [0])
        skew_proxy[i] = left_tail / rv if rv > 0 else 0
    return skew_proxy

def proxy_0dte(volume, window=20):
    """⑥ 末日轮爆量 (IMG_0080)
       代理：当日成交量 / 20日均量
       含义：交易量异常放大 = 短期投机/对冲需求暴增
    """
    n = len(volume)
    vol_ratio = [None] * n
    for i in range(window - 1, n):
        avg = sum(volume[i - window + 1: i + 1]) / window
        vol_ratio[i] = volume[i] / avg if avg > 0 else 1.0
    return vol_ratio

# ────────────────────────────────────────
# Z-score 归一化（横向对比：把不同量纲的指标合并）
# ────────────────────────────────────────

def zscore_series(series):
    """把整个序列做z-score归一化（使用整个序列的mean/std做baseline）"""
    valid = [v for v in series if v is not None]
    if not valid:
        return series
    import statistics
    mu = statistics.mean(valid)
    sd = statistics.stdev(valid) if len(valid) > 1 else 0.001
    return [(v - mu) / sd if v is not None else None for v in series]

# ────────────────────────────────────────
# 复合压力得分
# ────────────────────────────────────────

def composite_stress_score(etf, basis, gex, hedge, skew, vol_ratio):
    """Composite Stress Score = 6个z-score的等权平均
       0-100 标尺：把均值映射到 0-100 (假设z=0 → 50, z=2 → 100, z=-2 → 0)
       各series长度可能不同（因None填充），用最大长度，其它用None填充
    """
    n = max(len(s) for s in [etf, basis, gex, hedge, skew, vol_ratio])

    # 将各序列pad到相同长度
    def pad(s):
        return s + [None] * (n - len(s))

    z_etf = zscore_series(pad(etf))
    z_basis = zscore_series(pad(basis))
    z_gex = zscore_series(pad(gex))
    z_hedge = zscore_series(pad(hedge))
    z_skew = zscore_series(pad(skew))
    z_vol = zscore_series(pad(vol_ratio))

    scores = [None] * n
    for i in range(n):
        z_values = []
        for z in [z_etf[i], z_basis[i], z_gex[i], z_hedge[i], z_skew[i], z_vol[i]]:
            if z is not None:
                z_values.append(z)
        if z_values:
            avg_z = sum(z_values) / len(z_values)
            # 映射到0-100：z=0 → 50, ±2σ覆盖0-100
            score = max(0, min(100, 50 + avg_z * 25))
            scores[i] = score
    return scores

# ────────────────────────────────────────
# 策略回测 (与V2相同的rotation逻辑)
# ────────────────────────────────────────

def run_v3_strategy(kc_data, hs_data, zz_data,
                     calm_max=35, crisis_min=70,
                     atr_multiplier=3.5, hard_stop_pct=0.08,
                     cooldown_score=55,
                     start_idx=30):

    kc = kc_data["kline"]
    hs = hs_data["kline"]
    zz = zz_data["kline"]

    n = len(kc)
    kc_close = [d["close"] for d in kc]
    kc_high = [d["high"] for d in kc]
    kc_low = [d["low"] for d in kc]
    kc_vol = [d["volume"] for d in kc]

    hs_close = [d["close"] for d in hs]
    zz_close = [d["close"] for d in zz]

    # 计算所有指标
    returns = calc_daily_returns(kc_close)
    atr = calc_atr(kc_high, kc_low, kc_close, 14)
    sma20 = calc_sma(kc_close, 20)

    # 6个代理变量
    etf_anom = proxy_etf_anomaly(kc_high, kc_low, kc_close)
    basis = proxy_futures_basis(kc_close, hs_close)
    gex = proxy_gex(returns)
    hedge = proxy_dealer_hedge(returns)
    skew = proxy_skew(returns)
    vol_ratio = proxy_0dte(kc_vol)

    # 复合压力得分
    css = composite_stress_score(etf_anom, basis, gex, hedge, skew, vol_ratio)

    # 用科创50的回测作为基础（因为ETF异常等是科创的）
    # 然后用复合得分做regime切换
    # V3的创新：用CSS替代RV做regime分类

    # 与V2相同：用zz1000 vs kechuang切换
    # 但regime阈值用CSS (35-70) 而不是RV

    # 简化版：用CSS阈值 (calm=35, crisis=70) + V2相同的入场止损

    dates = [d["date"] for d in kc]
    cash = 100000.0
    position = None  # None / 'kc' / 'zz'
    shares = 0
    entry_price = 0
    trailing_stop = 0
    cooldown_until = 0
    trades = []
    daily_values = []

    # 沪深300和科创50买入持有基准
    hs_nav0 = hs_close[0]
    kc_nav0 = kc_close[0]

    for i in range(start_idx, n):
        date = dates[i]
        price = kc_close[i]
        zz_price = zz_close[i]
        score = css[i]
        ma = sma20[i]
        a = atr[i]

        if i == 0:
            nav_kc = 100000.0
        else:
            nav_kc = 100000.0 * (kc_close[i] / kc_close[max(0, i - 1)])

        # Regime基于CSS而不是RV
        if score is None:
            regime = 'transition'
        elif score < calm_max:
            regime = 'calm'
        elif score > crisis_min:
            regime = 'crisis'
        else:
            regime = 'transition'

        # 处理强制止损后冷却
        now_idx = i
        if cooldown_until > now_idx:
            pass  # 冷却期，不开新仓

        # 当前NAV
        if position == 'kc':
            cur_val = shares * price
        elif position == 'zz':
            cur_val = shares * zz_price
        else:
            cur_val = cash

        hs_bh_val = 100000.0 * (hs_close[i] / hs_nav0)
        kc_bh_val = 100000.0 * (kc_close[i] / kc_nav0)

        daily_values.append({
            'date': date,
            'nav': cur_val,
            'position': position,
            'css': score,
            'ma': ma,
            'regime': regime,
            'kc_close': price,
            'zz_close': zz_price,
            'hs300': hs_bh_val,
            'kc_bh': kc_bh_val,
        })

        # ─── 仓位决策 ───
        if position == 'kc':
            # 更新trailing stop
            new_stop = max(trailing_stop, price - atr_multiplier * a)
            trailing_stop = new_stop
            # 止损检测
            if price <= trailing_stop or price <= entry_price * (1 - hard_stop_pct):
                # 止损触发
                cash = shares * price
                pnl_pct = (price - entry_price) / entry_price * 100
                trades.append({
                    'entry_date': dates[entry_idx],
                    'exit_date': date,
                    'symbol': 'kechuang',
                    'entry_price': entry_price,
                    'exit_price': price,
                    'pnl_pct': round(pnl_pct, 2),
                    'exit_reason': 'trailing_stop' if price <= trailing_stop else 'hard_stop'
                })
                shares = 0
                position = None
                cooldown_until = i + cooldown_days  # 冷却期

        elif position == 'zz':
            # 中证1000止损（用其自身的ATR和均线）
            # 简化：-8%硬止损
            if price <= entry_price * (1 - hard_stop_pct):
                cash = shares * zz_price
                pnl_pct = (zz_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_date': dates[entry_idx],
                    'exit_date': date,
                    'symbol': 'zz1000',
                    'entry_price': entry_price,
                    'exit_price': zz_price,
                    'pnl_pct': round(pnl_pct, 2),
                    'exit_reason': 'hard_stop'
                })
                shares = 0
                position = None
                cooldown_until = i + cooldown_days

        else:
            # 空仓 → 决定是否入场
            if cooldown_until <= i:
                if regime == 'calm' and ma is not None and price > ma:
                    # 入场科创50
                    shares = cash / price
                    entry_price = price
                    entry_idx = i
                    position = 'kc'
                    trailing_stop = price - atr_multiplier * a
                    cooldown_days = 5  # 默认5天冷却
                    cash = 0
                elif regime == 'crisis':
                    # 入场中证1000
                    shares = cash / zz_price
                    entry_price = zz_price
                    entry_idx = i
                    position = 'zz'
                    cooldown_days = 5
                    cash = 0

    # 计算总指标
    final_val = daily_values[-1]['nav'] if daily_values else 100000
    total_return = (final_val / 100000 - 1) * 100
    n_days = len(daily_values)
    annual_return = ((final_val / 100000) ** (252 / n_days) - 1) * 100 if n_days > 0 else 0

    # 最大回撤
    peak = -1e18
    max_dd = 0
    for dv in daily_values:
        peak = max(peak, dv['nav'])
        dd = (dv['nav'] - peak) / peak * 100
        max_dd = min(max_dd, dd)

    # 夏普比率
    nav_ret = []
    for j in range(1, len(daily_values)):
        nav_ret.append((daily_values[j]['nav'] - daily_values[j-1]['nav']) / daily_values[j-1]['nav'])
    import statistics
    sharpe = (statistics.mean(nav_ret) / statistics.stdev(nav_ret) * math.sqrt(252)) if len(nav_ret) > 1 and statistics.stdev(nav_ret) > 0 else 0

    # 胜率
    wins = sum(1 for t in trades if t['pnl_pct'] > 0)
    losses = sum(1 for t in trades if t['pnl_pct'] < 0)
    avg_win = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] > 0) / wins if wins else 0
    avg_loss = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] < 0) / losses if losses else 0

    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'n_trades': len(trades),
        'win_rate': wins / len(trades) * 100 if trades else 0,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'final_value': final_val,
        'n_days': n_days,
        'trades': trades,
        'daily_values': daily_values,
        'css_series': css,
    }


# ────────────────────────────────────────
# 当前信号输出：每次运行结束后打印当前因子值和买卖建议
# ────────────────────────────────────────

def output_current_signal(kc_data, hs_data, best_result, best_params):
    """输出最新的6个因子值、CSS得分、当前持仓状态和买卖建议"""

    def pad_to_n(s, n):
        """把序列pad到长度n"""
        return list(s) + [None] * (n - len(s))

    kc = kc_data["kline"]
    hs = hs_data["kline"]
    n = len(kc)
    kc_close = [d["close"] for d in kc]
    kc_high = [d["high"] for d in kc]
    kc_low = [d["low"] for d in kc]
    kc_vol = [d["volume"] for d in kc]
    hs_close = [d["close"] for d in hs]
    returns = calc_daily_returns(kc_close)

    # 计算6个代理变量（returns长度为n-1，需要对齐到n）
    etf_anom = proxy_etf_anomaly(kc_high, kc_low, kc_close)
    basis = proxy_futures_basis(kc_close, hs_close)
    gex = proxy_gex(returns)
    hedge = proxy_dealer_hedge(returns)
    skew = proxy_skew(returns)
    vol_ratio = proxy_0dte(kc_vol)

    # 对齐到价格数组长度n（returns-based的因子需要前移1位+补None）
    def align_to_n(s, n):
        """把returns-based的序列(长度n-1)对齐到价格数组(长度n)"""
        return [None] + list(s)  # 前面补一个None，因为returns[0]对应price[1]

    z_etf = zscore_to_score(pad_to_n(etf_anom, n))
    z_basis = zscore_to_score(pad_to_n(basis, n))
    z_gex = zscore_to_score(pad_to_n(align_to_n(gex, n), n))
    z_hedge = zscore_to_score(pad_to_n(align_to_n(hedge, n), n))
    z_skew = zscore_to_score(pad_to_n(align_to_n(skew, n), n))
    z_vol = zscore_to_score(pad_to_n(vol_ratio, n))

    # 复合CSS
    css = [None] * n
    for i in range(n):
        z_values = []
        for z in [z_etf[i], z_basis[i], z_gex[i], z_hedge[i], z_skew[i], z_vol[i]]:
            if z is not None:
                z_values.append(z)
        if z_values:
            css[i] = sum(z_values) / len(z_values)

    # 获取最新一天的值
    last_idx = n - 1
    last_date = kc[last_idx]["date"]
    last_price = kc_close[last_idx]

    # MA20和ATR
    sma20 = calc_sma(kc_close, 20)
    atr = calc_atr(kc_high, kc_low, kc_close, 14)
    last_ma = sma20[last_idx]
    last_atr = atr[last_idx]
    last_css = css[last_idx]

    # 当前持仓状态（从回测结果获取）
    last_dv = best_result['daily_values'][-1]
    current_position = last_dv['position']

    # Regime判断
    if last_css is None:
        regime = 'transition'
    elif last_css < best_params['calm']:
        regime = 'calm'
    elif last_css > best_params['crisis']:
        regime = 'crisis'
    else:
        regime = 'transition'

    # 生成买卖建议
    if current_position == 'kc':
        trailing_stop = last_price - best_params['atr_m'] * last_atr if last_atr else last_price * 0.92
        hard_stop = last_price * (1 - 0.08)
        effective_stop = max(trailing_stop, hard_stop)
        recommendation = f"持有科创50ETF (当前价 {last_price:.3f})"
        recommendation += f" | 跟踪止损: {effective_stop:.3f} ({(effective_stop/last_price-1)*100:.1f}%)"
        action = 'HOLD_KC'
    elif current_position == 'zz':
        hard_stop = last_price * (1 - 0.08)  # 简化：用KC价格做参考
        recommendation = f"持有中证1000ETF"
        action = 'HOLD_ZZ'
    else:
        # 空仓 → 检查是否应该入场
        if regime == 'calm' and last_ma is not None and last_price > last_ma:
            recommendation = (f"建议买入科创50ETF "
                            f"(CSS={last_css:.1f}<{best_params['calm']}, "
                            f"价格{last_price:.3f}>MA20={last_ma:.3f})")
            action = 'BUY_KC'
        elif regime == 'crisis':
            recommendation = (f"建议轮动到中证1000ETF "
                            f"(CSS={last_css:.1f}>{best_params['crisis']})")
            action = 'BUY_ZZ'
        else:
            recommendation = (f"观望 (CSS={last_css:.1f}, 体制={regime})")
            action = 'WAIT'

    # 因子值表
    factor_values = {
        '①ETF异常': z_etf[last_idx],
        '②期货贴水': z_basis[last_idx],
        '③Gamma挤压': z_gex[last_idx],
        '④做市商对冲': z_hedge[last_idx],
        '⑤SKEW': z_skew[last_idx],
        '⑥0DTE爆量': z_vol[last_idx],
        '★复合CSS': last_css,
    }

    # 打印
    print(f'\n{"="*60}')
    print(f'  当前信号快照 — {last_date}')
    print(f'{"="*60}')
    print(f'\n  6个因子值 (0=最安全, 100=最危险):')
    for name, val in factor_values.items():
        if val is not None:
            bar_len = int(val / 5)
            bar = '█' * bar_len + '░' * (20 - bar_len)
            status = '⚠️危险' if val > 75 else ('⚡注意' if val > 50 else '✅安全')
            print(f'  {name:12s} {val:6.1f} |{bar}| {status}')
        else:
            print(f'  {name:12s}   N/A  |{"?"*20}| 数据不足')

    print(f'\n  市场状态:')
    print(f'    科创50ETF价格:  {last_price:.3f}')
    print(f'    MA20:           {last_ma:.3f}' if last_ma else '    MA20:           N/A')
    print(f'    ATR(14):        {last_atr:.4f}' if last_atr else '    ATR(14):        N/A')
    print(f'    复合压力得分:   {last_css:.1f}' if last_css else '    复合压力得分:   N/A')
    print(f'    市场体制:       {regime}')
    print(f'    当前持仓:       {current_position or "空仓"}')

    print(f'\n  >> 建议: {recommendation}')
    print(f'{"="*60}\n')

    # 保存到文件
    signal_output = {
        'date': last_date,
        'factors': {k: round(v, 2) if v is not None else None for k, v in factor_values.items()},
        'market': {
            'price': round(last_price, 4),
            'ma20': round(last_ma, 4) if last_ma else None,
            'atr14': round(last_atr, 6) if last_atr else None,
            'css': round(last_css, 2) if last_css else None,
            'regime': regime,
        },
        'position': current_position,
        'action': action,
        'recommendation': recommendation,
    }

    with open(DATA_DIR.parent / 'current_signal.json', 'w') as f:
        json.dump(signal_output, f, ensure_ascii=False, indent=2)

    print(f'当前信号已保存到 current_signal.json')
    return signal_output


def zscore_to_score(series):
    """把单因子序列做z-score后映射到0-100"""
    valid = [v for v in series if v is not None]
    if not valid:
        return series
    import statistics
    mu = statistics.mean(valid)
    sd = statistics.stdev(valid) if len(valid) > 1 else 0.001
    return [max(0, min(100, 50 + (v - mu) / sd * 25)) if v is not None else None for v in series]


def main():
    kc_data = load_kline('kechuang50_etf.json')
    hs_data = load_kline('hs300_etf.json')
    zz_data = load_kline('zz1000_etf.json')

    print(f'数据范围: {kc_data["kline"][0]["date"]} ~ {kc_data["kline"][-1]["date"]} ({len(kc_data["kline"])}天)')

    # 多种参数组合测试
    results = []

    for calm in [30, 35, 40]:
        for crisis in [65, 70, 75, 80]:
            for atr_m in [2.5, 3.0, 3.5, 4.0]:
                for hs_pct in [0.08]:
                    r = run_v3_strategy(
                        kc_data, hs_data, zz_data,
                        calm_max=calm,
                        crisis_min=crisis,
                        atr_multiplier=atr_m,
                        hard_stop_pct=hs_pct,
                    )
                    results.append({
                        'params': {'calm': calm, 'crisis': crisis, 'atr_m': atr_m, 'hard_stop': hs_pct},
                        'metrics': {
                            'total_return': r['total_return'],
                            'max_drawdown': r['max_drawdown'],
                            'sharpe': r['sharpe'],
                            'n_trades': r['n_trades'],
                            'win_rate': r['win_rate'],
                        }
                    })

    # 按总收益排名
    results.sort(key=lambda x: x['metrics']['total_return'], reverse=True)

    print('\n=== Top 15 参数组合 ===')
    for i, r in enumerate(results[:15]):
        p = r['params']
        m = r['metrics']
        print(f'{i+1:2d}. calm<{p["calm"]} crisis>{p["crisis"]} ATR×{p["atr_m"]} HS={p["hard_stop"]*100}%'
              f' | ret={m["total_return"]:+.2f}% dd={m["max_drawdown"]:.2f}% sharpe={m["sharpe"]:.2f}'
              f' trades={m["n_trades"]} win={m["win_rate"]:.0f}%')

    # 用最优参数运行完整回测
    best_params = results[0]['params']
    print(f'\n=== 用最优参数 full backtest: {best_params} ===')

    best = run_v3_strategy(
        kc_data, hs_data, zz_data,
        calm_max=best_params['calm'],
        crisis_min=best_params['crisis'],
        atr_multiplier=best_params['atr_m'],
        hard_stop_pct=best_params['hard_stop'],
    )

    print(f'\n最优参数表现:')
    print(f'  总收益:     {best["total_return"]:+.2f}%')
    print(f'  年化收益:   {best["annual_return"]:+.2f}%')
    print(f'  最大回撤:   {best["max_drawdown"]:.2f}%')
    print(f'  夏普比率:   {best["sharpe"]:.2f}')
    print(f'  交易次数:   {best["n_trades"]}')
    print(f'  胜率:       {best["win_rate"]:.1f}%')

    print(f'\n交易明细:')
    for t in best['trades']:
        print(f'  {t["entry_date"]} → {t["exit_date"]} ({t["exit_reason"]}): {t["symbol"]} {t["pnl_pct"]:+.2f}%')

    # 输出到文件
    output = {
        'version': 'V3 - 6指标复合压力信号',
        'data_range': {
            'start': kc_data['kline'][0]['date'],
            'end': kc_data['kline'][-1]['date'],
            'n_days': len(kc_data['kline']),
        },
        'best_params': best_params,
        'top_15': results[:15],
        'best_metrics': {
            'total_return': best['total_return'],
            'annual_return': best['annual_return'],
            'max_drawdown': best['max_drawdown'],
            'sharpe': best['sharpe'],
            'n_trades': best['n_trades'],
            'win_rate': best['win_rate'],
            'avg_win': best['avg_win'],
            'avg_loss': best['avg_loss'],
        },
        'trades': best['trades'],
        'css_series_last50': [
            {'date': best['daily_values'][j]['date'],
             'css': best['daily_values'][j]['css'],
             'regime': best['daily_values'][j]['regime']}
            for j in range(max(0, len(best['daily_values']) - 50), len(best['daily_values']), 2)
        ],
        'sampled_nav': [
            {
                'date': best['daily_values'][j]['date'],
                'nav': best['daily_values'][j]['nav'],
                'regime': best['daily_values'][j]['regime'],
                'css': best['daily_values'][j]['css'],
                'hs300': best['daily_values'][j]['hs300'],
                'kc_bh': best['daily_values'][j]['kc_bh'],
            }
            for j in range(0, len(best['daily_values']), 3)
        ],
    }

    with open(DATA_DIR.parent / 'backtest_v3_results.json', 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n完整结果已保存到 backtest_v3_results.json')

    # 输出当前因子值和买卖建议
    output_current_signal(kc_data, hs_data, best, best_params)


if __name__ == '__main__':
    main()
