# NVIDIA PCB 公开不可验问题：第二轮一手来源核查

日期：2026-08-28
范围：`graph/open_questions.csv` 的 Q-001 至 Q-005；仅核查可由来源所有者直接公开的材料。
结论：**五项均不能解除“公开不可验”状态。** 本轮增加了可承重的架构与生产状态事实，但没有得到逐板 BOM、同口径工程参数、特定板卡材料/工艺，或 PCB 级制造 KPI。

## 方法与准入边界

检索限定为 NVIDIA 官方文档、技术博客、投资者关系/SEC 原文，以及标准组织或潜在供应商的官方技术/IR 原文。检索引擎只用于发现候选，不把搜索摘要、媒体、券商、转载、传闻或拆机转述作为证据。

每一项按下列门槛判断能否关闭：

| 问题 | 解除公开不可验所需的最低材料 |
|---|---|
| Q-001 | 同一 GB300 系统边界下每块 PCB 的数量、外形/面积、层数或可比价值量，以及采购价/可复核计价口径 |
| Q-002 | 至少两类 GB300 板卡的相同工程维度：通道/损耗预算、stack-up、线宽线距、层数/HDI、可靠性和良率；并先定义“技术要求最高”的评分规则 |
| Q-003 | Rubin 相对前代的新增 midplane 与被替代连接件/线缆的系统 BOM 及成本差额，且口径一致 |
| Q-004 | 可定位到 NVIDIA 产品和具体板卡的 stack-up、材料牌号、铜箔、HDI/微孔或截面/Gerber，且来源能说明供货/采用关系 |
| Q-005 | Rubin PCB 的良率、成本、供应商覆盖和设计余量的产品级披露；至少须有 SKU/板卡/期间/指标定义 |

本轮也执行两个防误判门槛：

1. 供应商说“参与 AI 服务器”或提及 NVIDIA 的市场趋势，**不等于**供货 GB300/Rubin 的某一块 PCB、CCL 或铜箔。
2. 专利可证明申请人公开过一种技术方案，**不等于**该方案已被 GB300/Rubin 量产采用；若无产品、SKU、BOM 或量产资格记录，不能用于关闭 Q-003/Q-004/Q-005。

## 一手来源索引

| ID | 来源所有者与材料 | 直接链接 | 本轮可用范围 |
|---|---|---|---|
| S1 | NVIDIA，GB300 NVL72 Enterprise Reference Architecture：System Hardware & Components | [官方文档](https://docs.nvidia.com/enterprise-reference-architectures/nvl72-ai-factory/latest/components.html) | GB300 tray、器件、网络与背板互连架构 |
| S2 | NVIDIA，DGX SuperPOD GB300 Reference Architecture | [官方 PDF](https://docs.nvidia.com/pdf/dgx-spod-gb300-ra.pdf) | GB300 compute/switch tray、线缆 cartridge、端口与系统组成 |
| S3 | NVIDIA，ConnectX-8 SuperNIC User Manual：Specifications | [官方文档](https://networking-docs.nvidia.com/connectx8hw/specifications) | ConnectX-8 速率、C2M/PCIe 接口和公开规格边界 |
| S4 | OIF，Common Electrical I/O (CEI)-224G 项目说明 | [原始标准组织页面](https://www.oiforum.com/technical-work/hot-topics/common-electrical-i-o-cei-224g/) | 224G 电接口的标准化技术背景，不是 GB300 板卡资料 |
| S5 | NVIDIA，Vera Rubin POD 技术博客 | [官方技术博客](https://developer.nvidia.com/blog/nvidia-vera-rubin-pod-seven-chips-five-rack-scale-systems-one-ai-supercomputer/) | Rubin midplane、tray 组装时间、铜缆 spine 和系统组成 |
| S6 | NVIDIA，Vera Rubin full-production 新闻稿 | [官方 IR 新闻稿](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Vera-Rubin-Ramps-Into-Full-Production-to-Power-Agentic-AI-Factories-Worldwide/default.aspx) | Rubin 平台/系统生产爬坡和生态范围 |
| S7 | NVIDIA，FY2026 Form 10-K | [SEC 原文](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) | 聚合制造/供应链/成本构成及风险，非 SKU/板卡 BOM |
| S8 | GCS，2025 Q3 investor presentation | [来源方 IR 原文](https://gcsincorp.com/pdf/Investor_PresentationQ3_2025.pdf) | 仅作“供应商/市场演示不可替代产品归因”的反例；该页没有声明 GCS 供货任何 GB300/Rubin 板卡 |

## Q-001 — CLM-026

**原主张**：Compute Tray 是 GB300 中 PCB 面积、板数量或采购价值量最大的部分。
**本轮判定**：仍为 **公开不可验**；不能解除。

**Resolution: No resolution.**

### 检索范围、关键词与路径

- NVIDIA Docs：`GB300 NVL72 compute tray BOM`、`PCB`、`board count`、`board area`、`layer count`、`cost`、`purchase price`。
- 路径：GB300 Enterprise RA 的 *System Hardware & Components* 与 *Appendix B / Node Configurations*；DGX SuperPOD GB300 的 compute tray、switch tray、cable cartridge、power shelf 各节。
- 监管原文：NVIDIA FY2026 10-K 的 `board and device costs`、`cost of revenue`、`manufacturing`、`supply`。

### 找到的候选来源与承重范围

- S1 直接披露每个 compute tray 有 4 个 B300 GPU、2 个 Grace CPU、2 块 ConnectX-8 mezzanine board、1 个 BlueField-3 DPU；每机架有 9 个 switch tray，每 tray 有 2 个 NVSwitch ASIC。它可以承重“compute tray 与 switch tray 是不同的系统单元，并可据此建立待调查清单”。它**不能**给出这些器件位于多少块 PCB、各板外形、层数、面积、采购价，或某一类在全机架中的 PCB 价值量排名。
- S2 进一步给出 18 个 compute tray、9 个 switch tray、后部 cable cartridge 与端口/连接器说明。它可以承重“GB300 有已公开的系统组成和连接边界”，仍不能把 tray 等同为单一 PCB，更不能计价。
- S7 说明成本收入中包含 `board and device costs`、制造支持成本、最终测试良率损耗、存货和保修准备等聚合项目。它可以承重“板和器件成本在公司级成本口径中存在”，但不按 GB300、tray、PCB 或供应商拆分，不能用来计算或排序。

### 是否足以解除公开不可验

否。已知 18/9 tray 数量、器件数量和部分线缆数，不是 PCB 面积/数量/价值量。把器件数、tray 数或连接器数加总为 PCB 价值量，会混入封装、散热、电源、线缆、连接器、组装和测试，并改变比较口径。

### 仍缺的材料

至少需要 NVIDIA/OEM 的产品级 BOM，或可复核的整机服务料号/装配图，明确每块板的数量、尺寸、层数和 SKU；再配套该系统边界内的采购单价、合同价格区间或经审计的成本拆分。若采用拆机数据，须有可复核样机、板卡标识、尺寸测量与可重复加总规则。

## Q-002 — CLM-027

**原主张**：NVLink/NVSwitch 或高速网络 PCB 是 GB300 中技术要求最高的板。
**本轮判定**：仍为 **公开不可验**；不能解除。

**Resolution: No resolution.**

### 检索范围、关键词与路径

- NVIDIA Docs：`GB300 NVSwitch tray copper backplane`、`ConnectX-8 800G`、`C2M`、`signal integrity`、`stack-up`、`insertion loss`、`trace`、`via`、`yield`、`reliability`。
- 路径：S1 的 NVLink switch tray / compute networking 小节，S2 的 compute-tray block diagram 与 cable-cartridge 小节，S3 的电气接口与公开规格说明。
- 标准路线：`224G PAM4 PCB channel`、`CEI-224G`；用 S4 仅定义可比较的高速电接口背景，不把标准要求归因给 GB300 的任一 PCB。

### 找到的候选来源与承重范围

- S1 披露 GB300 每 GPU 有 18 条第五代 NVLink、通过铜背板连接到机架内 NVSwitch；compute tray 内的 ConnectX-8 为 800 Gb/s 量级，并在 baseboard 上集成。它可以承重“这些路径确实是高速/高带宽系统路径”，不能承重其 PCB 的层数、走线长度、损耗、材料、HDI、可靠性或良率，也没有与其它板卡同口径的比较。
- S3 披露 ConnectX-8 支持的速率和 C2M/PCIe 接口，并明确完整电气与热规格需要通过 NVOnline 或 NVIDIA 代表获取。它可以承重“公开资料本身并非完整 channel design package”；它不能把某个 ConnectX-8 产品规格直接变成 GB300 baseboard、mezzanine 或 NVSwitch tray 的 stack-up。
- S4 对 224G 电接口的工作范围包括至 500 mm PCB 和至多一个连接器的 medium-reach 目标。它可承重“高速电接口需要按通道长度、连接器与信号制式建立比较维度”。它不是 NVIDIA 产品规范，也不披露 GB300 是否采用此 IA、采用何种通道预算或材料。

### 是否足以解除公开不可验

否。速度或链路角色不能自动定义“技术要求最高”。至少必须先锁定评价函数，例如：每通道损耗/裕量、最大层数、最小线宽线距、HDI 阶数、背钻/阻抗控制、热/功率密度、可靠性与制造良率的加权规则；然后取得同一 GB300 代际、至少两类实际板卡的原始输入。当前来源只有系统逻辑和部分接口速率。

### 仍缺的材料

NVIDIA/OEM 的板级 SI/PI 设计规范、stack-up 与材料表、通道/损耗预算、fabrication drawing、可靠性验证要求和量产良率；或经同一主体确认的两类板卡的完整可比工程数据。单一 CCL/PCB 厂的通用产品 datasheet 只能提供 context，不可用于排名。

## Q-003 — CLM-034

**原主张**：增加 PCB midplane 必然提高整个系统 PCB 净价值量。
**本轮判定**：仍为 **公开不可验**；不能解除。

**Resolution: No resolution.**

### 检索范围、关键词与路径

- NVIDIA 官方：`Rubin PCB midplane`、`cable-free compute tray`、`assembly time`、`cable cartridge`、`BOM`、`cost`、`cost of revenue`。
- 路径：S5 的 Vera Rubin NVL72 compute/NVLink switch tray 小节；S7 的成本及制造披露。
- 专利路线：以 `NVIDIA` 申请人为范围，组合 `Rubin`/`GB300`/`midplane`/`cable cartridge`/`printed circuit board` 检索。没有将专利作为量产或成本证据：即使找到结构相似的申请，也没有能够将其定位到 Rubin 商品化 midplane、替代件清单和生产采用记录的材料。

### 找到的候选来源与承重范围

- S5 明确称 Rubin compute tray 使用 PCB midplane，把两套 Vera Rubin superchip 连接到前部的 8 个 ConnectX-9 SuperNIC 和 1 个 BlueField-4 DPU；并称 tray assembly 从近两小时降至五分钟。它可承重“midplane 是该 tray 的真实架构要素，且官方宣称带来装配/可维护性改善”。
- 同一 S5 同时披露 NVLink spine 仍有 4 个 cable cartridge、约 5,000 根铜缆。这能证伪“增加 midplane = 整机所有线缆都由 PCB 替代”的扩展说法，也提醒系统价值变化必须在完整系统边界下计算。
- S7 的公司级 `board and device costs` 与供应链风险只能说明成本项目存在；没有 Rubin 的新增 midplane 成本、被替代的线缆/连接件/其他 PCB 成本，不能得到净差额。

### 是否足以解除公开不可验

否。中板存在、装配时间缩短，甚至系统仍保留大量铜缆，都不能推出 PCB 总价值的正/负方向。`价值量`须至少扣除被替换的部件、连接器、线缆、其他 PCB 变化和组装测试差异；`必然`还要求在不同配置下都成立，公开材料没有该证明。

### 仍缺的材料

同一系统边界内的 Rubin 与前代可比 BOM/报价/成本拆分：midplane 的数量、尺寸、层数、材料、制造和测试成本；被替代线缆、连接器、旧板卡及装配工时的对应项目；以及配置、币种、期间、数量级和会计/采购口径。若是专利，仅在与量产 SKU、工程变更单或出货认证明确对应时才能作为辅助结构证据。

## Q-004 — CLM-035

**原主张**：NVIDIA 特定板卡已经采用指定低 Df 材料、HVLP 铜箔、特定 HDI 微孔层数或厚铜。
**本轮判定**：仍为 **公开不可验**；不能解除。

**Resolution: No resolution.**

### 检索范围、关键词与路径

- NVIDIA Docs/IR：`GB300 PCB`、`Rubin PCB`、`stack-up`、`Gerber`、`cross section`、`low Df`、`HVLP`、`copper foil`、`microvia`、`HDI`、`thick copper`、`supplier`。
- 路径：S1/S2 的 GB300 tray 与背板资料，S5 的 Rubin midplane 资料，S6 的供应链/量产公告，S7 的制造及供应链披露。
- 供应商排查：以潜在 PCB/材料公司的官方 IR/技术资料为范围，组合 `NVIDIA`、`GB300`、`Rubin`、`M8`、`low Df`、`HVLP`、`midplane`、`qualification` 与具体产品名检索；只接受同时给出产品/板卡识别和供货/采用关系的材料。

### 找到的候选来源与承重范围

- S1/S2 能确认 GB300 采用铜背板/线缆 cartridge、compute/switch tray 的系统构成和接口，但不公开 stack-up、铜箔类型、介质牌号、微孔统计、铜重、Gerber 或截面。它们只能支持“这些板级资料在所核查的 NVIDIA 系统文档中未披露”，不能证明这些工艺没有采用。
- S5 能确认 Rubin compute tray 的 *robust PCB midplane* 与连接对象，但仍未披露层数、材料、铜箔、HDI、制造商或料号。它只能支持 midplane 的存在和功能范围。
- S6 列出大量系统制造商及生态伙伴，S7 列出部分晶圆、存储、封装和代工关系；二者都没有把 PCB/CCL/铜箔供应商映射到 GB300/Rubin 的具体板卡。因此“生态参与者名单”不是板卡材料认证或供货清单。
- S8 的来源方 IR 仅把 GB200/GB300 作为 CSP 部署目标、并展望 Rubin 平台转换；该页没有声称 GCS 供货某一 NVIDIA 板卡，也没有列层数、材料或认证。它是一个合格的来源方原文，却恰好说明“提到 NVIDIA AI 服务器”不足以完成产品归因。

### 是否足以解除公开不可验

否。不存在可把“材料/工艺参数”与“指定 NVIDIA SKU + 指定板卡 + 供货/采用关系”同时闭合的一手来源。通用 CCL 与铜箔性能资料、供应商对 AI 服务器的市场宣称、或专利中的可选实现，均只能是 context；不能将 M8、低 Df、HVLP、任一 HDI 阶数或厚铜写成 GB300/Rubin 特定板卡事实。

### 仍缺的材料

优先级从强到弱如下：

1. NVIDIA/OEM 发布的 board fabrication drawing、stack-up、物料表、维护料号/工程变更文件或经授权的截面资料；
2. PCB 厂/CCL 厂的官方年报、监管申报或客户认证公告，明确写出 NVIDIA 产品代际、板卡名、材料牌号与供货状态；
3. 双方可交叉验证的料号、订单/交付或产品认证，且能排除“样品/送样/通用平台兼容”。

## Q-005 — CLM-038

**原主张**：Rubin 量产状态不能单独证明 PCB 良率高、成本成熟、供应商广泛或性能余量充足。
**本轮判定**：仍为 **公开不可验**；不能解除。

**Resolution: No resolution.**

### 检索范围、关键词与路径

- NVIDIA IR/SEC：`Rubin full production`、`ramp`、`yield`、`board cost`、`PCB supplier`、`supplier coverage`、`design margin`、`reliability`。
- 路径：S6 的生产公告；S7 的 Manufacturing、Risk Factors、Cost of revenue；S5 的 Rubin 组装/架构披露。
- 判定方式：把“已量产”与四个独立制造 KPI（PCB 良率、成本成熟、供应商覆盖、性能/设计余量）逐一比对，不把平台或系统级宣传语自动投射到单一板卡。

### 找到的候选来源与承重范围

- S6 表示 Rubin 正在进入 full production，全球供应链领导者和系统制造商在规模化制造，并列出多类系统、基础设施软件和存储伙伴。它可以承重“Rubin 已超过概念阶段，至少有系统级生产爬坡/制造活动”。它没有 PCB 良率、单位成本、PCB 供应商名单/份额或设计余量的指标定义与数值。
- S5 说明该架构有 18 个 compute tray、9 个 NVLink switch tray、PCB midplane 与大量铜缆；它能承重“系统复杂度和架构范围”，不能披露任何 PCB 制造 KPI。
- S7 说明 NVIDIA 依赖第三方供应商、合同制造商和其原材料采购；同时把低制造良率、质量与交期作为一般经营风险，并在公司级成本中纳入 board/device costs 与最终测试 yield fallout。它能承重“公司层面仍把供应、质量、良率和成本视为风险/成本因素”，但没有将任一指标归属到 Rubin PCB，也没有供应商覆盖率或性能余量数据。

### 是否足以解除公开不可验

否。生产爬坡是存在制造能力的正面事实，但它不是良率、成本、覆盖或余量的量化代理。尤其是公告中的“数百合作伙伴/数百工厂”是平台/生态范围，不能当作 PCB 供应商数、合格覆盖率或第二来源比例。公开资料不能证明四项 KPI 为真，也不能量化其反面；因此不能单靠“公告没有数值”把任何一项写成确定事实。

### 仍缺的材料

需产品级、期间明确的原始披露，例如：PCB 厂或 OEM 的良率/一次通过率、报废/返工、产能爬坡、单位成本或毛利影响、已量产供应商及份额/认证状态、SI/PI/热设计的验证余量与失效标准。至少要能定位到 Rubin 的系统、板卡或料号，而不是泛称“AI 服务器”“NVIDIA 平台”或“生态伙伴”。

## 结论与图谱处理建议（不修改图谱）

| 问题 | 本轮新增的可承重事实 | 是否解除公开不可验 | 不能跨越的边界 |
|---|---|---|---|
| Q-001 | GB300 的 tray/器件/连接架构与公司级成本类别 | 否 | tray/器件数量 ≠ PCB 面积、板数或价值量 |
| Q-002 | GB300 高速路径、ConnectX-8 接口速率与公开规格边界 | 否 | 链路速率/功能 ≠ 板卡难度排名 |
| Q-003 | Rubin midplane、装配时间变化及仍有约 5,000 根铜缆 | 否 | 架构或工时变化 ≠ 系统 PCB 净价值量 |
| Q-004 | 特定板级工艺数据未见于核查的 NVIDIA 系统资料；供应商市场提及不构成归因 | 否 | 通用材料/供应商宣传/专利 ≠ 某 NVIDIA 板卡量产采用 |
| Q-005 | Rubin 系统生产爬坡、平台生态和公司级制造风险 | 否 | 系统量产/伙伴数量 ≠ PCB 良率、成本、覆盖或余量 |

因此，Q-001 至 Q-005 的当前状态应保持 `open`。这不是“尚未找到”的软结论，而是由各问题要求的最小证据单元与现有公开单元之间存在明确缺口所致；后续只有出现上述“仍缺的材料”类型的一手披露，才应重新开启对应主张的判定。
