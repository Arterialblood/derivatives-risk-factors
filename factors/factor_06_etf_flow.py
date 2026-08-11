"""
因子 06: ETF异常波动 (ETF Abnormal Flow)

含义:
    ETF通过"创设/赎回"(Creation/Redemption)机制运作。
    净流入 = 创设份额 - 赎回份额，以美元计价。
    大额净流入意味着新资金涌入，大额净流出意味着资金撤离。

    关键洞察: 同一标的（如标普500）有多只ETF（SPY、IVV、VOO等）。
    如果SPY大额流入但IVV大额流出，合计净流入很小，
    说明不是新资金在进场，而是同一批资金在换产品——
    呈现"高位拥挤"而非"增量入场"的特征。

计算公式:
    ETF净流入 = (创设份额 - 赎回份额) * NAV

    异常判断:
    |SPY净流入 + IVV净流入| <= $2B  → NORMAL (正常, 增量资金入场或离场)
    |SPY净流入 + IVV净流入| > $2B 但单方向 < $10B → WATCH (内部换手拥挤)
    |SPY净流入 + IVV净流入| > $10B → ALERT (极端, 可能触发日内停牌观察)

    拥挤度指标 = 1 - |合计净流入| / (|SPY流入| + |IVV流入|)
    拥挤度 → 1: 纯内部换手（无增量资金）
    拥挤度 → 0: 纯增量入场/离场
"""

from typing import Any, Dict

from .base import BaseFactor, RiskLevel


class FactorETFAbnormalFlow(BaseFactor):
    """ETF异常波动因子"""

    factor_id = "06"
    factor_name = "ETF异常波动"
    factor_name_en = "ETF Abnormal Flow"

    thresholds = {
        "normal_max_abs": 2.0,   # |合计| <= $2B 正常 (单位: 十亿美元)
        "alert_max_abs": 10.0,   # |合计| > $10B 异常
        "crowding_watch": 0.80,  # 拥挤度 > 80% 至少关注
        # $2B < |合计| <= $10B 关注
    }

    def _compute(self, raw_data: Dict[str, Any]) -> float:
        """
        输入:
          spy_flow: SPY周净流入 (十亿美元, 正=流入, 负=流出)
          ivv_flow: IVV周净流入 (十亿美元)

        返回:
          合计净流入 (十亿美元)
        """
        spy_flow = raw_data["spy_flow"]
        ivv_flow = raw_data["ivv_flow"]

        # 保存原始数据用于分类
        self._spy_flow = spy_flow
        self._ivv_flow = ivv_flow

        return spy_flow + ivv_flow

    def _classify(self, value: float) -> RiskLevel:
        abs_val = abs(value)

        # 先检查极端值
        if abs_val > self.thresholds["alert_max_abs"]:
            return RiskLevel.ALERT

        # 检查拥挤度: 即使合计净流入小, 如果单只ETF波动大也需关注
        total_abs = abs(self._spy_flow) + abs(self._ivv_flow)
        if total_abs > 0:
            crowding = 1.0 - abs_val / total_abs
        else:
            crowding = 0.0

        if abs_val > self.thresholds["normal_max_abs"]:
            return RiskLevel.WATCH
        elif crowding > self.thresholds["crowding_watch"]:
            return RiskLevel.WATCH
        else:
            return RiskLevel.NORMAL

    def _describe(self, value: float, signal: RiskLevel) -> str:
        if signal == RiskLevel.NORMAL:
            return (
                f"SPY+IVV合计净流入 = +${value:.2f}B，处于正常区间。"
                f"增量资金正常入场/离场，无拥挤交易特征。"
            )
        elif signal == RiskLevel.WATCH:
            return (
                f"SPY+IVV合计净流入 = +${value:.2f}B，绝对值偏小但"
                f"单只ETF波动大，呈现'内部换手'拥挤特征——"
                f"非增量资金入场，同一批资金在换产品。"
            )
        else:
            return (
                f"SPY+IVV合计净流入 = +${value:.2f}B，极端波动！"
                f"可能触发日内停牌观察，建议立即检查"
                f"ETF创设/赎回明细和做市商流动性提供情况。"
            )

    def _extract_extra(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算拥挤度指标"""
        extra = {}
        spy_flow = raw_data["spy_flow"]
        ivv_flow = raw_data["ivv_flow"]
        total_abs = abs(spy_flow) + abs(ivv_flow)

        if total_abs > 0:
            crowding = 1.0 - abs(spy_flow + ivv_flow) / total_abs
            extra["spy_flow"] = spy_flow
            extra["ivv_flow"] = ivv_flow
            extra["crowding_ratio"] = round(crowding, 4)
            extra["crowding_pct"] = round(crowding * 100, 1)
        return extra
