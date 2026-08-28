# DP5 证据/委外账本校验器

DP5 是 Wave 2 的离线、Python 标准库校验器。它只读取 `tree.yaml` 的活动格与阶段；不会写入 canonical
文件、事实点、关系边或其他 package。

它严格校验四类账本记录：能力 `point`、量化 `metric`、`manufacturing_edge` 和版本化
`prohibited_additive_subject_pair`，并以 `subject_mappings` 提供 issuer/legal entity/plant/group 四类 ID 映射。
任何未知枚举、缺列、NaN/Inf、重复 ID、悬空主体/边、时间倒置或主体不一致均失败。四类映射允许未知，
但缺失 ID 必须填写 `missing_id_reason`，不得编造占位 ID。

## 运行

```sh
PYTHONPATH=packages/dp5-ledger python3 -m dp5_ledger validate-ledger \
  --tree tree.yaml \
  --input packages/dp5-ledger/fixtures/valid_ledger.json \
  --output /tmp/dp5-ledger-report.json
```

输出始终是机器可读 JSON：退出码 `0` 为通过，`1` 为可解析但违反契约，`2` 为文件/JSON/schema 输入错误。

## 机械阻断

- 能力 point 必须显式给出合法 `cell_id`、`product_family`、角色、证据主体、原文锚和成熟度；角色不会由格推断。
- `product_family` 使用冻结的板族词表；M1/M3 等材料能力仍按所服务板族填写，不把材料格名称伪装成产品族。
- 只有 `mixed_business=true` 的混合业务记录必须填写 `split_evidence_id`；非混合记录禁止伪造拆分锚。
- `process_outsourcing` point 与由制造委外边导出的记录，不能生成 `self_owned` 产量。
- 委外边必须完整声明 capacity owner、process operator、contracting party、product integrator、seller of record，以及关系期间和证据锚。
- IC 载板只能挂 `FAB2`；其余板族只能挂 `FAB1`。PCBA/SMT/EMS/设计/整机/锂电铜箔均为树外，禁止挂 FAB。
- 聚合请求会阻断 FAB1/FAB2 混加、物理/披露跨输出混加、外协/自有混加、M1 CCL（含箔）与 M3 独立铜箔混加，以及禁止加总主体对的任一方向命中。

## 测试

```sh
cd packages/dp5-ledger
python3 -m unittest discover -s tests -v
python3 selftest.py
```

`fixtures/` 按 point、metric、manufacturing edge、prohibited pair 四类存放反例，并覆盖外协自有推断、
产品族缺失、母子双计、PCBA 收入挂 FAB、FAB 混格、五元组缺字段、混合记录无拆分锚、CCL 含箔、
台母披露与大陆厂物理输出混加、时间倒置、未知枚举和 NaN。
