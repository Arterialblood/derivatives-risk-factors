"""
因子 02: 深度虚值期权暴涨 (CBOE SKEW Index)

含义:
    虚值期权（Out-of-the-Money）是行权价远离当前现价的期权。
    比如标普500在7760点，行权价7200的看跌期权就是"深度虚值 Put"——
    只有市场暴跌7%以上才有价值。买这种期权本质是买"崩盘保险"。

    CBOE SKEW Index 衡量深度虚值 Put 相对于平值期权的价格溢价，
    反映市场对"尾部风险"（极端暴跌事件）的定价。

    关键信号: SKEW偏高但VIX偏低 → "低波动 + 高尾部风险"矛盾组合，
    说明市场整体平静但聪明钱在悄悄买保险。

计算公式:
    SKEW = 100 - 10 * { E[S(T)] - S(0) } / { sigma * sqrt(T) * S(0) }

    简化理解: SKEW ∝ (深度虚值Put的IV - 平值IV)
             IV差值越大 → SKEW越高 → 尾部风险定价越贵

    注: SKEW指数由CBOE官方计算发布，因子直接读取指数值即可。

阈值:
    < 130  → NORMAL (正常, 市场对崩盘风险不担忧)
    130~145 → WATCH  (关注, 尾部风险定价上升)
    > 145  → ALERT  (异常, 极端恐慌信号, 可能预示黑天鹅)
"""

from typing import Any, Dict

from .base import BaseFactor, RiskLevel


class FactorSkewIndex(BaseFactor):
    """深度虚值期权暴涨 (SKEW指数) 因子"""

    factor_id = "02"
    factor_name = "深度虚值期权暴涨"
    factor_name_en = "SKEW Index"

    thresholds = {
        "normal_max": 130.0,  # <= 130 正常
        "watch_max": 145.0,   # <= 145 关注
        # > 145 异常
    }

    def __init__(self):
        self._last_vix: float | None = None

    def _compute(self, raw_data: Dict[str, Any]) -> float:
        skew_value = raw_data["skew_value"]
        self._last_vix = raw_data.get("vix_value")
        return float(skew_value)

    def _classify(self, value: float) -> RiskLevel:
        if value <= self.thresholds["normal_max"]:
            return RiskLevel.NORMAL
        elif value <= self.thresholds["watch_max"]:
            return RiskLevel.WATCH
        else:
            return RiskLevel.ALERT

    def _describe(self, value: float, signal: RiskLevel) -> str:
        vix = self._last_vix  # 可选: 传入VIX做矛盾判断
        if signal == RiskLevel.NORMAL:
            return (
                f"SKEW = {value:.1f}，处于正常区间。"
                f"市场对尾部风险（极端暴跌）定价正常。"
            )
        elif signal == RiskLevel.WATCH:
            base = (
                f"SKEW = {value:.1f}，尾部风险定价上升。"
                f"有人在大量买入深度虚值Put（崩盘保险）。"
            )
            if vix is not None and vix < 18:
                base += (
                    f" 注意：VIX仅{vix:.1f}偏低，"
                    f"构成'低波动+高尾部风险'矛盾组合——"
                    f"表面平静但底层脆弱。"
                )
            return base
        else:
            return (
                f"SKEW = {value:.1f}，极端恐慌信号！"
                f"深度虚值Put被疯狂抢购，可能预示黑天鹅事件。"
                f"建议立即检查持仓尾部风险敞口。"
            )

    def _extract_extra(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        extra = {}
        if self._last_vix is not None:
            extra["vix_value"] = self._last_vix
            extra["low_vol_high_tail"] = self._last_vix < 18
        return extra
