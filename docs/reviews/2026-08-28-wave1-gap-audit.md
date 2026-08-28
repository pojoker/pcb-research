# Wave 1（DP1 / DP2 / DP4）严格依赖审计

**结论：不允许进入 Wave 2。**

| 开发包 | 裁决 | Wave 2 放行 | 阻断原因 |
|---|---|---|---|
| DP1 分母登记器 | **fail** | 否 | 可在没有人工裁决记录的情况下把示例来源行校验为 `已冻结`。 |
| DP2 来源登记器 | **indeterminate** | 否（随整体阻断） | 核心机械闸通过，但没有独立 selftest，且 CSV CLI 未执行精确表头 schema 校验。 |
| DP4 词表实测器 | **fail** | 否 | 非活动格 M6/M8 可作为 `target_cell`；M4 在活动格与损耗俗称之间存在宪法冲突；三个候选词没有任何排除正则。 |

单测全绿不能覆盖上述结论：Wave 1 的验收对象是“反例 + 不变量 + 人闸边界”，不是仅测试通过。审计过程未修改 `packages/`、canonical graph、`tree.yaml` 或其他项目文件；本报告是本次唯一持久写入，未提交 Git。

## 审计范围与判据

- 交付基线：`ddf6d29...037a597`，45 个 Wave 1 文件、2,947 行新增；`037a597..HEAD` 未再改动三个包。
- 对照：`docs/plans/06-外包开发任务书.md` 的 DP1/DP2/DP4 交付和验收段；`CLAUDE.md` 第 1、3、6 条；`docs/05-不变量清单.md` 的 ①、⑦、⑧、⑨、⑩、⑰、⑱、⑲、㉑；以及包内 README、代码、fixtures、tests。为核验包所声明的上游约束，同时读取 `docs/01-宇宙分母.md` 与 `docs/04-词表.md`。
- 依赖边界：三个包仅依赖 Python 标准库；仓库内没有其他模块导入它们。它们不读取或写入 canonical 文件。各包的 CLI 本身可以写调用方指定的输出路径，此次审计未调用任何会在项目目录落盘的写命令。

## 已实际运行的命令

所有 Python 命令均加 `PYTHONDONTWRITEBYTECODE=1`；测试内部临时目录在运行结束时删除。

```sh
cd /Users/jowang/Downloads/pcb-research/packages/dp1-denominator
python3 -m unittest discover -s tests -v
python3 selftest.py

cd /Users/jowang/Downloads/pcb-research/packages/dp2-sources
python3 -m unittest discover -s tests -v

cd /Users/jowang/Downloads/pcb-research/packages/dp4-lexicon
python3 -m unittest discover -s tests -v

cd /Users/jowang/Downloads/pcb-research
PYTHONPATH=packages/dp1-denominator python3 -m dp1_denominator validate \
  --frozen packages/dp1-denominator/fixtures/_frozen.csv \
  --decisions packages/dp1-denominator/fixtures/inclusion_decision.csv
PYTHONPATH=packages/dp2-sources python3 -m dp2_sources detect-echoes \
  packages/dp2-sources/fixtures/prismark_three_layers.json /dev/null
PYTHONPATH=packages/dp2-sources python3 -m dp2_sources probe-t1 \
  packages/dp2-sources/fixtures/t1_probe_sources.csv /dev/null
PYTHONPATH=packages/dp4-lexicon python3 -m dp4_lexicon selftest
PYTHONPATH=packages/dp4-lexicon python3 -m dp4_lexicon validate
PYTHONPATH=packages/dp4-lexicon python3 -m dp4_lexicon measure \
  --corpus packages/dp4-lexicon/fixtures/corpus.jsonl \
  --scope audit-fixture --date 2026-08-28
```

结果：DP1 `8/8`、DP2 `12/12`、DP4 `4/4` 单测通过；DP1 selftest 通过；DP4 文档化 selftest 输出 `PASS (10 entries, 17 golden fixtures)`。DP2 没有独立 selftest 入口或文件。DP2 的空来源台账和空 8534 模板分别返回退出码 `1`，符合“模板未填写不得通过”的负向预期。

## DP1 分母登记器 — fail

### 已满足的验收项

- `_frozen.csv` 严格使用四类 ID 字段、名称、层级、登记源、URL、查询日；实现对 ID 命名空间、层级、日期和 URL 做校验。证据：[registry.py](../../packages/dp1-denominator/dp1_denominator/registry.py) 第 15–20、182–208、241–273 行；[_frozen.csv](../../packages/dp1-denominator/fixtures/_frozen.csv)。
- 三组母子/合并口径候选都存在，并由重复键生成 warning 而非自动删除；缺少 `duplicate_candidate` triage 会失败。证据：[test_registry.py](../../packages/dp1-denominator/tests/test_registry.py) 第 40–52 行、[inclusion_decision.csv](../../packages/dp1-denominator/fixtures/inclusion_decision.csv)。
- 快照增删会生成 `snapshot_add` / `snapshot_remove` triage 行。证据：[registry.py](../../packages/dp1-denominator/dp1_denominator/registry.py) 第 415–442 行、[test_registry.py](../../packages/dp1-denominator/tests/test_registry.py) 第 78–99 行。
- 草稿适配器强制输出 `待核`，不会把 HTTP/fixture 输入直接标为冻结。证据：[adapters.py](../../packages/dp1-denominator/dp1_denominator/adapters.py) 第 39–63 行、[test_registry.py](../../packages/dp1-denominator/tests/test_registry.py) 第 101–137 行。

### 未满足验收项 / 阻断证据

1. **冻结状态没有绑定人工纳入裁决，违反“人闸不可外包”与分母冻结/增列必须留痕。**

   `validate_frozen` 只验证 `record_status` 是 `待核` 或 `已冻结`，不要求 `manual_include` 决策、裁决人、裁决日期或可核验锚；`build_snapshot_metadata` 也接受 CLI 传入的 `--freeze-status 已冻结`。证据：[registry.py](../../packages/dp1-denominator/dp1_denominator/registry.py) 第 241–265、348–383 行；[cli.py](../../packages/dp1-denominator/dp1_denominator/cli.py) 第 43–64、110–119 行。

   可复现的无落盘反例：

   ```sh
   cd /Users/jowang/Downloads/pcb-research
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/dp1-denominator python3 -c '
   from dp1_denominator.registry import FROZEN_FIELDS, load_csv, validate_frozen
   rows = load_csv("packages/dp1-denominator/fixtures/_frozen.csv", FROZEN_FIELDS)
   rows[0]["record_status"] = "已冻结"
   report = validate_frozen(rows)
   print({"valid": report.ok, "errors": report.errors, "source_url": rows[0]["source_url"]})'
   ```

   实际输出为 `{'valid': True, 'errors': [], 'source_url': 'https://example.invalid/...'} `。也就是说，一个没有 `manual_include` 记录、仍指向 `example.invalid` 的示例行可通过冻结校验。这与 `docs/01-宇宙分母.md` “冻结后增列走判定闸留痕”、`CLAUDE.md` 第 1/3 条、以及不变量 ①/⑦/⑰ 的意图不相容。

2. **“交易所/协会成分抓取”仅有通用 JSON/HTTP 映射器，未交付任一交易所或协会的实际适配器/可审计抓取样例。**

   适配器要求调用方提供 endpoint、字段映射和来源元数据；fixtures 仅为 `example.invalid`。这足以作“草稿映射器”，但不足以证明任务书所列的交易所/协会成分抓取已交付。证据：[adapters.py](../../packages/dp1-denominator/dp1_denominator/adapters.py) 第 22–63 行、[README.md](../../packages/dp1-denominator/README.md) “生产配置应使用真实 endpoint”段、[draft_config.json](../../packages/dp1-denominator/fixtures/draft_config.json)。

### 放行条件

补上“`已冻结` 必须由对应 `manual_include` 的裁决人、日期、锚和双计策略共同授权”的机械关联，并新增回归反例；再交付至少一个真实来源适配器或把任务书明确降级为“通用草稿映射器”。在此之前不放行。

## DP2 来源登记器 — indeterminate

### 已满足的验收项

- 台账字段包含 `origin_source_id`、`carrier_url`、`independence_group`、`paywall`、`coverage_scope` 和 `direct|secondary|derived|unavailable`，并要求记录/复核/T1 人工裁决字段。证据：[schema.py](../../packages/dp2-sources/dp2_sources/schema.py) 第 16–40、67–113 行。
- T1 网络探测默认关闭，打开网络后也固定产出 `待人工裁决`，没有将 HTTP 成功升级为承重资格。证据：[accessibility.py](../../packages/dp2-sources/dp2_sources/accessibility.py) 第 41–88 行、[test_accessibility.py](../../packages/dp2-sources/tests/test_accessibility.py) 第 11–44 行。
- 8534 缺任一冻结字段即为 `待核-口径未冻结`；字段齐全仍要求人工裁决和审计字段。证据：[customs8534.py](../../packages/dp2-sources/dp2_sources/customs8534.py) 第 39–70 行、[test_customs8534.py](../../packages/dp2-sources/tests/test_customs8534.py) 第 7–27 行。
- Prismark → 券商 → 自媒体 fixture 跨三个域名却计作一个独立来源；计数基于 `independence_group` 而非转载数。证据：[echoes.py](../../packages/dp2-sources/dp2_sources/echoes.py) 第 69–97 行、[test_echoes.py](../../packages/dp2-sources/tests/test_echoes.py) 第 8–26 行。

### 不能判为 pass 的事项

1. **没有独立 selftest。**

   任务书的发包交付约定是“代码 + selftest + fixtures 报告”；DP2 只有 unittest，README 将其称为“离线自测”，但包内不存在 `selftest.py` 或 `selftest` CLI 子命令。严格审计不能将两者等同。可复现：

   ```sh
   cd /Users/jowang/Downloads/pcb-research
   rg --files packages/dp2-sources | rg '(^|/)selftest(\\.py)?$'
   ```

   输出为空。

2. **来源台账和 8534 的 CLI 没有精确 CSV 表头校验。**

   `_read_csv` 直接使用 `csv.DictReader`，随后逐行校验值；`LEDGER_FIELDS` 与 `FREEZE_TEMPLATE_FIELDS` 只作为常量/返回值，并未在 CLI 上比较 `fieldnames`。缺列通常会因必填值缺失而失败，但多列和字段顺序漂移不会作为 schema drift 阻断。DP1 的 `load_csv` 已展示了本项目要求的“精确字段集”实现，DP2 未对齐。证据：[cli.py](../../packages/dp2-sources/dp2_sources/cli.py) 第 18–24、27–56 行；[schema.py](../../packages/dp2-sources/dp2_sources/schema.py) 第 21–40、116–119 行；[customs8534.py](../../packages/dp2-sources/dp2_sources/customs8534.py) 第 11–28、73–74 行。

### 放行条件

补一个可从包根运行的 selftest，覆盖四个 CLI 闸和 fixtures；并在读 CSV 时对 ledger/8534 的完整、顺序固定表头 fail-closed。之后可复审为 pass；但当前整体仍受 DP1/DP4 阻断。

## DP4 词表实测器 — fail

### 已满足的验收项

- 实现和 JSON schema 都强制七字段结构，正则编译失败、未知 target、重复词形、裸缩写会 fail-closed。证据：[schema.py](../../packages/dp4-lexicon/dp4_lexicon/schema.py) 第 13–100 行、[validation.py](../../packages/dp4-lexicon/dp4_lexicon/validation.py) 第 95–167 行。
- golden fixtures 覆盖正例、反例和边界例；SAP/HDI/BT/PCB 四个负样本均在实际 selftest 中为空命中。证据：[golden.json](../../packages/dp4-lexicon/fixtures/golden.json)、[selftest.py](../../packages/dp4-lexicon/dp4_lexicon/selftest.py) 第 24–89 行。
- 四键实测和碰撞统计确实执行，审计语料得到 4 篇文档、3 篇有命中、2 篇碰撞，状态仍为 `pending_review`。证据：[corpus.py](../../packages/dp4-lexicon/dp4_lexicon/corpus.py) 第 21–110 行。

### 未满足验收项 / 阻断证据

1. **M6/M8 被接受为 `target_cell`；M4 则暴露了上游规格自相矛盾。**

   `RESERVED_CELL_IDS` 把 M4/M6/M8 一并当作合法 target 集合。M6/M8 不在 `tree.yaml` 的活动格中，因此接受它们是确定性漏洞。M4 不同：`tree.yaml` 与 `docs/04-词表.md` 的活动格清单把 M4 定义为“基体树脂与固化体系”，但同一文档下一条又把 M4 与 M6/M8 一起称为损耗等级俗称并写“禁止作格 ID”。这不是校验器能自行裁决的问题，必须在 G4 人闸中决定保留/改名并同步修正规格。证据：[validation.py](../../packages/dp4-lexicon/dp4_lexicon/validation.py) 第 13–48 行；[docs/04-词表.md](../04-词表.md) 第 8–12 行；[tree.yaml](../../tree.yaml) 的 M4 cell。

   可复现的无落盘反例：

   ```sh
   cd /Users/jowang/Downloads/pcb-research
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/dp4-lexicon python3 -c '
   from dp4_lexicon.validation import validate_cell_id
   accepted = []
   for value in ("M4", "M6", "M8"):
       validate_cell_id(value)
       accepted.append(value)
   print({"accepted_as_target_cells": accepted})'
   ```

   实际输出：`{'accepted_as_target_cells': ['M4', 'M6', 'M8']}`。其中 M6/M8 应确定性拒绝；M4 的期望结果等待人闸。现有 tests 只测试“把 M6 当词形”会拒绝，没有测试“把 M6/M8 当 target”会拒绝。

2. **三个候选词没有排除正则。**

   `docs/04-词表.md` 要求“每个词必须登记真实可编译的排除正则”；但 `覆铜板`、`半固化片`、`PI膜` 的 `exclude_patterns` 均为空数组。任务书也要求 include/exclude patterns 的结构化词表和反例 fixtures。证据：[candidate_lexicon.json](../../packages/dp4-lexicon/data/candidate_lexicon.json) 第 2–27、75–81 行；[docs/04-词表.md](../04-词表.md) 第 3–6 行。

   可复现：

   ```sh
   cd /Users/jowang/Downloads/pcb-research
   python3 -c 'import json; rows=json.load(open("packages/dp4-lexicon/data/candidate_lexicon.json", encoding="utf-8")); print([row["term"] for row in rows if not row["exclude_patterns"]])'
   ```

   实际输出：`['覆铜板', '半固化片', 'PI膜']`。

### 放行条件

将 M6/M8 从合法 target 集合移除并增加 target 反例；由 G4 人闸裁决 M4 是保留为活动树脂格还是改名，同时明确损耗俗称的词表表达；为每个候选补上可编译排除正则及各自负/边界 fixture，或由判定闸明确修订 `docs/04-词表.md` 的“每词必有排除正则”规则。完成后重新运行 selftest、unittest 和 measure。

## 最终放行清单

- [ ] DP1：冻结状态与人工裁决记录强绑定；真实来源适配器/范围降级完成。
- [ ] DP2：独立 selftest 与严格 CSV 表头闸完成。
- [ ] DP4：M6/M8 target 漏洞封堵；M4 命名冲突经 G4 人闸解决；三个空排除词补齐反例。
- [ ] 三包重跑测试、selftest 和所列无落盘反例，审计复核为 pass。

在以上清单全部完成前，按 `CLAUDE.md` 第 3 条和不变量 ⑲，Wave 2 的 DP3/DP5/DP6/DP7 不应启动。
