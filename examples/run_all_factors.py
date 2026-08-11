"""
示例: 运行全部6个衍生品风险因子 + 综合风险评分。

使用2026-08-07实盘快照数据作为示例输入。
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from factors import (
    Factor0DTEVolumeSurge,
    FactorSkewIndex,
    FactorDealerHedgingRatio,
    FactorGammaExposure,
    FactorFuturesBasis,
    FactorETFAbnormalFlow,
    CompositeRiskScore,
)


def main():
    print("=" * 70)
    print("  衍生品市场风险监控因子 · 6因子全景扫描")
    print("  数据快照: 2026-08-07")
    print("=" * 70)

    # --- 因子 01: 末日轮爆量 ---
    f1 = Factor0DTEVolumeSurge()
    r1 = f1.calculate(today_volume=1_200_000, avg_volume_30d=550_000)
    print(f"\n[{r1.factor_id}] {r1.factor_name} ({r1.factor_name_en})")
    print(f"  值: {r1.value:.2f}x  信号: {r1.signal.value}")
    print(f"  {r1.description}")

    # --- 因子 02: SKEW ---
    f2 = FactorSkewIndex()
    r2 = f2.calculate(skew_value=141.23, vix_value=14.9)
    print(f"\n[{r2.factor_id}] {r2.factor_name} ({r2.factor_name_en})")
    print(f"  值: {r2.value:.1f}  信号: {r2.signal.value}")
    print(f"  {r2.description}")
    if r2.extra.get("low_vol_high_tail"):
        print(f"  ⚠ 低波动+高尾部风险矛盾组合已触发")

    # --- 因子 03: 做市商对冲占比 ---
    f3 = FactorDealerHedgingRatio()
    r3 = f3.calculate(hedge_volume_1h=680_000, total_volume_1h=1_000_000)
    print(f"\n[{r3.factor_id}] {r3.factor_name} ({r3.factor_name_en})")
    print(f"  值: {r3.value*100:.1f}%  信号: {r3.signal.value}")
    print(f"  {r3.description}")

    # --- 因子 04: GEX ---
    f4 = FactorGammaExposure()
    r4 = f4.calculate(gex_value=3.2)
    print(f"\n[{r4.factor_id}] {r4.factor_name} ({r4.factor_name_en})")
    print(f"  值: +${r4.value:.1f}B  信号: {r4.signal.value}")
    print(f"  {r4.description}")

    # --- 因子 05: 股指期货贴水 ---
    f5 = FactorFuturesBasis()
    r5 = f5.calculate(futures=[
        {"name": "IH", "future_price": 2400.0, "spot_price": 2430.0, "days_to_expiry": 33},
        {"name": "IF", "future_price": 3600.0, "spot_price": 3640.0, "days_to_expiry": 33},
        {"name": "IC", "future_price": 5832.4, "spot_price": 5931.76, "days_to_expiry": 58},
        {"name": "IM", "future_price": 6100.0, "spot_price": 6190.0, "days_to_expiry": 58},
    ])
    print(f"\n[{r5.factor_id}] {r5.factor_name} ({r5.factor_name_en})")
    print(f"  值: {r5.value:.2f}%  信号: {r5.signal.value}")
    print(f"  {r5.description}")
    if r5.extra:
        for k, v in r5.extra.items():
            if k not in ("worst_contract", "worst_basis"):
                print(f"  {k}: {v}%")
        print(f"  最极端合约: {r5.extra.get('worst_contract')} = {r5.extra.get('worst_basis')}%")

    # --- 因子 06: ETF异常波动 ---
    f6 = FactorETFAbnormalFlow()
    r6 = f6.calculate(spy_flow=7.72, ivv_flow=-7.14)
    print(f"\n[{r6.factor_id}] {r6.factor_name} ({r6.factor_name_en})")
    print(f"  值: +${r6.value:.2f}B  信号: {r6.signal.value}")
    print(f"  {r6.description}")
    if r6.extra.get("crowding_pct") is not None:
        print(f"  拥挤度: {r6.extra['crowding_pct']}% (越高=越像内部换手)")

    # --- 综合风险评分 ---
    print("\n" + "=" * 70)
    print("  综合风险评分")
    print("=" * 70)

    composite = CompositeRiskScore()
    result = composite.calculate([r1, r2, r3, r4, r5, r6])

    print(f"\n  评分: {result['score']}/100")
    print(f"  等级: {result['level']}")
    print(f"  异常项: {result['alert_count']}  关注项: {result['watch_count']}")
    if result["gex_negative_bonus"] > 0:
        print(f"  GEX负值额外加分: +{result['gex_negative_bonus']}")
    print(f"\n  {result['summary']}")

    print("\n  各因子明细:")
    for fid, info in result["factor_scores"].items():
        print(f"    [{fid}] {info['name']:12s}  {info['signal']:6s}  "
              f"得分 {info['raw_score']} * 权重 = {info['weighted_score']}")

    # --- JSON输出 ---
    print("\n" + "=" * 70)
    print("  JSON输出 (可直接对接下游系统)")
    print("=" * 70)

    output = {
        "factors": [r.to_dict() for r in [r1, r2, r3, r4, r5, r6]],
        "composite": result,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
