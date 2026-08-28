# Wave 2 机械实现集成审计

审计日期：2026-08-28

## 结论

G1-A/G2-A/G3-A/G4-A/G5-A/G6-A 经用户批准后，Wave 2 的四个机械开发包已全部实现并通过集成验收：

- DP3：`packages/dp3-tree`，冻结树、30 cells、A–F、M4/M6/M8、树外邻居、空格渲染与工序—设备映射闸；
- DP5：`packages/dp5-ledger`，能力点、量化记录、委外五元组、禁止加总主体对与聚合阻断；
- DP6：`packages/dp6-publish-gate`，pass/fail/indeterminate、产能天顶、8534 宏观边界、容差 ADR 接口与安全渲染；
- DP7：`packages/dp7-casebook`，空库开工、A–D 人工判例模板、13 项陷阱、锚类型和 C/D 承重限制。

开发提交依次为：`458fbb3`（DP3）、`8c6ce04`（DP5）、`734a1d1`（DP6）、`60a9b45`（DP7）。

## 集成验收

- 根图谱：`python3 scan.py --check` 通过，30 cells、40 claims、25 evidence、49 条 claim-evidence 关系、21 条 knowledge edges；
- 单元测试：根目录与 DP1–DP7 合计 **81/81** 通过；
- 独立自测：DP1–DP7 **7/7** 通过；
- 所有 `packages/**/*.json` 均可严格解析；
- `git diff --check` 通过；
- 验收前工作区干净，`main` 已逐包推送 GitHub。

## 主审修复

外包实现返回后，主审补强了以下易漏边界：

1. DP3：PM1–PM3 不得误当 P1–P9 工序；`IC 载板` 词形对齐；材料能力不被强塞 FAB；
2. DP5：非混合主体不得伪造拆分锚；缺失四类 ID 必须留原因；量化类型与冻结口径对齐；
3. DP6：容差未批准时不得用零容差误判 fail；customs-only 不依赖容差 ADR；renderer 重新计算 publishable；
4. DP7：A级要求两个独立来源组的两条硬证据；同源不得伪装独立组；陷阱锚与消费槽位必须可回指。

## 仍未完成且不可外包的研究状态

本审计只证明机械合同可以执行，不证明产业知识图谱已实例化。以下仍保持 pending：

- 各层正式 `_frozen` 分母行及逐行 inclusion/exclusion 裁决；
- T1 承重资格和真实 8534 冻结快照；
- 公司/法人/厂址/集团 canonical points、制造/委外/供应 edges 与 30 格覆盖；
- 公司级产量、销量、收入、产能与 recalibration 账本；
- 容差 ADR、汇率折算 ADR；
- 客户/供应关系、路线画像和公开不可验主张的后续重开。

因此 Wave 2 开发包可以结案，但“整个 PCB 产业知识图谱”目标继续保持 active。
