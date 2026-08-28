# 实例候选首轮集成审计

审计日期：2026-08-28

## 结论

本轮已把“正式数据缺失”推进到可逐项人审的候选状态，但没有越权把候选写成 canonical：

- 分母候选 2,036 行：L1-A 29、L1-B 13、L1-C 6、L2 1,985、L3 2、L4 1；
- L2 原始官方快照 2 份：TWSE 1,095、TPEx 890，保留原始 JSON、SHA-256、HTTP 状态、出表日，代码交集为 0；
- T1 来源资格候选 12 条，全部 `待人工裁决`；
- 公司 point 候选 11 条、manufacturing edge 0 条、禁止加总 pair 候选 1 条；
- 产能/量化候选 9 条：批复 1、建成 2、实际产量 1、销量 1、收入 4；
- 容差 ADR 与汇率 ADR 均为 `status: proposed`，未生成任何 approved 实例。

因此，机械实例化底稿已形成；“正式冻结、T1 允许、point/metric canonical、容差/FX 生效”仍必须由用户人闸批准。

## Kimi / Cursor 双审与主审修复

两位本地只读审核员共同指出：候选曾自标 T1、主体 ID 跨账本不可 join、依顿产能丢失 `/年` 维度、兴森数值短引不承重、未裁决 pair 填了裁决日期、L3 预填集团关系、L2 缺原始快照哈希、TPEx 证书兼容开关过宽。

主审已修复：

1. 11 个 point 和 pair 的来源等级统一降为 `T1_candidate`；
2. 新增 `subject_identity_map.csv`，以 DP1 四类外部 ID 桥接 DP5/产能内部 ID；
3. 依顿两行改为 `square_meter_per_year`，兴森锚同时保留 6,000 平方米/月和建成试产；
4. pair 的 `adjudicated_on` 清空，L3 两行不再预填 `group_id` 与禁止加总结论；
5. 保存 TWSE/TPEx 原始快照和 SHA-256，并加入计数/交集自检；
6. TPEx 的 `VERIFY_X509_STRICT` 兼容只允许官方 endpoint；
7. G1-A 已批准的 L2 母集字段在 TWSE/TPEx 适配器与候选 CSV 间对齐；
8. 产品列示不能承重量产的 5 个材料/设备 point，成熟度降为 `qualified`；
9. 补齐 13 家 L1-B 与 6 家 L1-C 分母候选，保证现有 point 有分母回指。

## 机械验收

- `python3 data/candidates/selftest.py`：PASS；
- DP1 单元测试：18/18；
- 全仓单元测试：85/85；DP1–DP7 加候选账本 selftest：8/8；
- L2 快照哈希、行数、代码交集校验：PASS；
- DP1/DP2 候选 schema：PASS；
- 全部候选 JSON 可解析；
- 任何 point/metric/T1/ADR 均未逃逸 pending/proposed 状态。

## 人闸建议

1. 批准当前 L2 快照冻结时点：2026-08-28，TWSE+TPEx、不含兴柜；发行人母集不等于 PCB 主营或大陆物理产能。
2. 12 个来源可按各行 `coverage_scope + review_note` 一次性批准窄范围 T1；索引/导航页自身不能代替具体公告正文。
3. 公司 point、pair 和 9 条量化记录应逐条批准；缺产品族、厂址、法人、物理流或原始批复者继续 pending。
4. 容差 ADR 推荐批准“无全局默认、按精确 scope 校准；样本不足即 indeterminate”；不批准任意 10%/30%。
5. FX ADR 推荐批准“目标 CNY、强制保留原币、存量期末前最后官方报价日、流量交易日优先；期间平均须满足单独波动人闸”；未批准波动规则时平均折算保持 indeterminate。
