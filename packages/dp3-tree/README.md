# DP3 树结构校验器

DP3 是 Wave 2 的离线、标准库实现，用来把冻结的 PCB 结构树变成可机械检查的契约。它只读 canonical `tree.yaml`，不会修改树、docs、graph 或其他 package。

## 覆盖范围

- 严格检查树的根字段、cell 字段、A-F 路线轴字段；要求 `status=frozen`、30 个且仅 30 个活动格、唯一 `cell_id` 和唯一合法 `flow_id`。
- `M4` 是合法活动格；`M6/M8` 是保留损耗词，不能成为 cell 或 target；`OUT` 是树外命名空间，不是 cell。
- 检查 `stage`、`finished_board`、六个树外邻居，以及路线值不可冒充 cell。
- 校验板厂/能力样本必须落到合法 `cell_id`，并执行产品族兼容矩阵：普通刚性、HDI、FPC、刚挠、金属基、高频、背板 → `FAB1`；IC 载板 → `FAB2`；PCBA、SMT、EMS、设计、锂电铜箔、整机 → 树外。
- 显式渲染 30 格覆盖表。没有附件的格输出 `empty_space=true` 和 `space="空格"`，不会被省略。
- 校验 `process_equipment_map` 的显式多对多边。未映射工序返回 `unmapped_processes`，不会自动补 `EQ6/EQ7`。

`tree.yaml` 当前是 JSON-compatible YAML，因此 DP3 用 Python 标准库 `json` 解析，避免隐式引入 YAML 方言或第三方依赖。

## 运行

在仓库根目录执行：

```sh
PYTHONPATH=packages/dp3-tree python3 -m dp3_tree validate-tree \
  --tree tree.yaml --output /tmp/dp3-tree.json

PYTHONPATH=packages/dp3-tree python3 -m dp3_tree validate-samples \
  --tree tree.yaml \
  --input packages/dp3-tree/fixtures/valid_samples.json \
  --output /tmp/dp3-samples.json

PYTHONPATH=packages/dp3-tree python3 -m dp3_tree validate-map \
  --tree tree.yaml \
  --input packages/dp3-tree/fixtures/valid_process_equipment_map.json \
  --output /tmp/dp3-map.json

PYTHONPATH=packages/dp3-tree python3 -m dp3_tree render \
  --tree tree.yaml \
  --input packages/dp3-tree/fixtures/valid_render_input.json \
  --output /tmp/dp3-render.json
```

退出码为 `0` 表示通过，`1` 表示输入可解析但违反契约，`2` 表示文件或 schema 输入错误。

## 输入约定

样本 JSON 是对象数组，每行严格包含：`sample_id`、`entity_id`、`entity_name`、`role`、`sample_kind`、`cell_id`、`product_family`、`outside_neighbor`。`board`/`capability` 样本必须有活动 `cell_id`；`outside` 样本的 `cell_id` 必须为空，并使用 `outside_neighbor`。

渲染 JSON 严格包含 `attachments` 和 `coverage` 两个数组。附件字段为 `attachment_id`、`cell_id`；覆盖字段为 `cell_id`、`status`，状态是 `covered`、`empty` 或 `待核`。

设备映射只接受 `{ "process_id": "P*", "equipment_id": "EQ*" }`。同一工序可有多个设备、同一设备可服务多个工序，但重复边、未知端点和语义不兼容边会失败。

## 测试与自测

```sh
cd packages/dp3-tree
python3 -m unittest discover -s tests -v
python3 selftest.py
```

`fixtures/` 中的正例和反例覆盖 M6/M8 target、OUT 假 cell、PCBA 挂 FAB、IC 载板挂 FAB1、裸板无 cell、重复/未知映射和 EQ6/EQ7 兜底误用。selftest 通过公开 CLI 子进程运行，不绕过 CLI schema。
