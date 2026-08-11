"""
因子 04: Gamma挤压 (Gamma Exposure / GEX)

含义:
    Delta 衡量"价格涨$1时期权价格变多少"，
    Gamma 衡量"价格涨$1时Delta变多少"——即 Delta 的变化率。
    Gamma 越大，做市商需要调整的对冲量就越大。

    GEX (Gamma Exposure) = 所有期权持仓的 Gamma 加总，
    衡量整个市场做市商群体的对冲压力方向。

核心机制:
    正 Gamma (GEX > 0): 做市商在涨时卖出、跌时买入 → 抑制波动（减震器）
    负 Gamma (GEX < 0): 做市商在涨时买入、跌时卖出 → 放大波动（加速器）

    GEX从正值收窄趋向零 → 减震器变弱
    GEX跌破零线 → 市场从"自我稳定"切换为"自我强化"

计算公式:
    GEX = Sigma [ Gamma_i * OI_i * 100 * Spot^2 * 0.01 * sign_i ]

    其中:
      Gamma_i = 第i个期权合约的Gamma值 (Black-Scholes模型计算)
      OI_i    = 该合约的未平仓量 (Open Interest)
      100     = 每张期权合约对应100股
      Spot    = 标的现价
      0.01    = 代表1%价格变动
      sign_i  = Call的做市商敞口为+1, Put为-1

    注: GEX可从 SpotGamma、Tier1 Alpha 等数据源获取，
       也可用期权链OI + Black-Scholes Gamma自行计算。

阈值 (以SPX GEX, 单位十亿美元):
    > +$2B  → NORMAL (正区间深, 波动被抑制)
    $0~+$2B → WATCH  (正区间浅, 减震器变弱)
    < $0    → ALERT  (负区间, 波动将被放大)
"""

from typing import Any, Dict, List

from .base import BaseFactor, RiskLevel


class FactorGammaExposure(BaseFactor):
    """Gamma挤压 (GEX) 因子"""

    factor_id = "04"
    factor_name = "Gamma挤压"
    factor_name_en = "Gamma Exposure (GEX)"

    thresholds = {
        "normal_min": 2.0,   # > +$2B 正常 (单位: 十亿美元)
        "watch_min": 0.0,    # > $0 关注
        # < $0 异常
    }

    def _compute(self, raw_data: Dict[str, Any]) -> float:
        """
        两种模式:
        1. 直接传入 gex_value (十亿美元)
        2. 传入期权链数据自行计算
        """
        if "gex_value" in raw_data:
            return float(raw_data["gex_value"])

        # 模式2: 从期权链计算
        return self._compute_from_chain(raw_data)

    def _compute_from_chain(self, raw_data: Dict[str, Any]) -> float:
        """
        从期权链数据计算GEX。

        需要:
          - spot: 标的现价
          - options: 期权链列表, 每项含 gamma, open_interest, option_type ('call'/'put')
        """
        import math

        spot = raw_data["spot"]
        options: List[Dict] = raw_data["options"]

        total_gex = 0.0
        for opt in options:
            gamma = opt["gamma"]
            oi = opt["open_interest"]
            sign = 1.0 if opt["option_type"] == "call" else -1.0
            # GEX = Gamma * OI * 100 * Spot^2 * 0.01 * sign
            gex_i = gamma * oi * 100 * (spot ** 2) * 0.01 * sign
            total_gex += gex_i

        # 转换为十亿美元
        return total_gex / 1e9

    def _classify(self, value: float) -> RiskLevel:
        if value > self.thresholds["normal_min"]:
            return RiskLevel.NORMAL
        elif value > self.thresholds["watch_min"]:
            return RiskLevel.WATCH
        else:
            return RiskLevel.ALERT

    def _describe(self, value: float, signal: RiskLevel) -> str:
        if signal == RiskLevel.NORMAL:
            return (
                f"GEX = +${value:.1f}B，正区间较深。"
                f"做市商在涨时卖出、跌时买入，波动被抑制（减震器有效）。"
            )
        elif signal == RiskLevel.WATCH:
            return (
                f"GEX = +${value:.1f}B，正区间但已收窄。"
                f"减震器变弱——若跌破零线，市场将从'自我稳定'"
                f"切换为'自我强化'，任何方向的波动都会被放大。"
            )
        else:
            return (
                f"GEX = ${value:.1f}B，已进入负区间！"
                f"做市商在涨时买入、跌时卖出，波动将被加速放大。"
                f"与末日轮爆量(①)和对冲占比(③)形成共振，"
                f"尾部风险急剧上升。"
            )
