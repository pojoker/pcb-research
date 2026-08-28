# 容差与汇率 ADR 证据登记（2026-08-28）

状态：研究草案；不构成 canonical 事实，不批准 ADR，不生成 `approved_tolerance.json`。

## 研究合同

- 目的：为 `docs/adr/0002-capacity-ceiling-tolerance.md` 和 `docs/adr/0003-fx-conversion-policy.md` 提供可复核的一手资料和反例。
- 范围：DP6 的推断值—产能天顶比较、金额的跨币种分析折算；不扩展为财务报表编制意见，也不为 PCB 行业凭空创造统一容差。
- 检索日：2026-08-28（Asia/Shanghai）。
- 证据纪律：官方来源可承重其发布的规则、统计口径或数据存在；不能仅凭官方汇率页面证明任何公司产能、产品族、厂址或供应关系。

## 官方一手资料登记

| source_id | 官方来源 | 核对到的规则/事实 | 可承重范围 | 不能承重 |
|---|---|---|---|---|
| `SRC-SEC-SAB99` | [SEC Staff Accounting Bulletin No. 99](https://www.sec.gov/interps/account/sab99.htm) | SEC 说明单一百分比/数字阈值不能替代对全部相关情况的判断；百分比只能作为分析起点。 | 反对将“±30%”或任何单值当作充分理由；支持保留定性/范围审查。 | 不提供 PCB 产能容差，也不决定本项目 DP6 的数值。 |
| `SRC-NIST-MU` | [NIST Measurement Uncertainty](https://www.nist.gov/itl/sed/topic-areas/measurement-uncertainty) | 不确定度应表达为与测量结果相关的参数，可用标准不确定度或带覆盖概率的区间表示。 | 支持把容差与误差/不确定度来源及覆盖目标绑定，而不是拍脑袋。 | 不证明历史回算误差服从某个分布，也不指定 Q95 或任何 `τ`。 |
| `SRC-BIPM-GUM` | [BIPM/JCGM Guides in Metrology](https://www.bipm.org/en/web/guest/publications/guides) | GUM 系列提供评估、表达、传播测量不确定度的方法框架。 | 支持记录不确定度分量、模型和覆盖因子。 | 产能披露是统计/会计口径，不等同于实验室测量；不能直接移植一个标准百分比。 |
| `SRC-IFRS-IAS21` | [IFRS Foundation IAS 21](https://www.ifrs.org/content/dam/ifrs/publications/pdf-standards/english/2022/issued/part-a/ias-21-the-effects-of-changes-in-foreign-exchange-rates.pdf) | 外币资产负债按报告日 closing rate；收入费用按交易日汇率，若汇率没有显著波动，期间平均可作近似。 | 支持存量/流量分开，支持“交易日优先、条件平均”的候选规则。 | 不决定本项目的目标币种、波动阈值、商业行情源或 DP6 schema。 |
| `SRC-PBOC-CNY` | [中国人民银行人民币汇率中间价公告索引](https://www.pbc.gov.cn/zhengcehuobisi/125207/125217/125925/17105-2.html) | 官方索引提供中国外汇交易中心授权公布的人民币汇率中间价公告入口；具体日值要按期间登记。 | CNY 方向官方来源候选，含报价单位和发布日期。 | 中间价不是公司实际结算价；不能替代公司原始披露或证明某项收入发生。 |
| `SRC-HKMA-FX` | [Hong Kong Monetary Authority exchange-rate datasets](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/) | 官方数据集分列期末、期间平均、日度汇率。 | HKD 的 closing/period-average/daily 来源候选。 | 不自动决定本项目采用哪个序列，也不修复主体/期间错配。 |
| `SRC-CBC-TWD` | [Central Bank of the Republic of China (Taiwan) foreign-exchange information](https://www.cbc.gov.tw/tw/np-297-1.html) | 官方页面提供新台币外汇资讯及新台币对美元银行间成交收盘汇率入口。 | TWD 官方收盘/日度来源候选；必要时可经 USD 交叉。 | 不提供 TWD/CNY 全部期间平均的既成项目字段，不能静默补齐。 |
| `SRC-BOJ-JPY` | [Bank of Japan daily FX rates](https://www.boj.or.jp/en/statistics/market/forex/fxdaily/fxlist/) | 日本银行发布每日外汇市况，并提供长期时序数据入口。 | JPY 日度/期末来源候选。 | 页面不自动给出本项目所需的期间加权平均；平均仍需记录计算方法。 |
| `SRC-ECB-EUR` | [European Central Bank euro reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) | ECB 工作日发布欧元参考汇率和时序下载，并注明参考汇率用于信息目的、不宜直接当交易执行价。 | EUR pivot 与欧元交叉的官方来源候选。 | 不证明实际成交价，不授权将 EUR 视为所有币种的唯一 pivot。 |

## 容差结论

1. 项目现有 DP6 已把“同口径、强天顶、只允许 `pass` 发布、不可比为 `indeterminate`”写成机械边界；容差 ADR 只应补足比较上限的标量来源和生效范围。
2. 没有检索到官方 PCB 行业资料规定一个适用于不同公司、不同厂址、不同产品族和不同期间的统一产能容差。因而 `±30%` 没有证据基础，固定 10% 也不能从测试 fixture 推导。
3. 可审计候选是 scope 级回算误差公式；在没有实际值/推断值配对、样本不足或口径发生变化时，公式应返回未知，DP6 保持 `indeterminate`。
4. 容差是上侧“超天顶”保护带，不应写成对称区间，也不应吸收来源不一致、主体错配、产品混格、委外归属或汇率波动。

## 汇率结论

1. IAS 21 的结构与项目需求一致：存量和流量分别处理；存量使用期末汇率，流量以交易日为优先，期间平均只在近似交易日汇率且没有显著波动时作为实务简化。
2. PBOC、HKMA、CBC、BOJ、ECB 都提供官方汇率或数据入口，但产品字段不同：不能把某一来源的“closing”“daily”“period average”标签跨源混用。
3. CNY 目标视图可以作为项目候选，但必须由用户裁决；原币金额、报价方向、日期、来源和折算公式必须保留。
4. FX 不适用于平方米、片数、产能或销量；它只影响金额派生值。官方源不可达、直接报价缺失、序列不完整或波动检查失败时应为 `indeterminate`。
5. 当前 DP6/tolerance schema 的货币枚举不含 `KRW`，虽不变量清单提到 KRW；KRW 只能作为待扩枚举的开放问题，不能在本 ADR 中静默加入。

## 人闸问题清单（精确输入）

### TOL-1 至 TOL-5

- `TOL-1 scope`：首个 `subject_id / plant_id / product_family / fab_cell / metric_type / unit / period_type / period / currency / consolidation_basis` 是什么？
- `TOL-2 scalar`：选固定比例、来源分档还是 scope 级校准？若不是 C，逐一给出 `tolerance`；若是 C，给出 `τ_round`、`τ_cap`、Q 分位数、窗口和最小样本数。
- `TOL-3 ceiling`：产销量表/建成产能自述是否是唯一强天顶；批复产能是否一律 `indeterminate`？
- `TOL-4 zero`：是否允许显式 `τ=0`，以及只对哪些直接披露 scope？
- `TOL-5 reopen`：哪些新证据会让旧 ADR 失效并重开？

### FX-1 至 FX-6

- `FX-1 target`：目标币种是否 `CNY`，是否同时需要 `USD`；是否强制保留原币？
- `FX-2 flow`：批准“交易日/金额加权优先，条件期间平均备选”吗？显著波动的精确阈值是什么？
- `FX-3 close-day`：期末非营业日按期末前最后一个官方报价日，还是另定规则？
- `FX-4 source`：是否按 PBOC/HKMA/CBC/BOJ/ECB 的币种层级使用官方源；源不可用时是 pivot 还是 `indeterminate`？
- `FX-5 reported-rate`：是否允许年报明确披露的折算率仅用于复现原披露；与官方序列冲突时谁优先？
- `FX-6 precision`：汇率精度、金额精度、舍入和修订重算规则是什么？

## 本轮不得做的实例化动作

- 不把上述任何候选规则写入 DP6 fixture，不把 `0.1` 解释为真实批准值。
- 不修改 `tolerance-adr.schema.json`、DP6 代码、points/edges、产能账本或其他文件。
- 不把本研究登记中的官方来源候选升级成 T1 承重资格或 canonical 事实；那属于另一个人闸。
