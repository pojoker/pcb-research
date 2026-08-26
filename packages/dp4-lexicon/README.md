# DP4 词表实测器

DP4 是波 1 的机械探测包：它校验候选词表、编译所有正则、运行正例/反例/边界例 golden fixtures，并对离线语料生成四键实测记录与碰撞统计。所有输出都标记为 `pending_review`，不会自动决定歧义词收弃，也不会写入项目 canonical 文档。

## 目录

- `data/candidate_lexicon.json`：包内候选词表；每条记录严格只有以下七个字段：
  `term`、`match_mode`、`include_patterns`、`exclude_patterns`、`target_cell`、`case_policy`、`test_fixture_ids`。
- `data/lexicon.schema.json`：对应的结构化 JSON Schema（运行时仍由标准库校验器执行正则和 cell_id 闸）。
- `fixtures/golden.json`：正例、反例、边界例；其中包含 SAP、HDI、BT、PCB 负样本。
- `fixtures/negative_samples.json`：四个高撞车缩写的独立负样本登记。
- `fixtures/corpus.jsonl`：可离线运行的最小语料样例。
- `dp4_lexicon/`：标准库实现。

## 匹配模式

`literal` 用转义后的词形匹配；`regex` 将 `term` 本身作为正则；两者都会执行 `include_patterns`（全部满足）和 `exclude_patterns`（命中任一即排除）。`context_any` 要求至少一个 include 命中，`context_all` 要求全部命中，`context_2_of` 要求至少两个 include 命中。每一个 include/exclude 都经过 Python `re` 编译闸。

裸 ASCII 缩写（例如 `SAP`、`HDI`、`BT`、`PCB`、`M6`）直接失败，不能仅靠上下文正则升级为合格词形；应改用短语。`mSAP` 是 `docs/04-词表.md` 明确允许的限定工艺词，作为唯一的当前例外。词形与 FAB1/FAB2、M1-M9、MSK、FLX、PM1-3、P1-9、EQ1-7 以及 M4/M6/M8 保留字冲突时直接失败。

## 用法

从仓库根目录运行：

```sh
PYTHONPATH=packages/dp4-lexicon python -m dp4_lexicon selftest
PYTHONPATH=packages/dp4-lexicon python -m dp4_lexicon validate
PYTHONPATH=packages/dp4-lexicon python -m unittest discover -s packages/dp4-lexicon/tests -p 'test_*.py'
PYTHONPATH=packages/dp4-lexicon python -m dp4_lexicon measure \
  --corpus packages/dp4-lexicon/fixtures/corpus.jsonl \
  --scope demo-corpus --date 2026-08-26 \
  --output /tmp/dp4-candidate-report.json
```

语料是 JSONL，每行一个 `{ "id": "...", "text": "..." }`。每个 `Measurement` 严格记录四键：`keyword`、`scope`、`date`、`hit_count`；命中数是匹配到的语料文档数，不是字符出现次数。碰撞报告另列同时命中两个以上候选词的文档和词对计数。

## 失败语义与人工裁决边界

非法正则、裸缩写、保留 cell_id 冲突、未知 target cell、重复词形或缺失 fixture 引用都会让验证失败。golden fixture 只验证机械行为，不把候选提升为事实。语料报告中的碰撞、零命中、负样本通过与否仍然是待核材料；歧义词的收弃、FAB/OUT 边界、研究范围和 canonical 写入必须由用户/人工判定闸处理。
