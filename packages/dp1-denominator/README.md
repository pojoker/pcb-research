# DP1 分母登记器

DP1 是波 1 的机械登记包：登记候选分母、校验 CSV schema、生成快照元数据和增删 diff，并把重复候选交给人工 triage。它不决定研究范围，不把候选自动冻结，也不把母子公司合并。

## 目录

- `fixtures/_frozen.csv`：待核候选分母。每行显式包含 `issuer` / `legal_entity` / `plant` / `group` 四类 ID 字段；不用的字段写 `-`。
- `fixtures/inclusion_decision.csv`：三组母子/合并口径重复候选的 triage 记录。
- `dp1_denominator/registry.py`：schema、身份/层级/来源/日期校验，重复候选识别，快照元数据和 diff。
- `dp1_denominator/adapters.py`：配置驱动的 JSON/HTTP 草稿适配器。输出状态强制为 `待核`。
- `tests/`、`selftest.py`：离线 unittest 与反例。

## 离线自测

在仓库根目录运行：

```bash
python packages/dp1-denominator/selftest.py
```

预期为 8 个测试全部通过。也可以在包目录运行：

```bash
cd packages/dp1-denominator
python selftest.py
```

## 常用命令

校验分母和裁决台账：

```bash
PYTHONPATH=packages/dp1-denominator \
python -m dp1_denominator.cli validate \
  --frozen packages/dp1-denominator/fixtures/_frozen.csv \
  --decisions packages/dp1-denominator/fixtures/inclusion_decision.csv
```

生成快照元数据。`source_url` 是登记元数据，不表示来源结论已经核验：

```bash
PYTHONPATH=packages/dp1-denominator \
python -m dp1_denominator.cli snapshot \
  --frozen packages/dp1-denominator/fixtures/_frozen.csv \
  --output /tmp/dp1-snapshot.json \
  --source-name fixture-seed \
  --source-kind fixture \
  --source-url https://example.invalid/dp1/fixture-seed \
  --query-date 2026-08-26 \
  --adapter-name fixture \
  --freeze-status 待核
```

生成增删报告和 triage 台账：

```bash
PYTHONPATH=packages/dp1-denominator \
python -m dp1_denominator.cli diff \
  --before old/_frozen.csv \
  --after new/_frozen.csv \
  --before-snapshot-id snap:old \
  --after-snapshot-id snap:new \
  --query-date 2026-08-26 \
  --existing-decisions packages/dp1-denominator/fixtures/inclusion_decision.csv \
  --out-dir /tmp/dp1-diff
```

该命令同时写出 `diff.csv`、`triage.csv` 和合并后的 `inclusion_decision.csv`。每个 `add`/`remove` 都必有一行 `snapshot_add`/`snapshot_remove`，且保持 `待核`。

配置适配器只负责草稿映射：

```bash
PYTHONPATH=packages/dp1-denominator \
python -m dp1_denominator.cli fetch-draft \
  --config packages/dp1-denominator/fixtures/draft_config.json \
  --output /tmp/dp1-draft.csv
```

生产配置应使用真实 endpoint、字段映射和来源元数据；适配器不内置交易所或协会成员结论，HTTP 返回的数据也不会被标成 `已冻结`。

## 关键规则

`_frozen.csv` 是严格字段集合；空值必须写 `-`。`entity_id` 必须与 `entity_type` 对应的 ID 相等，四类 ID 使用带命名空间的形式，如 `issuer:TW:4958`。层级只接受 `L1-A`、`L1-B`、`L1-C`、`L2`、`L3`、`L4`、`观察`；来源 URL 必须为 HTTP(S)，查询日为 ISO 日期。

`double_count_key` 重复只产生 warning/候选，不作删除、合并或加总。三组 fixtures 明确覆盖：臻鼎-KY×鹏鼎控股、建滔集团×建滔积层板、生益科技×生益电子；其统计策略均为 `分列-禁止加总`。
若传入冻结行校验决策台账，则每个重复键下的每个主体都必须有 `duplicate_candidate` triage 行。

所有 fixtures 都是 `待核`，`example.invalid` 仅用于离线测试，不能被解释为交易所、协会或披露易结论。研究范围、层级成分、混合主体拆分、双计键的最终含义仍需用户判定闸裁决。
