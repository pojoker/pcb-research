---
status: proposed
---

# 金额跨币种折算规则

本 ADR 只提出供人闸选择的分析折算政策，不批准任何汇率表或目标币种。它用于在保留原币事实的前提下，给跨主体/跨地区的金额指标提供可复算的显示或比较值；它不改变公司原始披露，也不把物理数量转换成金额。

## 适用范围与不变式

- 原始值、原币种、原始披露期间、合并口径和来源锚永远保留；折算值是派生字段。
- 只有金额指标可折算：收入、成本、费用、货币性资产/负债、资本开支金额等。平方米、片/块、产能、产量和销量禁止做 FX 折算。
- `flow` 指期间发生并在损益或期间统计中累计的金额；`stock` 指报告日余额或期末状态金额。不能用流量汇率去换存量，不能用期末汇率去替代整个期间流量。
- 跨币种比较前，主体、厂址/地理范围、产品族、FAB、指标、期间、合并口径先满足项目既有同口径要求；FX 不能修复 scope 不一致。

## 候选规则

### 1. 存量：期末汇率

对报告日的货币性存量使用报告期末的官方 closing/reference rate：

```text
converted_stock(target) = stock(source) × R_close(source → target, period_end)
```

若期末不是有官方报价的营业日，必须记录明确的日历滚动规则（推荐使用期末前最后一个可用官方报价日），不能静默取抓取日或下一期数据。固定资产的物理产能数量不属于 stock 金额，不做此折算；固定资产账面金额/资本金余额才属于金额 stock。

### 2. 流量：交易日优先，条件平均为备选

如果交易日期和金额可得，优先用交易日汇率并按金额加权：

```text
R_flow = Σ(amount_i × R_i) / Σ(amount_i)
converted_flow = flow(source) × R_flow
```

若只有期间汇总，且官方日度汇率在该期间没有达到人闸定义的“显著波动”，可使用官方日度报价的期间平均或官方发布的期间平均：

```text
R_avg = mean({R_d | d 为期间内官方可用报价日})
converted_flow = flow(source) × R_avg
```

如果显著波动、期间内币种制度/报价源改变、交易日分布明显偏斜且无法金额加权，或缺少完整汇率序列，则结果为 `indeterminate`，不得套用平均值。

### 3. 报价方向与交叉汇率

规范化保存 `R = target_currency per 1 source_currency`。若官方资料以反向报价发布，使用可审计的倒数；若没有 source→target 直接报价，允许经项目批准的共同 pivot（推荐 CNY 或 EUR）交叉：

```text
R(source → target) = R(source → pivot) × R(pivot → target)
```

每一段必须记录官方来源、报价日/期间、方向、单位、是否倒数、pivot、精度和舍入。汇率四舍五入不得先于最终乘法；原始金额和未舍入汇率保留。

## 选项与推荐

| 选项 | 规则 | 优点 | 反例/代价 |
|---|---|---|---|
| A. 单一期间平均 | 所有金额都用期间平均 | 易实现 | 把期末现金/负债换错；在波动期违反存量/流量区分 |
| B. 存量期末 + 流量期间平均（推荐基线） | stock 用 `R_close`；flow 在无显著波动且序列完整时用 `R_avg` | 与 IAS 21 的存量/流量结构一致，适合财报期间汇总 | “显著波动”阈值仍需项目人闸；平均值不等于每笔交易日真实汇率 |
| C. 交易日逐笔/金额加权 | 能取交易日期时用 `R_i`，只能取期间总额时拒绝折算 | 最接近交易发生时点，波动期最稳健 | 需要更多数据；对公开资料经常导致 `indeterminate` |

推荐 B+C 的组合：C 是有交易日时的首选，B 仅是序列完整且通过波动检查时的期间汇总备选。没有通过波动检查的流量不降级为平均，保留 `indeterminate`。

## 官方来源候选与层级

- CNY 报价：人民银行的人民币汇率中间价公告索引展示中国外汇交易中心授权公布的人民币汇率中间价，具体日值仍需按期间登记。[PBOC 人民币汇率中间价公告索引](https://www.pbc.gov.cn/zhengcehuobisi/125207/125217/125925/17105-2.html)
- HKD：香港金管局官方数据集明确分列 end-of-period、period-average 和 daily figures。[HKMA Exchange rates and interest rates](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/)
- TWD：台湾中央银行提供新台币对美元银行间成交收盘汇率等官方外汇资料。[中央銀行外匯資訊](https://www.cbc.gov.tw/tw/np-297-1.html)
- JPY：日本银行发布每日外汇市况，并提供时序数据入口。[Bank of Japan daily FX rates](https://www.boj.or.jp/en/statistics/market/forex/fxdaily/fxlist/)
- EUR 及欧元交叉：欧洲央行工作日发布欧元外汇参考汇率和时序下载；其页面明确称参考汇率用于信息目的，不应直接当作交易执行价。[ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
- 当前 DP6/tolerance schema 的货币枚举没有 `KRW`，虽然不变量清单提到 KRW；因此涉及 KRW 的记录在单独枚举 ADR 获批前必须保持阻断/`indeterminate`，不能在本 ADR 中偷偷扩枚举。
- 方法依据：IAS 21 对外币折算区分报告日 closing rate 与交易日汇率，并说明期间平均只有在近似交易日汇率且汇率未显著波动时才可作为实务简化。[IFRS Foundation IAS 21](https://www.ifrs.org/content/dam/ifrs/publications/pdf-standards/english/2022/issued/part-a/ias-21-the-effects-of-changes-in-foreign-exchange-rates.pdf)

这些来源是官方来源候选，不代表项目已选定唯一供应源。源不可达、版本改变、直接报价缺失或序列不完整时必须登记并转 `indeterminate`，不能以商业行情站静默替代。

## 不适用与反例

- 不为物理产量、产能面积、片数、层数或任何非金额单位做 FX 折算；`m²` 不能因公司使用 TWD 就换成 CNY。
- 不用年末汇率把全年收入、全年产量或期间平均收入替换掉；不把平均汇率用于期末现金、应收、债务或资产负债表余额。
- 不把公司披露中的“美元收入占比”当作美元金额，不把集团合并收入分摊到大陆厂址后再折算。
- 不用汇率政策吸收主体错配、母子双计、FAB1/FAB2 混加、PCBA/裸板混加、委外归属或 8534 口径不一致。
- 不使用未经登记的商业报价、抓取时点汇率或研究报告中的“约合”数字作为 T1 锚；若只能得到这些线索，保留为发现/待核。

## 对 DP6 和数据模型的影响

当前 DP6 只在比较键币种一致时比较；本 ADR 获批后，任何需要 FX 的桥接必须先生成可审计派生字段，再将比较两侧统一到同一目标币种，并保留原币。折算参数至少需要：`source_currency`、`target_currency`、`rate`、`rate_unit`、`rate_date/period`、`rate_type`（transaction/closing/period_average）、`source_id`、`quote_direction`、`pivot`、`rounding_rule`、`volatility_check` 和 `formula`。这些字段未落地前，不应声称 FX 已实例化。

## 必须由用户回答的精确人闸问题

1. 目标展示/比较币种是否确定为 `CNY`？是否要求同时提供 `USD` 视图；原币是否强制保留（推荐“强制保留”）？
2. 是否批准“C 交易日优先 + B 条件期间平均”的组合？如果只允许期间汇总，显著波动的具体判定阈值是什么（例如基于日度汇率相对平均值的最大偏离，需给出精确百分比/统计量）？
3. 期末非营业日采用“期末前最后一个官方报价日”还是其他规则？缺失日是否允许向后滚动？
4. 首选官方源顺序是否为：PBOC/CNY、HKMA/HKD、CBC/TWD、BOJ/JPY、ECB/EUR；各源不可用时是否允许经 CNY 或 EUR pivot 交叉，还是直接 `indeterminate`？
5. 是否允许使用公司经审计年报明确披露的折算率作为“原始披露复现”而非跨公司统一比较率？若允许，如何与官方日度序列冲突时裁决？
6. 目标币种派生值的精度、最终舍入位数和汇率修订/重算触发条件是什么？
