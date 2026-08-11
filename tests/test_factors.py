"""
因子单元测试。

运行: python -m pytest tests/test_factors.py -v
或:   python tests/test_factors.py
"""

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
    RiskLevel,
)


def test_01_0dte_surge():
    f = Factor0DTEVolumeSurge()

    # 正常
    r = f.calculate(today_volume=500_000, avg_volume_30d=550_000)
    assert r.signal == RiskLevel.NORMAL
    assert abs(r.value - 0.909) < 0.01

    # 关注
    r = f.calculate(today_volume=1_200_000, avg_volume_30d=550_000)
    assert r.signal == RiskLevel.WATCH
    assert abs(r.value - 2.182) < 0.01

    # 异常
    r = f.calculate(today_volume=1_500_000, avg_volume_30d=550_000)
    assert r.signal == RiskLevel.ALERT
    assert abs(r.value - 2.727) < 0.01

    print("[PASS] test_01_0dte_surge")


def test_02_skew():
    f = FactorSkewIndex()

    r = f.calculate(skew_value=125.0)
    assert r.signal == RiskLevel.NORMAL

    r = f.calculate(skew_value=141.23, vix_value=14.9)
    assert r.signal == RiskLevel.WATCH
    assert r.extra.get("low_vol_high_tail") == True

    r = f.calculate(skew_value=150.0)
    assert r.signal == RiskLevel.ALERT

    print("[PASS] test_02_skew")


def test_03_dealer_hedge():
    f = FactorDealerHedgingRatio()

    r = f.calculate(hedge_volume_1h=300_000, total_volume_1h=1_000_000)
    assert r.signal == RiskLevel.NORMAL
    assert abs(r.value - 0.30) < 0.001

    r = f.calculate(hedge_volume_1h=680_000, total_volume_1h=1_000_000)
    assert r.signal == RiskLevel.WATCH

    r = f.calculate(hedge_volume_1h=800_000, total_volume_1h=1_000_000)
    assert r.signal == RiskLevel.ALERT

    print("[PASS] test_03_dealer_hedge")


def test_04_gex():
    f = FactorGammaExposure()

    # 正常: 正区间深
    r = f.calculate(gex_value=4.0)
    assert r.signal == RiskLevel.NORMAL

    # 关注: 正区间浅
    r = f.calculate(gex_value=1.0)
    assert r.signal == RiskLevel.WATCH

    # 异常: 负区间
    r = f.calculate(gex_value=-1.5)
    assert r.signal == RiskLevel.ALERT

    print("[PASS] test_04_gex")


def test_05_futures_basis():
    f = FactorFuturesBasis()

    # 直接传入年化基差率
    r = f.calculate(basis_annualized=-4.0)
    assert r.signal == RiskLevel.NORMAL

    r = f.calculate(basis_annualized=-8.0)
    assert r.signal == RiskLevel.WATCH

    r = f.calculate(basis_annualized=-10.66)
    assert r.signal == RiskLevel.ALERT

    # 从分品种数据计算
    r = f.calculate(futures=[
        {"name": "IH", "future_price": 2500.0, "spot_price": 2510.0, "days_to_expiry": 120},
        {"name": "IC", "future_price": 5832.4, "spot_price": 5931.76, "days_to_expiry": 58},
    ])
    assert "IH" in r.extra
    assert "IC" in r.extra
    assert r.extra["worst_contract"] == "IC"

    print("[PASS] test_05_futures_basis")


def test_06_etf_flow():
    f = FactorETFAbnormalFlow()

    # 正常: 合计绝对值小
    r = f.calculate(spy_flow=1.0, ivv_flow=0.5)
    assert r.signal == RiskLevel.NORMAL

    # 关注: 内部换手
    r = f.calculate(spy_flow=7.72, ivv_flow=-7.14)
    assert r.signal == RiskLevel.WATCH
    assert r.extra["crowding_pct"] > 80  # 高拥挤度

    # 异常: 极端
    r = f.calculate(spy_flow=8.0, ivv_flow=5.0)
    assert r.signal == RiskLevel.ALERT

    print("[PASS] test_06_etf_flow")


def test_composite():
    composite = CompositeRiskScore()

    # 全部正常 → LOW
    from factors.base import FactorResult
    results_normal = [
        FactorResult("01", "末日轮", "0DTE", 1.0, RiskLevel.NORMAL, ""),
        FactorResult("02", "SKEW", "SKEW", 125.0, RiskLevel.NORMAL, ""),
        FactorResult("03", "对冲", "Hedge", 0.3, RiskLevel.NORMAL, ""),
        FactorResult("04", "GEX", "GEX", 4.0, RiskLevel.NORMAL, ""),
        FactorResult("05", "贴水", "Basis", -4.0, RiskLevel.NORMAL, ""),
        FactorResult("06", "ETF", "ETF", 1.0, RiskLevel.NORMAL, ""),
    ]
    r = composite.calculate(results_normal)
    assert r["level"] == "LOW"
    assert r["score"] == 0.0

    # 混合信号 → MEDIUM
    results_mixed = [
        FactorResult("01", "末日轮", "0DTE", 2.18, RiskLevel.WATCH, ""),
        FactorResult("02", "SKEW", "SKEW", 141.0, RiskLevel.WATCH, ""),
        FactorResult("03", "对冲", "Hedge", 0.68, RiskLevel.WATCH, ""),
        FactorResult("04", "GEX", "GEX", 3.2, RiskLevel.WATCH, ""),
        FactorResult("05", "贴水", "Basis", -10.66, RiskLevel.ALERT, ""),
        FactorResult("06", "ETF", "ETF", 0.58, RiskLevel.WATCH, ""),
    ]
    r = composite.calculate(results_mixed)
    assert r["level"] == "MEDIUM"
    assert r["alert_count"] == 1
    assert r["watch_count"] == 5

    print("[PASS] test_composite")


if __name__ == "__main__":
    test_01_0dte_surge()
    test_02_skew()
    test_03_dealer_hedge()
    test_04_gex()
    test_05_futures_basis()
    test_06_etf_flow()
    test_composite()
    print("\n✅ All tests passed!")
