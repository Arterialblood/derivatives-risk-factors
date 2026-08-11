"""
综合风险评分 (Composite Risk Score)

将6个衍生品风险因子的信号聚合为一个0-100的综合风险评分。

评分逻辑:
    1. 每个因子按信号等级赋分:
       NORMAL → 0分
       WATCH  → 1分
       ALERT  → 2分

    2. 6个因子满分12分，映射到0-100:
       综合评分 = (总得分 / 12) * 100

    3. 特殊加权: ④GEX为负（波动放大器开启）时，额外+15分上限封100

    4. 综合评级:
       0-40   → LOW (低风险)
       40-70  → MEDIUM (中等风险·关注级)
       70-100 → HIGH (高风险·响应级)
"""

from typing import List

from .base import FactorResult, RiskLevel


SIGNAL_SCORES = {
    RiskLevel.NORMAL: 0,
    RiskLevel.WATCH: 1,
    RiskLevel.ALERT: 2,
}


class CompositeRiskScore:
    """综合风险评分器"""

    # 因子权重（默认等权，可自定义）
    DEFAULT_WEIGHTS = {
        "01": 1.0,  # 末日轮爆量
        "02": 1.0,  # SKEW
        "03": 1.0,  # 做市商对冲
        "04": 1.5,  # GEX (加权1.5, 因为核心)
        "05": 1.0,  # 期货贴水
        "06": 1.0,  # ETF异常
    }

    def __init__(self, weights: dict | None = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

    def calculate(self, results: List[FactorResult]) -> dict:
        """
        计算综合风险评分。

        Args:
            results: 6个因子的FactorResult列表

        Returns:
            {
                "score": float,          # 0-100
                "level": str,            # LOW / MEDIUM / HIGH
                "weighted_score": float,  # 加权原始分
                "max_score": float,       # 加权满分
                "factor_scores": dict,    # 各因子得分明细
                "gex_negative_bonus": float,  # GEX负值额外加分
                "summary": str,           # 文字摘要
            }
        """
        total_weighted = 0.0
        max_weighted = 0.0
        factor_scores = {}
        gex_negative = False

        for r in results:
            weight = self.weights.get(r.factor_id, 1.0)
            score = SIGNAL_SCORES[r.signal]
            weighted = score * weight

            total_weighted += weighted
            max_weighted += 2.0 * weight  # ALERT=2是满分

            factor_scores[r.factor_id] = {
                "name": r.factor_name,
                "signal": r.signal.value,
                "raw_score": score,
                "weighted_score": weighted,
            }

            # 检测GEX是否为负
            if r.factor_id == "04" and r.value < 0:
                gex_negative = True

        # 基础评分
        base_score = (total_weighted / max_weighted) * 100 if max_weighted > 0 else 0

        # GEX负值额外加分
        gex_bonus = 15.0 if gex_negative else 0.0
        final_score = min(base_score + gex_bonus, 100.0)

        # 评级
        if final_score < 40:
            level = "LOW"
        elif final_score < 70:
            level = "MEDIUM"
        else:
            level = "HIGH"

        # 摘要
        alert_count = sum(
            1 for r in results if r.signal == RiskLevel.ALERT
        )
        watch_count = sum(
            1 for r in results if r.signal == RiskLevel.WATCH
        )
        summary = self._build_summary(
            final_score, level, alert_count, watch_count, gex_negative
        )

        return {
            "score": round(final_score, 1),
            "level": level,
            "weighted_score": round(total_weighted, 2),
            "max_score": round(max_weighted, 2),
            "factor_scores": factor_scores,
            "gex_negative_bonus": gex_bonus,
            "alert_count": alert_count,
            "watch_count": watch_count,
            "summary": summary,
        }

    @staticmethod
    def _build_summary(
        score: float,
        level: str,
        alert_count: int,
        watch_count: int,
        gex_negative: bool,
    ) -> str:
        parts = [f"综合风险评分 {score:.0f}/100 ({level})"]

        detail_parts = []
        if alert_count > 0:
            detail_parts.append(f"{alert_count}项异常")
        if watch_count > 0:
            detail_parts.append(f"{watch_count}项关注")
        if gex_negative:
            detail_parts.append("GEX转负(波动放大器开启)")

        if detail_parts:
            parts.append("·".join(detail_parts))

        if level == "LOW":
            parts.append("市场衍生品结构稳定，可正常操作。")
        elif level == "MEDIUM":
            parts.append("表面平静但底层脆弱，建议控制仓位并加强盘中跟踪。")
        else:
            parts.append("衍生品风险信号密集，建议收紧风控、降低敞口。")

        return "，".join(parts)
