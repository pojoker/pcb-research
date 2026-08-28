# PCB 主张—证据知识图谱

本目录用于回答两个不同问题：PCB 的通用结构与机理是什么；公开证据能否支持或证伪“PCB是什么”讨论中的具体陈述。它不把通用工程规律自动升级为 NVIDIA 或其他具体产品的采用事实。

## 文件

- `manifest.json`：文件 schema、枚举和讨论覆盖范围。
- `concepts.csv`：概念节点，不承载真假判定。
- `claims.csv`：可证伪原子主张及当前 verdict。
- `evidence.csv`：一手来源披露件及可定位短摘录。
- `claim_evidence.csv`：`supports/refutes/limits/context_only` 证据边。
- `knowledge_edges.csv`：概念间关系，每条边由一个主张承重。
- `open_questions.csv`：公开不可验或待核主张缺什么证据才能重开。
- `search_log.csv`：开放问题的一手来源检索协议、候选命中和适用域不足记录；负向检索不等于反驳。
- 根目录 `tree.yaml`：PCB 物理格、技术路线轴和需求侧骨架。
- `docs/research/2026-08-28-pcb-claims-primary-sources.md`：本轮一手来源逐命题核验底稿。

## 当前快照

- 40 条讨论主张已全部原子化：31 条支持、3 条部分支持、5 条公开不可验、1 条分析标注、0 条待核。
- 25 份一手来源通过 49 条证据关系承重；证据关系与概念关系分表保存。
- 5 个公开不可验命题均有重开条件，覆盖价值量排名、技术难度排名、midplane 净价值量、NVIDIA 板级制造参数和 Rubin PCB 制造 KPI。
- 讨论中的星级评级归入 `analyst_annotation`；它不是公开事实评级，不会进入事实结论。
- 6 个开放问题均有检索协议记录；5 个一手来源候选因适用域不足未改变 verdict，星级评级的会话溯源记录为无公开量表。

## 判定纪律

1. `supported` 至少需要一条适用域匹配的 `supports` 边。
2. `refuted` 至少需要一条 `refutes` 边；“没有找到”不能构成反驳。
3. `partially_supported` 必须同时有支持边和限界/反驳边。
4. `publicly_unverifiable` 必须进入 `open_questions.csv`，写明缺失证据与重开条件。
5. `application_observation` 或 `application_inference` 主张若要判 `supported`，必须有具体产品一手来源且 `scope_match=exact`；通用标准只能提供背景。
6. `does_not_imply` 是正式知识边，用来阻断从前提到过宽结论的自动升级。
7. `analyst_annotation` 只能搭配同名 claim class；校验器禁止把它改写为事实裁决。
8. `search_log` 只记录检索覆盖与候选披露；`no_candidate_found` 不得自动改变 claim verdict。

运行 `python3 scan.py --check` 校验 schema、ID、端点、证据边、适用域和讨论命题覆盖。
