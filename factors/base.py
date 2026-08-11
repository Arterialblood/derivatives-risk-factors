"""
因子基类与数据结构定义。

所有衍生品风险因子继承 BaseFactor，实现 calculate() 方法，
返回 FactorResult 数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RiskLevel(str, Enum):
    """三档风险等级"""

    NORMAL = "NORMAL"  # 绿色 - 正常
    WATCH = "WATCH"    # 黄色 - 关注
    ALERT = "ALERT"    # 红色 - 异常


@dataclass
class FactorResult:
    """单个因子计算结果"""

    factor_id: str               # 因子编号，如 "01"
    factor_name: str             # 因子中文名
    factor_name_en: str          # 因子英文名
    value: float                 # 原始值
    signal: RiskLevel            # 风险等级
    description: str             # 结果描述
    thresholds: Dict[str, float] = field(default_factory=dict)
    # 各档阈值上下界
    extra: Dict[str, Any] = field(default_factory=dict)
    # 附加信息（如分品种明细等）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "factor_name": self.factor_name,
            "factor_name_en": self.factor_name_en,
            "value": self.value,
            "signal": self.signal.value,
            "description": self.description,
            "thresholds": self.thresholds,
            "extra": self.extra,
        }


class BaseFactor:
    """
    因子基类。

    子类需要:
      1. 设置 factor_id, factor_name, factor_name_en
      2. 设置 thresholds (各档阈值)
      3. 实现 _compute(raw_data) -> float
      4. 实现 _classify(value) -> RiskLevel
    """

    factor_id: str = ""
    factor_name: str = ""
    factor_name_en: str = ""

    # 默认阈值，子类覆盖
    thresholds: Dict[str, float] = {}

    def calculate(self, **kwargs) -> FactorResult:
        """
        计算因子值并输出风险信号。

        Returns:
            FactorResult
        """
        value = self._compute(kwargs)
        signal = self._classify(value)
        desc = self._describe(value, signal)
        extra = self._extract_extra(kwargs)

        return FactorResult(
            factor_id=self.factor_id,
            factor_name=self.factor_name,
            factor_name_en=self.factor_name_en,
            value=value,
            signal=signal,
            description=desc,
            thresholds=self.thresholds.copy(),
            extra=extra,
        )

    def _compute(self, raw_data: Dict[str, Any]) -> float:
        """从原始数据计算因子值，子类实现"""
        raise NotImplementedError

    def _classify(self, value: float) -> RiskLevel:
        """根据因子值判定风险档位，子类实现"""
        raise NotImplementedError

    def _describe(self, value: float, signal: RiskLevel) -> str:
        """生成结果描述文本，子类可覆盖"""
        return f"{self.factor_name} = {value:.2f}, signal = {signal.value}"

    def _extract_extra(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取附加信息，子类可覆盖"""
        return {}
