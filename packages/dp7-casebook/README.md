# DP7 判例库校验器

DP7 是离线、Python 标准库、纯机械校验器。它只校验人工填写的判例与其引用记录：不会生成行业结论，不会从证据链、锚点或内容推导/升级/选择 A–D 等级，也不会把 A/B 自动标记为 Canonical。

输入是一个严格 JSON 文档，根字段固定为 `schema_version`、`cases`、`references`；未知字段一律拒绝。空库（两数组均为空）合法，故可在首例前开工。

## 运行

在仓库根目录：

```sh
PYTHONPATH=packages/dp7-casebook python3 -m dp7_casebook validate \
  --input packages/dp7-casebook/fixtures/empty_casebook.json
```

默认输出机器可读 JSON；退出码为 `0` 表示有效，`1` 表示记录被拒绝，`2` 表示文件或 JSON 无法读取。

## 人工填写契约

每个 case 必须有：人工结论与 A/B/C/D 等级、至少一个 point/edge 等槽位引用、已到工序阶段及其后全部未动用阶段、证据链、替代解释和排除理由、剩余不可知、可推翻条件、裁决人/日期、版本，以及恰好以下 13 项陷阱检查：

`direct_terminal_customer`、`accounting_period`、`fx`、`multi_entity`、`trader_intermediary`、`group_subject_scope`、`bonded_processing_trade`、`outsourced_process_attribution`、`substrate_mixing`、`lithium_copper_foil`、`area_unit_period`、`tpca_scope`、`plant_legal_issuer`。

每项陷阱均须 `status=checked|not_applicable`、非空说明及证据锚；`not_applicable` 也不能省理由。每条证据须有 `origin_source_id`、`independence_group`、`anchor_type`、`anchor_locator`、`retrieval_date`、`claim_or_role` 和人工填写的 `evidence_strength`。后者仅让 B 级的“至少一个硬证据”成为可审计的人工声明，并不推导等级。

锚类型只允许 `url`、`local_file`、`ledger_ref`、`search_protocol`、`web_snapshot`。URL 必须是 http(s) URL；本地文件必须是路径形态；后三类必须是无空白、带命名空间分隔符的引用，例如 `ledger:EDGE-1` 或 `search_protocol:case-001`。校验器不会访问这些位置。

引用记录必须包含 `reference_id`、`case_id`、`consumer_type`、`consumer_id`、`usage` 与类型化 `anchor`，且 consumer 必须命中该判例声明的槽位。C 级不能 `load_bearing`；D 级只能 `limit`；悬空引用、重复 ID、未知字段、日期和枚举均为红。A级至少要有两个不同 `origin_source_id`、两个不同 `independence_group`，且两条均由人工标为 `hard`；同一来源不得伪填多个独立组。B级至少有一个人工标为 `hard` 的证据；C/D 仍须填写不可知与可推翻条件。13 项陷阱的 `evidence_anchor` 必须回指本判例证据链中的 `origin_source_id`。

## 验收

```sh
cd packages/dp7-casebook
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 selftest.py
```

`fixtures/empty_casebook.json` 是可开工空库；`fixtures/templates.json` 含有效 A/B/C/D 模板和允许的 A/B/C/D 引用方式；`fixtures/cases.json` 枚举自测逐项复现的所有红色反例。
