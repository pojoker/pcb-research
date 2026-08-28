# DP6 三态发布闸

DP6 是一个 Python 标准库、离线、机械校验器。它只读取一个 DP6 输入文档和一个独立的容差 ADR，不写入 canonical、docs、tree、graph 或其他 package。

状态只有三种：`pass`、`fail`、`indeterminate`。只有状态为 `pass` 的行 `publishable=true`；`fail` 与 `indeterminate` 永远不可发布。汇总优先级为 `fail > indeterminate > pass`。文本和 JSON renderer 都逐行原样输出状态，不会把 `indeterminate` 渲染成 `pass`。

## 运行

在仓库根目录：

```sh
PYTHONPATH=packages/dp6-publish-gate python3 -m dp6_publish_gate validate \
  --input packages/dp6-publish-gate/fixtures/valid_pass.json \
  --tolerance-adr packages/dp6-publish-gate/fixtures/approved_tolerance.json
```

机器可读报告包含每行的状态、原因码、比较值、比较口径、容差、容差锚、不可比原因、裁决日期和 `publishable`。退出码为 `0` 仅表示汇总为 `pass`；`1` 表示可解析但被拒绝或待判；`2` 表示文件/JSON 输入错误。

## 机械边界

- 量化推断行必须有主体、厂址、产品族、FAB、期间、metric、数值和单位、推导式、收入输入与锚、单价输入与锚、产能天顶与锚、海关适用域、证据等级和检索日期。缺列、未知列、重复 ID、NaN/Infinity 均为硬失败。
- 基准量化行固定为证据等级 `C`；情景行必须显式 `scenario=true` 且为 `D`，与基准行分离。包不把任何真实事实、容差或汇率写死。
- 只有人工核验的产销量表或建成产能自述可作为强锚；`approval_capacity` 是 weak ceiling，不能产生 `pass`。超出可比上限乘以 ADR 批准容差时为 `fail`。
- 比较必须在主体、厂址、产品族、FAB、期间、metric、单位、币种和合并口径一致时进行；不可比为 `indeterminate`。容差 ADR 必须独立传入、`status=approved`、有裁决人、日期、证据锚和匹配生效范围。
- HS 8534 只能做 `macro_only` 地区/行业校准。公司级或厂址级使用、橱窗单价循环换算为 `fail`；待核、宏观元数据不全、缺少内销证据为 `indeterminate`。
- recalibration 的实际值、误差、日期、单位、期间和公式必须全空或全有；半填、非有限数、单位/期间不一致或公式不一致为 `fail`。

## 文件

- `schema.json`：DP6 输入 JSON Schema。
- `tolerance-adr.schema.json`：独立容差 ADR JSON Schema。
- `fixtures/valid_pass.json` 与 `fixtures/approved_tolerance.json`：仅用于测试的通过样例；其中 `0.1` 不代表任何用户真实批准的容差。
- `fixtures/cases.json`：超天顶、缺锚、NaN/Infinity、单位/期间/主体不一致、未批准容差、弱上界、recalibration 反例描述。
- `fixtures/customs_cases.json`：8534 元数据缺失、待核、无内销证据、公司级使用、橱窗单价循环反例描述。

## 验收

```sh
cd packages/dp6-publish-gate
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 selftest.py
```

`selftest.py` 独立展开 fixture case 描述并检查所有三态与 renderer 不变量；它不依赖 canonical 或其他 package。
