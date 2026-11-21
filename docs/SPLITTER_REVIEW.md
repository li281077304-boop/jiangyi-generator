# 离线 Splitter 复核

从已有评估目录生成审查摘要和可填写的逐块清单。仅需 Python 3.9+ 标准库，可在断网环境运行。输入来自 `tools/splitter_assessment_20261025.py`，包含 `report.json` 和每个样本子目录内的 `assessment.json`、`source_dump.json`、`1v1.json`、`class.json`。工具按总报告的样本顺序读取，核对总报告、样本记录和两份模板记录的副本。源文件路径、manifest、DOCX 和网络都不参与处理。

在仓库根目录运行。输入须是一次已有评估，输出须是输入目录以外、尚不存在的新目录。

```sh
python3 tools/splitter_review.py local-run local-review
```

| 本机产物 | 用法 |
|---|---|
| `review_summary.md` | 先看统计，再按样本和模板查看哈希状态、槽位及块 ID、异常、风险和短摘要 |
| `review_summary.json` | 查看记录的各项 SHA-256、每个物理块的归属、未归类与重复/遗漏证据 |
| `review_checklist.csv` | 每个已识别源块在每种模板各占一行。对照原稿，在 `human_decision` 填目标槽位、保留封面或待定，在 `notes` 记下原因和逐题对应情况 |

退出码 0 表示已生成复核包且程序检查无异常，含正常降级和待人工核对项；1 表示已生成复核包且至少一个组合的证据有异常或不足；2 表示无法建立审计输入清单或写出整包。纠正损坏的输入请回到评估环节；再次运行时指定新的输出目录，以免覆盖已有批注。摘要、原始异常消息和人工判定可能含私有材料，请将真实资料的复核包保存在本机。

## 读数与人工判定

- **计数单位**。`samples` 按样本 ID 计数。其余计数都按样本 × 模板计数，一个组合只计一次。`plans_created` 按模板文件声明的计划状态计数，即使另有证据异常也能追查这项声明。`rule_paths` 含 NAVIGATION、SEMANTIC 和 RULES。`partition` 单列按题组比例分配的组合。`preserved` 仅计 PRESERVATION，其物理槽位只说明原文放置位置。
- **程序检查**。哈希核对使用评估器记录的预期、读取前、快照、转储、模板证据及读取后摘要。不同有效值或源变更标记为 `failed`，一致但缺证据为 `unknown`。物理检查核对源块 ID、计划索引和各槽记录。`verified` 的范围限于报告中的这条证据链。合法封面元信息有物理记录和排除原因，人工清单保留该行。
- **降级与材料风险**。PARTITION 要复核例题及训练比例；PRESERVATION 要重新判定教学归属。公式、OLE、图片应对照原稿检查。原稿分析或模板计划报错时，记录已有的异常原因；缺转储时无法给出该源的逐块清单。
- **人工进度**。`pending_review` 包括无可用计划的组合，本工具未导入任何人工判定。`rows_with_findings` 只计存在异常或证据不足的组合。结构标注覆盖章节、题组、材料与答案范围，未提供知识、训练、巩固的独立金标。教师与学生原稿独立评估，逐题对应仍须人工核对。报告不计算教学分槽准确率。

## 合成示例

查看[合成审查报告](../examples/splitter_review/synthetic_review.md)和[可填写的示例清单](../examples/splitter_review/synthetic_checklist.csv)。S01 的一对一模板有三个教学槽，班课模板的 PRESERVATION 路径把三个正文块保留在同一物理槽，两种模板均待人工判定。以下命令可重新生成相同的报告和清单。请在示例目录不存在时运行。

```sh
python3 examples/splitter_review/make_example.py demo-run
python3 tools/splitter_review.py demo-run demo-review
```

一次评审可先在 Markdown 点查异常块，再到 CSV 中按 `sample_id`、`template`、`block_id` 定位同一行。两个模板可以给出不同的人工判定。保留原来的槽位和路径字段，方便后续对照。

限定测试：

```sh
python3 -m pytest -q tests/test_splitter_review.py
```
