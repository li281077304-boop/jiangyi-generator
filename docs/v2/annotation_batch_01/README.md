# Annotation Batch 01

本目录保存 Luna 在 2026-09-29 从 229 份 Stage1 StructDoc 样本中选出的首批 15 份人工结构标注基线。**S01–S15 是本批唯一正式样本编号。**

## 文件

- `样本清单.md`：15 份文档及逐份选择理由。
- `sample_manifest.json`：样本元数据、SHA256、选择理由、特征统计；`source` 相对于语料根目录，ZIP 样本另列 `member`。
- `标注模板.md`：空白模板；`annotations/` 下有每份样本的独立空白表。
- `人工标注操作说明.md`：标注尺度、块定位及操作顺序。
- `reference_dumps/`：只保留两个代表性 dump，分别示范多层数学专题和全文大表。其余 dump 可从源 DOCX/ZIP 重建，没有复制进仓库。
- `Luna基线与现有候选清单差异.md`：与另一 Agent 已重建候选清单的逐文件对比。

## 语料定位

原始语料根目录为 `C:\Users\Administrator\Desktop\工作\讲义生成器`。manifest 的 `source` 路径相对于该根目录；ZIP 内文档使用 `member` 指定。语料文件没有复制入仓库。其他机器可将该根目录映射到本地语料位置，并按文件名/ZIP member 与 SHA256 核对。

## 标注范围

只标目录/正文、章节边界与父子关系、完整题组、共享材料与题组的关系、答案/解析范围及 unknown。本批不标知识/例题/练习/巩固，也不包含已填写 Gold。
