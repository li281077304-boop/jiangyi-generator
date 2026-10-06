# V1.2 Final Product Closeout — 2026-10-06

## 结论

`V1_2_FINAL_CLOSEOUT_BLOCKED`。本轮四项限定修改已落地并通过定向自动测试；实际指定的教师/学生文件通过浏览器直传和 ZIP 输入均被识别为一对，但两种输入都以 `PRODUCT_REPEATED_BLOCK_SEQUENCE` 失败，没有产出可验收成品。检查发现指定文件来自用户成品目录，正文已经含有完整六模块模板与重复块，属于已生成成品再次作为原始输入。Product Integrity 正确拒绝递归生成。本轮未改 Product Integrity、Router 或模板原件，也没有构建 EXE/RC。

## 四项修改

1. `JobService.create_inputs()` 对两个 DOCX 调用现有 `resolve_batch()`，只在其解析为唯一 logical pair 时创建一个普通单任务；教师/学生文件序号沿 resolver 结果还原。
2. 第一页定位从“二、知识回顾”标题改为模板 row 5 中的模块二结束分隔线。仅调整分隔线前的既有空段，按模板分别定位；不改 frozen 模板、字号、页边距或页面尺寸。
3. display renumber 不再要求 `NO_KNOWLEDGE_POINT` 或 training-only。它依据 A-Line question-group 贡献块和最终 slot route 建立教师/学生共用 occurrence map，只在槽内展示题号非 `1..N` 连续时应用；表格值排除，跨题引用与不可编辑题号整体 fail-safe。
4. V0.9 runtime 的四个 PowerShell 调用统一经 `_run_hidden_process()` 执行；Windows 使用 `CREATE_NO_WINDOW` 与 `SW_HIDE`，保留原 stdout/stderr、timeout、return-code 参数。

## WPS 模板锚点测量

在 WPS 12.0 中对冻结模板副本执行打开并导出 PDF，定位到模块二结束分隔线（PDF 文本框 y1）：

- 1 对 1：分隔线位于第 1 页，y1 = `760.3 pt`；模块三标题从第 2 页开始。
- 班课：分隔线位于第 1 页，y1 = `740.1 pt`；模块三标题从第 2 页开始。
- 两份模板的第 1 页均保留模块一、模块二标题与结束边界。
- 证据 PDF：`C:\xml-uat\v12-final-closeout-20261006\1v1-21.pdf`、`C:\xml-uat\v12-final-closeout-20261006\class-22.pdf`。

这是模板锚点测量，不是实际讲义内容验收；事故样本未生成成品，因此教师/学生实际内容、目标重难点、答案处理及 WPS roundtrip 仍未通过。

## 真人浏览器提交证据

隔离源码服务：`http://127.0.0.1:5132`。表单按 `物理 / 九年级` 提交，未按文件名中的“高一 数学”设置。

- 直接同时选择教师版和学生版：job `1e285b712b724c4a948986329c2b8441`，resolver 识别为 `TEACHER_AND_STUDENT`、单个普通 job，教师/学生路径对应上传的两个文件。Renderer 尝试失败并进入 V0.9，最终被 Product Integrity 拒绝：`PRODUCT_REPEATED_BLOCK_SEQUENCE`。
- 同一对文件 ZIP 上传：parent `f4fc378021a24017ac382bd7b6a262e4`、item job `245bc727f95540658f08aa17dd488673`。ZIP 展开后仍唯一配对为 `TEACHER_AND_STUDENT`；Router 给出 `SLOT_ROUTING_AMBIGUOUS: unclassified section at b2: 六、巩固练习`，随后 V0.9 全任务结果同样被 Product Integrity 拒绝。
- 两次均没有 `done`、没有最终输出路径；原成品目录未发布新 DOCX。
- 输入 SHA-256：教师 `EFB5D7EAE68EA64821B62AA49C303BEA5A093EFDE8FEF1480001F62637976350`；学生 `EF59DD4A8A9921F2920D2A70654BA9ACEC288F78398A440168F0ABD6370B2C48`；上传 ZIP `C0C9A14FEAA79C46A978AD56F92366E2624E39C197087512D45CC77ECC34E6B5`。
- 输入位置均在 `D:\Documents\生成讲义结果\...` 下。作业 metadata 与输出结构进一步确认它们是已有成品而非干净原始 source。重复内容来自重新摄入完整成品；Product Integrity 在发布前阻断，没有形成新的套娃成品。

## 自动化与限制

- 定向 pytest：`58 passed, 6 subtests passed`，覆盖 final polish、normalizer、metadata、router、package validator、direct-pair JobService。
- `py_compile`：本轮 7 个 Python 文件通过。
- `git diff --check`：通过。
- WPS 页面定位只验证冻结模板的 spacer 定位；没有对实际最终讲义执行 `Open → SaveAs → Close → Reopen → PDF`。
- 尚未运行 JS syntax、相关 full pytest、Stage2/Stage3 回归、冻结资产哈希检查；由于真实内容 Gate 已失败，未进入 RC 构建条件。
- 没有生成 EXE 或 RC ZIP；没有 tag 或 GitHub Release。
- GPT-6.1 Sol final review 尚未完成。

## 唯一当前阻塞

指定的教师/学生文件已是生成成品，不能作为本轮要求的干净原始输入来证明 XML 主路径。它们包含模板模块/重复块；现有完整性门将其拒绝。需提供 immutable 原始教师/学生 source（或从原始资料重新选择文件）后，才能完成实际 XML、三槽、编号、答案和 WPS 成品验收。不能把这两份成品再次作为输入并宣称 closeout PASS。

## Git 与独立评审

- 修复代码 commit：`8935e2f886b45ef5e4e834da167bd60d017a6d26`；已推送，推送后 local HEAD 与 remote HEAD 一致。
- 本轮运行环境没有提供可确认的 GPT-6 Luna worker 身份；实现由当前 Codex GPT-6 continuation 执行，不冒报 Luna。
- GPT-6.1 Sol final review 未进入：真实产品 Gate 在指定输入阶段失败，且没有符合条件的最终候选 EXE。
