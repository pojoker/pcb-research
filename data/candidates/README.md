# 候选实例账本

本目录只保存待人工裁决的分母、来源、公司点/关系和量化候选；它不是 canonical 图谱，也不能进入发布闸的正式输出。

- `denominator_candidates.csv`：DP1 schema；L1-A、L2、L3、L4 候选，L2 行由 `data/snapshots/2026-08-28/` 两个原始官方快照机械展开。
- `denominator_l1bc_candidates.csv`：DP1 schema；13 家 L1-B 与 6 家 L1-C 发行人候选，只承重证券披露入口，产品格仍待人闸。
- `t1_source_candidates.csv`：DP2 schema；`source_role=direct` 只描述来源关系，不等于 T1 承重许可。
- `company_points_edges.json`：DP5 候选扩展；内部 `subject_id` 遵循 DP5 的无冒号 ID 语法，外部四类 ID 通过 `subject_identity_map.csv` 对接 DP1。
- `capacity_metrics.json`：量化候选扩展；批复、建成、实际产量、销量与收入分列，未补全物理键或人闸前不得转换为 DP5/DP6 正式输入。
- `subject_identity_map.csv`：不同候选账本的主体 ID 桥；映射状态仍可为 pending，不据名称猜配法人、厂址或集团。

机械转换只能保持 `pending/待核`。T1、挂格、集团关系、禁止加总期间、强天顶、容差和汇率规则必须由人闸留痕。
