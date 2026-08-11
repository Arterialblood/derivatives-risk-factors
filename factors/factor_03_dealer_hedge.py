"""
因子 03: 做市商对冲占比 (Dealer Hedging Ratio)

含义:
    做市商（Dealer）在期权市场充当对手方——你买Call，他就卖Call给你。
    卖出Call后他持有负Delta敞口（相当于做空），需要买入现货来对冲使
    Delta归零（Delta-Neutral）。这就是"被迫对冲"——不是主动交易，
    而是被期权头寸逼着做的。

    当做市商对冲占比过高（>50%），意味着市场成交中很大一部分不是
    基本面驱动的方向性交易，而是机械化的对冲程序在买卖。这会导致:
      - 价格弹性增大（小幅消息引发大幅波动）
      - 日内出现非理性脉冲
      - 流动性在关键价位突然枯竭

计算公式:
    对冲占比 = 过去1小时内归因于Delta-hedging的成交量 / 同期总成交量

    归因方法: 通过TAQ（逐笔报价）数据，识别大额期权成交后紧跟的
             现货反向交易，按时间窗口匹配后统计。

    注: 该因子需要Level-2逐笔数据或第三方做市商对冲估算数据源。

阈值:
    < 50%  → NORMAL (正常, 方向性交易主导)
    50~75% → WATCH  (关注, 机械对冲主导成交)
    > 75%  → ALERT  (异常, 对冲程序主导, 流动性风险上升)
"""

from typing import Any, Dict

from .base import BaseFactor, RiskLevel


class FactorDealerHedgingRatio(BaseFactor):
    """做市商对冲占比因子"""

    factor_id = "03"
    factor_name = "做市商对冲占比"
    factor_name_en = "Dealer Hedging Ratio"

    thresholds = {
        "normal_max": 0.50,  # <= 50% 正常
        "watch_max": 0.75,   # <= 75% 关注
        # > 75% 异常
    }

    def _compute(self, raw_data: Dict[str, Any]) -> float:
        hedge_volume = raw_data["hedge_volume_1h"]
        total_volume = raw_data["total_volume_1h"]

        if total_volume <= 0:
            raise ValueError("total_volume_1h must be positive")

        return hedge_volume / total_volume

    def _classify(self, value: float) -> RiskLevel:
        if value <= self.thresholds["normal_max"]:
            return RiskLevel.NORMAL
        elif value <= self.thresholds["watch_max"]:
            return RiskLevel.WATCH
        else:
            return RiskLevel.ALERT

    def _describe(self, value: float, signal: RiskLevel) -> str:
        pct = value * 100
        if signal == RiskLevel.NORMAL:
            return (
                f"做市商对冲占比 {pct:.1f}%，方向性交易主导市场。"
                f"成交结构健康，流动性正常。"
            )
        elif signal == RiskLevel.WATCH:
            return (
                f"做市商对冲占比 {pct:.1f}%，机械对冲主导成交。"
                f"小幅消息可能引发放大波动，关注关键价位流动性变化。"
            )
        else:
            return (
                f"做市商对冲占比 {pct:.1f}%，对冲程序主导！"
                f"流动性在关键价位可能突然枯竭，"
                f"日内非理性脉冲风险极高。"
            )
