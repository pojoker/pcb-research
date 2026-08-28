# DP2 来源登记器

PCB 波 1 的离线优先来源登记器。它只保存来源、可达性和口径草稿；不会把 HTTP 成功升级为 T1 承重资格，也不会自动冻结 8534 口径或裁决 Prismark 等来源的事实权重。

## 内容

- `fixtures/source_ledger_template.csv`：来源台账模板。强制字段包括 `origin_source_id`、`carrier_url`、`independence_group`、`paywall`、`coverage_scope`、`source_role` 和审计/人工裁决字段。
- `fixtures/8534_freeze_template.csv`：8534 口径冻结表。十二个冻结项任一缺失，校验结果必为 `待核-口径未冻结`；字段填齐后仍为 `待人工裁决-口径字段齐全`，直到人工留痕作出冻结决定。
- `fixtures/t1_probe_sources.csv`：不含事实的 T1 探测输入样例；实际运行应换为人工登记的 T1 清单。
- `fixtures/prismark_three_layers.json`：已知“Prismark → 券商 → 自媒体”三层转载的离线反例；跨三个域名但同一 `independence_group`，计为一个来源。
- `dp2_sources`：仅依赖 Python 标准库的校验、探测和回声聚类模块。

`source_role` 只接受 `direct`、`secondary`、`derived`、`unavailable`。它描述某锚与原始来源的关系，不等于 T1、也不等于承重许可。

## 离线自测

在本目录运行：

```sh
python3 selftest.py
python3 -m unittest discover -s tests -v
python3 -m dp2_sources detect-echoes fixtures/prismark_three_layers.json /tmp/dp2-echoes.json
python3 -m dp2_sources probe-t1 fixtures/t1_probe_sources.csv /tmp/dp2-probes.json
```

`selftest.py` 是独立离线入口，会通过公开 CLI 依次覆盖来源台账、T1 探测、8534 口径与数字回声四个闸。所有 CSV 输入必须与各自 canonical schema 的字段和顺序完全一致；缺列、多列、乱序或额外数据单元均 fail closed。JSON 回声输入要求字段集合精确，但不把对象字段顺序误当作语义。

最后一条默认**不发网络请求**，而是为每行生成日期、`network_disabled` 错误和 `待人工裁决` 的审计记录。只有用户明确决定进行网络观察时才可以加开关：

```sh
python3 -m dp2_sources probe-t1 INPUT.csv OUTPUT.json --enable-network
```

即使网络探测返回 2xx/3xx，输出的 `bearing_decision` 仍固定为 `待人工裁决`。

## 常用检查

```sh
python3 -m dp2_sources validate-ledger fixtures/source_ledger_template.csv /tmp/dp2-ledger-check.json
python3 -m dp2_sources check-8534 fixtures/8534_freeze_template.csv /tmp/dp2-8534-check.json
```

模板的空行本来就应校验失败：它是待人工填写的结构，而不是示例事实。CLI 输出 JSON 便于后续人工审阅或被其他波次消费；它不修改 canonical 文档。

## 回声检测输入

`detect-echoes` 接受 JSON 数组，每项包含：

```json
{
  "mention_id": "转载条目 ID",
  "carrier_url": "https://carrier.example/article",
  "origin_source_id": "已人工追溯的原始来源 ID",
  "independence_group": "独立性分组",
  "claim_key": "人工限定的同一主张键",
  "text": "携带数字的文本"
}
```

只有同一 `claim_key`、相同归一化数字、且跨至少两个域名的条目会组成“待人工复核-数字回声草稿”。最终 `counted_source_count` 按不同 `independence_group` 计数，绝不按转载篇数或域名数计数。
