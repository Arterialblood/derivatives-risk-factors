"""
因子 01: 末日轮爆量 (0DTE Options Volume Surge)

含义:
    0DTE（Zero Days to Expiration）期权是当天到期、当天行权的期权。
    交易圈俗称"末日轮"——在期权到期日最后几小时，大量资金涌入买卖
    即将归零的合约，赌最后一段价格波动。

    当末日轮成交量异常放大时，意味着市场投机资金极度活跃。
    这些期权 Gamma 极高（时间价值接近零，Delta 变化剧烈），
    最后的对冲行为会对现货产生脉冲式冲击——收盘前1-2小时
    可能出现非理性的急涨或急跌。

计算公式:
    末日轮倍率 = 当日0DTE期权总成交量 / 过去30个交易日0DTE日均成交量

阈值:
    < 1.5x   → NORMAL (正常)
    1.5~2.5x → WATCH  (关注)
    > 2.5x   → ALERT  (异常)
"""

from typing import Any, Dict

from .base import BaseFactor, RiskLevel


class Factor0DTEVolumeSurge(BaseFactor):
    """末日轮爆量因子"""

    factor_id = "01"
    factor_name = "末日轮爆量"
    factor_name_en = "0DTE Volume Surge"

    thresholds = {
        "normal_max": 1.5,   # <= 1.5x 正常
        "watch_max": 2.5,    # <= 2.5x 关注
        # > 2.5x 异常
    }

    def _compute(self, raw_data: Dict[str, Any]) -> float:
        today_volume = raw_data["today_volume"]
        avg_volume_30d = raw_data["avg_volume_30d"]

        if avg_volume_30d <= 0:
            raise ValueError("avg_volume_30d must be positive")

        return today_volume / avg_volume_30d

    def _classify(self, value: float) -> RiskLevel:
        if value <= self.thresholds["normal_max"]:
            return RiskLevel.NORMAL
        elif value <= self.thresholds["watch_max"]:
            return RiskLevel.WATCH
        else:
            return RiskLevel.ALERT

    def _describe(self, value: float, signal: RiskLevel) -> str:
        ratio = value
        if signal == RiskLevel.NORMAL:
            return (
                f"0DTE成交量为30日均值的 {ratio:.2f}x，处于正常区间。"
                f"末日轮投机资金活跃度未见异常。"
            )
        elif signal == RiskLevel.WATCH:
            return (
                f"0DTE成交量为30日均值的 {ratio:.2f}x，进入关注区间。"
                f"收盘前1-2小时可能出现脉冲式冲击，建议跟踪尾盘波动。"
            )
        else:
            return (
                f"0DTE成交量为30日均值的 {ratio:.2f}x，异常放大！"
                f"高Gamma末日轮对冲可能引发现货非理性急涨/急跌，"
                f"建议收紧尾盘风控。"
            )
