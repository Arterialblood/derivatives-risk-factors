"""
因子 05: 股指期货大幅贴水 (Index Futures Basis)

含义:
    期货价格低于现货价格称为"贴水"(Discount)，反之称为"升水"(Premium)。
    A股4大股指期货(IH/IF/IC/IM)长期处于贴水是常态，
    但贴水幅度异常加深则是风险信号。

    IC(中证500)和IM(中证1000)贴水加深 → 中小盘看空情绪升温
    IH(上证50)和IF(沪深300)贴水加深 → 大盘蓝筹看空情绪升温

计算公式:
    年化基差率 = (期货价格 - 现货价格) / 现货价格 * (365 / 距交割日天数) * 100%

    示例: IC主力合约
      期货价 = 5,832.40  现货价 = 5,931.76  距交割 = 58天
      基差率 = (5832.40 - 5931.76) / 5931.76 * (365/58) * 100%
             = -1.674% * 6.293
             = -10.54%

阈值 (年化基差率):
    > -6%   → NORMAL (正常, 贴水来自分红预期和资金成本)
    -6%~-10% → WATCH  (关注, 看空情绪升温)
    < -10%  → ALERT  (异常, 极端看空, 可能预示系统性风险)
"""

from typing import Any, Dict, List

from .base import BaseFactor, RiskLevel


class FactorFuturesBasis(BaseFactor):
    """股指期货贴水因子"""

    factor_id = "05"
    factor_name = "股指期货大幅贴水"
    factor_name_en = "Index Futures Basis"

    thresholds = {
        "normal_min": -6.0,   # > -6% 正常
        "watch_min": -10.0,   # > -10% 关注
        # < -10% 异常
    }

    def _compute(self, raw_data: Dict[str, Any]) -> float:
        """
        两种模式:
        1. 直接传入 basis_annualized (已年化的基差率百分比, 如 -8.4)
        2. 传入 futures 列表, 自动计算年化基差率并取均值
        """
        if "basis_annualized" in raw_data:
            return float(raw_data["basis_annualized"])

        # 模式2: 从分品种数据计算
        futures: List[Dict] = raw_data["futures"]
        if not futures:
            raise ValueError("futures list is empty")

        rates = []
        for f in futures:
            rate = self._calc_single_basis(f)
            rates.append(rate)
            f["basis_annualized"] = rate  # 回写

        return sum(rates) / len(rates)

    @staticmethod
    def _calc_single_basis(f: Dict) -> float:
        """计算单个品种的年化基差率"""
        future_price = f["future_price"]
        spot_price = f["spot_price"]
        days_to_expiry = f["days_to_expiry"]

        if spot_price <= 0 or days_to_expiry <= 0:
            raise ValueError("spot_price and days_to_expiry must be positive")

        raw_basis = (future_price - spot_price) / spot_price
        annualized = raw_basis * (365.0 / days_to_expiry) * 100.0
        return annualized

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
                f"年化基差率 = {value:.2f}%，贴水处于正常区间。"
                f"主要来自分红预期和资金成本，市场情绪中性。"
            )
        elif signal == RiskLevel.WATCH:
            return (
                f"年化基差率 = {value:.2f}%，贴水加深进入关注区间。"
                f"看空情绪升温，现货端抛压增大，"
                f"建议关注中小盘成分股（IC/IM对应标的）。"
            )
        else:
            return (
                f"年化基差率 = {value:.2f}%，贴水异常极端！"
                f"市场看空情绪极度浓厚，可能预示系统性风险事件。"
                f"建议向现货端传递抛压预警，收紧持仓风控。"
            )

    def _extract_extra(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取分品种明细"""
        extra = {}
        if "futures" in raw_data:
            for f in raw_data["futures"]:
                name = f.get("name", "unknown")
                rate = f.get("basis_annualized")
                if rate is None:
                    rate = self._calc_single_basis(f)
                extra[name] = round(rate, 2)

            # 找出最极端的品种
            if extra:
                worst = min(extra, key=lambda k: extra[k])
                extra["worst_contract"] = worst
                extra["worst_basis"] = extra[worst]
        return extra
