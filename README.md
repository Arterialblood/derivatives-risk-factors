# Derivatives Risk Monitoring Factors

6 个衍生品/期权市场风险监控量化因子，来源于实盘衍生品风险看板的指标体系。

## 因子列表

| 编号 | 因子名称 | 类名 | 信号含义 |
|------|---------|------|---------|
| 01 | 末日轮爆量 (0DTE Volume Surge) | `Factor0DTEVolumeSurge` | 0DTE期权成交量相对30日均值的倍数，反映投机资金极端活跃度 |
| 02 | 深度虚值期权暴涨 (SKEW Index) | `FactorSkewIndex` | CBOE SKEW指数，衡量深度虚值Put的尾部风险定价 |
| 03 | 做市商对冲占比 (Dealer Hedging Ratio) | `FactorDealerHedgingRatio` | 1小时内做市商Delta对冲交易占总成交比重，反映机械对冲主导程度 |
| 04 | Gamma挤压 (Gamma Exposure) | `FactorGammaExposure` | SPX GEX，衡量做市商整体对冲压力方向（正=抑制波动，负=放大波动） |
| 05 | 股指期货贴水 (Index Futures Basis) | `FactorFuturesBasis` | A股4大期指年化基差率，贴水加深=看空情绪升温 |
| 06 | ETF异常波动 (ETF Abnormal Flow) | `FactorETFAbnormalFlow` | 同标的ETF净流入合计，判断增量资金入场vs内部换手拥挤 |

## 风险档位

每个因子输出三档信号：

| 档位 | 颜色 | 含义 |
|------|------|------|
| `NORMAL` | 绿色 | 正常区间，无需关注 |
| `WATCH` | 黄色 | 关注区间，建议跟踪 |
| `ALERT` | 红色 | 异常区间，建议响应 |

## 快速开始

```bash
pip install numpy pandas

# 运行示例
python examples/run_all_factors.py
```

```python
from factors import (
    Factor0DTEVolumeSurge,
    FactorSkewIndex,
    FactorDealerHedgingRatio,
    FactorGammaExposure,
    FactorFuturesBasis,
    FactorETFAbnormalFlow,
    CompositeRiskScore,
)

# 末日轮爆量
f1 = Factor0DTEVolumeSurge()
result = f1.calculate(today_volume=1_200_000, avg_volume_30d=550_000)
print(result.signal)   # WATCH
print(result.value)     # 2.18
```

## 项目结构

```
derivatives-risk-factors/
├── README.md
├── requirements.txt
├── factors/
│   ├── __init__.py
│   ├── base.py                    # 因子基类 + 数据结构
│   ├── factor_01_0dte_surge.py    # 末日轮爆量
│   ├── factor_02_skew_index.py    # 深度虚值期权暴涨 (SKEW)
│   ├── factor_03_dealer_hedge.py  # 做市商对冲占比
│   ├── factor_04_gex_gamma.py     # Gamma挤压 (GEX)
│   ├── factor_05_futures_basis.py # 股指期货贴水
│   ├── factor_06_etf_flow.py      # ETF异常波动
│   └── composite_risk.py          # 综合风险评分
├── examples/
│   └── run_all_factors.py
└── tests/
    └── test_factors.py
```

## 因子联动逻辑

6个因子形成一条从期权市场到期现市场的风险传导链：

```
② SKEW偏高（聪明钱买崩盘保险）
       ↓
① 末日轮爆量 + ③ 对冲占比高（脉冲压力 + 机械对冲主导）
       ↓
④ GEX收窄/转负（减震器变弱 → 波动放大）
       ↓
⑤ 期货贴水加深（跨市场抛压传导）
       ↓
⑥ ETF内部换手（资金面验证：无增量支撑）
```

## License

MIT
