# H1–H4 正式实例账本

本目录由 `build_from_approved_candidates.py` 从候选数据确定性生成。独立人闸输入位于
`data/decisions/2026-08-28-h1-h4.json`，生成器只校验并复制，不得创造或改变裁决；`build_manifest.json`
保存该输入和整批数据产物的 SHA-256。

- H1：`denominator_l2_frozen.csv` 与配套裁决冻结 1,985 条台湾上市/上柜发行人机械母集。
- H2：`t1_source_ledger.csv` 仅在逐行 `coverage_scope + review_note` 内允许 T1 承重。
- H3：冻结 13 家发行人分母，并以 `subject_identity_map.csv` 跨账本连接主体；正式纳入 11 个 point、0 条制造边、1 个禁止加总 pair；9 条产能/金额记录只作为披露快照，全部禁止聚合与发布。
- H4：接受容差与汇率规则形状；当前容差数值实例和实际 FX 换算均为 0。

消费纪律：T1 必须同时读取 `t1_bearing_decision + coverage_scope + review_note` 并落到具体文件 URL；不得只凭导航页或“人工允许”承重。point 只证明窄范围能力，禁止从 `evidence_quote` 抽取数字生成产能；定量内容只能走受阻披露快照或后续正式 metric 人闸。

运行 `python3 data/canonical/selftest.py` 会先重建全部生成物，再调用 DP1、DP2、DP5 校验器并检查阻断条件。
