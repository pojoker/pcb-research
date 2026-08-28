---
status: proposed
---

# 产能天顶比较的容差规则

本 ADR 只提出供人闸选择的容差规则，不批准任何真实项目值。DP6 的职责是把推断产量与同口径的可比产能天顶作单边比较；容差不能用来修补主体、厂址、产品族、FAB、期间、指标、单位、币种或合并口径不一致。

## 适用范围

仅适用于 `kind=quantitative_inference` 的基准推断行，并且必须同时满足：

- 比较键完全一致：`subject_id`、`plant_id`、`product_family`、`fab_cell`、`period`、`period_type`、`metric_type`、`unit`、`currency`、`consolidation_basis`；任一不一致均为 `indeterminate`，不是“套容差”。
- 天顶锚为人工核验的产销量表或建成产能自述。环评/规划/批复产能是弱上界，单独使用只能保持 `indeterminate`；海关 8534 不能成为公司或厂址级天顶。
- 估计值与天顶已经在同一物理口径。FAB1 与 FAB2、裸板与 PCBA、不同 `product_family`、不同 `physical_flow_id` 不合并。
- 容差值是非负比例 `τ`，是上侧保护带，不是对称的“±τ”。

## 候选判定公式

令 `I` 为推断值，`C` 为同口径、人工核验的产能天顶，`τ_scope` 为本 ADR 对精确 scope 生成的标量：

```text
limit = C × (1 + τ_scope)
I > limit  => fail
I ≤ limit  => pass
```

若比较键、天顶锚、推导链、容差 ADR 的状态/生效期或口径元数据不完整，结果为 `indeterminate`。`τ_scope=0` 只有在人闸明确批准后才合法；它不是缺省值。

### 选项

| 选项 | 规则 | 优点 | 反例/代价 |
|---|---|---|---|
| A. 固定比例 | 对所有 scope 使用一个固定 `τ`，例如 0.10 仅作为待投票候选 | 实现简单、容易解释 | 把不同来源、产品族和估计误差混成一个数字；项目没有证据支持普适 10%；fixture 的 0.1 只是测试值 |
| B. 来源分档 | 按产销量表、建成产能自述等锚类型分别给固定 `τ_source` | 能表达来源强弱 | 仍是人为分档；同一锚类型下的混合业务、单位和期间差异可能被掩盖 |
| C. scope 级校准（推荐） | 用同一 scope 的历史回算误差估计，并设置人工批准的上限：`τ_scope = min(τ_cap, max(τ_round, Q95({|A_i-I_i| / max(|A_i|, q_i)|})))` | 把容差绑定到真实公司/厂址/产品族/期间和已回算误差；可随新财报校准 | 初始没有足够 `A_i/I_i` 时不能计算，必须保持 `indeterminate`；需要明确样本窗口、最小样本数、分位数定义与上限 |

其中：`A_i` 是后续同口径实际值，`I_i` 是当时的推断值，`q_i` 是该单位的最小报告分辨率，`τ_round` 是只覆盖舍入/报告分辨率的人工批准项，`τ_cap` 是风险上限。Q95 不是官方 PCB 规则，只是把不确定度证据物化为一个可审计标量的候选公式；若样本不足或 scope 发生变化，不能借用别的公司或别的 FAB 的分位数。

推荐采用 C 作为规则形状，但不推荐在没有校准样本时填入任意数字。若人闸选择 A 或 B，仍必须把适用的精确 scope 写入 `tolerance-adr.schema.json` 对应实例；不得把它写成全局默认。

## 明确不适用的情形

- 不适用于直接披露的产量、销量、收入、批复产能或建成产能本身；这些事实仍按原口径保存。
- 不适用于把收入除以单价得到的结果之外的任何隐含估计；缺收入锚、单价锚或推导式仍为硬失败/待判，不由容差掩盖。
- 不适用于汇率差异、期间错配、混合主体、母子双计、委外产能归属、PCBA/EMS 收入或 CCL/M3 双计。
- 不适用于 `approval_capacity` 作为可发布天顶，也不适用于把容差写成面积或片数的绝对加减额。

## 证据依据与限制

SEC Staff Accounting Bulletin No. 99 明确指出，不能把单一百分比阈值作为充分的重大性判断；百分比最多是分析起点，仍须考虑全部相关情况。[SEC SAB 99](https://www.sec.gov/interps/account/sab99.htm) 这是对“不能笼统 ±30%”的反例约束，不是 PCB 产能容差的直接授权。

NIST 对测量不确定度的说明支持把不确定度作为带覆盖概率的区间，并强调需说明不确定度来源；BIPM/JCGM GUM 提供不确定度表达和传播框架。[NIST Measurement Uncertainty](https://www.nist.gov/itl/sed/topic-areas/measurement-uncertainty)、[BIPM JCGM Guides](https://www.bipm.org/en/web/guest/publications/guides) 这些资料支持“按证据估计不确定度”的方法论，不规定本项目的 `τ` 数值。

## 影响

- 在 ADR 被批准前，所有真实推断行必须因 `DP6_TOLERANCE_NOT_APPROVED_OR_MISSING` 保持 `indeterminate`，不能发布。
- 采用 C 会使早期数据较少的 scope 暂时不能发布，但保留了后续回算和复核路径；采用 A/B 会提高可操作性，却增加跨 scope 误用风险。
- 每个获批实例必须记录 `decided_by`、`decision_date`、`evidence_anchor`、`effective_from/to`，并在证据锚或外部审计记录中注明所依据的本文件版本；当前容差 schema 不允许额外塞入未定义字段。
- 新的实际值、产能天顶变化、产品族拆分、主体/厂址重组或推导式变化，应触发重算或重开，而不是沿用旧容差。

## 必须由用户回答的精确人闸问题

1. 首个获批实例的完整 scope 是什么：`subject_id`、`plant_id`、`product_family`、`fab_cell`、`metric_type`、`unit`、`period_type`、`period`、`currency`、`consolidation_basis`？
2. 选择 A、B 还是 C？若选 A/B，请给出每个精确 scope 的 `tolerance` 小数值；若选 C，请给出 `τ_round`、`τ_cap`、Q 分位数、校准窗口和最小样本数。
3. 只有产销量表/建成产能自述才可作强天顶是否确认？`approval_capacity` 是否一律维持 `indeterminate`？
4. `τ=0` 是否允许作为某些已直接披露、无推导误差的精确 scope 的显式决定？
5. 容差的复审触发条件和失效日期是什么：新财报、天顶变更、主体重组、产品族变更、单次回算超界、连续多次回算超界，还是以上全部？
