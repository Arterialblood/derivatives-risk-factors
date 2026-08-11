"""
derivatives-risk-factors
========================
6个衍生品/期权市场风险监控量化因子。

Usage:
    from factors import (
        Factor0DTEVolumeSurge,
        FactorSkewIndex,
        FactorDealerHedgingRatio,
        FactorGammaExposure,
        FactorFuturesBasis,
        FactorETFAbnormalFlow,
        CompositeRiskScore,
    )
"""

from .base import BaseFactor, FactorResult, RiskLevel
from .factor_01_0dte_surge import Factor0DTEVolumeSurge
from .factor_02_skew_index import FactorSkewIndex
from .factor_03_dealer_hedge import FactorDealerHedgingRatio
from .factor_04_gex_gamma import FactorGammaExposure
from .factor_05_futures_basis import FactorFuturesBasis
from .factor_06_etf_flow import FactorETFAbnormalFlow
from .composite_risk import CompositeRiskScore

__all__ = [
    "BaseFactor",
    "FactorResult",
    "RiskLevel",
    "Factor0DTEVolumeSurge",
    "FactorSkewIndex",
    "FactorDealerHedgingRatio",
    "FactorGammaExposure",
    "FactorFuturesBasis",
    "FactorETFAbnormalFlow",
    "CompositeRiskScore",
]

__version__ = "1.0.0"
