# V1.2 产品抢救：实测测试包与未通过项

状态：**QA_TEST_PACKAGE_AVAILABLE / RELEASE_BLOCKED**。P0 网页恢复实测通过，已交付真实 XML 成品；没有宣称整个产品、完整回归或所有兼容成品通过。

工作分支 `feature/v1.2-c4-release-engineering`；main 未修改、未合并。生产代码起点 `ca5e825d4b43e7359d7c42a948c1bd29548a27a1`。P0 `9c646b4`、自动 XML 路径 `6cdbff1`、内容拦截 `3a76f9a`、中文失败说明 `6b426d6` 均已提交推送并逐次核对远端。

## 可运行成品

- 当前 Windows 入口：`C:\Users\Administrator\Desktop\讲义生成器 V1.2 当前测试版 20261008\讲义生成器\讲义生成器.exe`。
- ZIP：`D:\讲义生成器测试包\20261008\讲义生成器_V1.2_产品抢救安全测试版.zip`。
- build commit：`6b426d642ef77dde0b626cd8d01724c8eb5ef32c`。后续测试工具/报告提交不改变该包的代码来源。
- EXE SHA-256：`aeb483a0755de8dfa54fb92ab3b81ab4ee6c73b706103099f0cc5612899403a3`。
- ZIP SHA-256：`86b47e9fc72a481cab644a2310b4886011abc4da91b69a0cc5ea3ffd30ef4a35`。
- ZIP：133,641,424 bytes；onedir：1,274 files / 288,181,750 bytes。
- 打包说明已同步自动XML和教师单文件安全策略，未保留旧的手动引擎选择说明。只更新包外README/manifest；运行代码与已测6b426d6一致。
- 独立 PyInstaller onedir，自带运行时、OCR 模型、模板及冻结兼容内核；`console=False`。无 repo/开发虚拟环境依赖。包审计排除测试语料、Golden、用户讲义、开发日志、Git 和虚拟环境。
- EXE 本身的 hash 不能代替整个 onedir 的版本检查：应用部分以资源文件加载。完整文件清单及 SHA 在 ZIP 的 package manifest、外部 `RC_PACKAGE_REPORT.json` 中。
- 先前 `6cdbff1` 测试包不应再用于内容安全验收，本报告指定的新包包含文本框完整性拦截。

## P0：实际 EXE / Playwright

最终包解压到中文桌面目录，通过正常 launcher 启动，使用隔离 LOCALAPPDATA 保存测试任务；不是源码 Flask 代替 EXE。页面 200、自动打开浏览器、无缺失模块。未用桌面鼠标自动化。

实际一对一 incident pair：提交后刷新恢复 queued/running；浏览器 offline；重连失败有中文反馈；后台继续完成；恢复网络后按钮恢复任务；完成后刷新、重开标签仍保留任务；`/api/open` 真正打开 D 盘成品目录。最终 XML teacher/student 两份，package valid，page errors=0。

班课通过实际网页执行：过去 XML 失败的化学原卷/解析 pair、teacher-only、student-only、中文嵌套目录 ZIP + corrupt item。前三项 done，ZIP partial；有效 item 的两份文件完整落盘，损坏 item 单独失败。teacher-only 未证明安全去答案时只产教师版并警告，不冒充已生成学生版。

界面没有引擎选择；普通提交固定自动路径。内部诊断参数保留，未向用户提供选择。两份输入各自渲染、各自 metadata，警告逐题对应未经验证；不执行不可靠双版本重编号。教师正文不复制进学生源。

最终中文拒绝案例：氧气 pair / 1v1，job `a2b6d9658b17487ab5fa9bf3f59e4b5d`。XML 因 `UNSUPPORTED_BOOKMARK_SCOPE` 技术拒绝，V0.9 生成后内容检查未通过，job=error、has_result=false、output_paths=[]。页面解释文本框正文未完整保留；刷新后仍显示原因。没有把无效成品发布到用户目录。

原始日志：`C:\xml-uat\product-rescue-safe-20261008\browser-final-p0.log`、`browser-final-core-class-retry.log`、`browser-final-content-refusal.log`。结构化证据：`fixtures/product-rescue-20261008/safe_exe_browser.json`。

保留一条真实环境失败：首个最终班课请求500，C盘仅4,849,664 bytes空闲，未创建有效job.json，内部第二输入文件为0 bytes。没有把该提交算成功。打包缓存删除被自动审批拒绝，改为将本轮可重建缓存和旧包完整移至 `D:\xml-uat-recovery-cache` 保留；原始corpus和用户成品未动。空闲恢复后同一网页四案例成功。没有捕获原始ENOSPC异常堆栈，因此不声称已证明具体errno；证据明确表明严重磁盘空间压力。低磁盘空间时目前API仅通用失败说明，尚缺更具体提示。

## P1：实际调用链

`NAVIGATION → SEMANTIC → RULES → PRESERVATION → 技术失败才 V0.9`。均复用已存在的 importer/composer；未继续 canonical_pair_alignment、module-sync、OCR 或 OOXML 扩能力。

无法可靠分槽时，原始主体作为整体按源顺序进入模板；保留原题号，不危险拆分。产品规范化及 package/完整性检查在两种 renderer 后共同执行。无法安全去答案不调用未经证明的 make_student；teacher-only 可只交教师成品。

冻结 X017/X018 化学 pair 原先 `ALIGNMENT_UNRESOLVED`，现已在两种模板通过真实 EXE 交付 XML 两份，参考 `final_exe_browser.json`、`safe_exe_browser.json`。这不是逐题对齐已证明，也不是全部智能分槽成熟。

## 冻结 33 专题统计：不隐藏分母

manifest SHA-256：`c3efed7b9cd135f4b45c7092d9070013878badfcddc08ee872a2b06a9b6273b1`。13 fixed + 20 additional，全部提交；teacher/student 同专题不重复计专题。

主要路径测量代码 `6cdbff1`，随后安全检查针对全部 254 份 corpus 输出复核；没有伪称新包重新跑了整套 33 专题。

| 测量 | XML | 兼容 | 拒绝/失败 | 分母 |
|---|---:|---:|---:|---:|
| 冻结标准 pair / 1v1 | 22 | 10 | 1 | 33 |
| 冻结标准 pair / class | 22 | 10 | 1 | 33 |
| 独立原始 DOCX × 两模板 | 94 | 40 | 0 | 134 |
| 最初全部成员 envelope | 132 | 60 | 6 | 198 |

pair XML：22/33=66.67%，两模板相同。单文件 XML：47/67=70.15%（94/134）。初始 pair 两模板交付 32/33=96.97%，但**这是生产 done/文件落盘统计，不是完整内容验收通过率**。

一个专题有原卷、答案、解析三份：三成员 pair 被正确拒绝为角色歧义；按冻结历史 X021/X022 pair + 三份分别上传补测 8/8 XML，原始 envelope 失败仍保留在报告中。总原始记录 198 + 8 =206，不混同标准 pair 的 66 次。

一个几何大文件 pair 被拒绝：`DOCX 展开大小超过安全上限`；teacher/student 单独提交均成功。不能删去 pair 的拒绝记录。

XML 输出角色使用层级：NAVIGATION 24、SEMANTIC 148、RULES 4、PRESERVATION 8；这是角色次数，不是专题数。兼容提交 60 次：

- 6 次 `UNSUPPORTED_BOOKMARK_SCOPE`，exact detail：bookmark 18 missing/ambiguous（4），bookmark 25（2）。
- 54 次 `XML_RENDER_FAILED`：`ProjectionError: unknown StructDoc block kind at b1: unknown`，来自后部 9 个物理专题。

全部逐专题原因、原始 job、路径和 SHA 见 `coverage_final.json`、`corpus_submissions.json`。corpus harness 对含混文件名默认物理，部分封面测试参数不正确，因此其统计只能证明生成路径；不用于学科识别/封面串档验收。实际代表网页测试明确选择物理或化学、九年级。

### 新完整性检查后的差异

254 份旧产物中，2 份 oxygen /1v1 教师版（pair 一份、teacher-only 一份）含未保全文本框段落。新增 gate 会拒绝这两份，XML 数不变。该复核意味着标准 pair /1v1 的可通过当前静态检查记录由 32 降为31；class 仍32；两模板共同可通过31/33。它是既有文件复核，**不是新包 33 专题实时重跑或语义正确率**。

## 成品内容与 WPS

代表 XML 八份（incident/化学，两模板，teacher/student）和正确化学封面兼容两份完成 WPS `Open → SaveAs DOCX → Close → Reopen → PDF`。实际看过首页、主体、实验表格/图片和尾部渲染。另两份测试参数误设物理的历史兼容记录单独保留，不算封面验收。

结果仍有空模块占位、较大首页留白、稀疏或仅分隔线尾页；兼容1v1标题仍有旧样式。这些限制没有被包装成成品精修 PASS。图片、表格和公式的代表页可见；抽检学生页未发现从教师源复制答案，但不宣称134单文件全部答案隔离人工验证。

内容测量：EXE16份代表输出无长正文缺失、引用图片 hash 缺失、OLE 缺失；corpus254份零 OLE 缺失。12份兼容输出存在图片 hash 变化：已看过一个92×92→42×42数字徽标，属于缩放/重编码；没有逐一证明全部变更资源视觉等价。

长段落测量标记26份输出：16 XML 来自原文目标/重难点在封面预算下缩写，完整字段保留 job metadata；其余兼容标记大多是 AlternateContent/祖先段落重复拼接。最终12个未证明段落标记全部对应上述2份教师产物（含重复提取）。原始提醒确实遗漏：原稿 WPS PDF第3页存在，兼容教师PDF第5页实验表后没有它；不是仅凭字符串扫描认定。

新 `PRODUCT_TEXTBOX_CONTENT_UNPROVEN` gate 检查唯一叶段落≥40字符，发布前拒绝无法核验保留的正文；允许文本框文字转入正文。仅有图像化文本也不声称证明安全。冻结 Writer 未改，未删除旧证据/已完成 siblings。

## 回归：未宣布 full PASS

- 当前内容/UI定向：31 passed；新增生产拦截关联检查10 passed（有重复测试，不相加虚报唯一总数）。此前 P0/job/launcher：60 passed +一次 WinError5；该项隔离重跑1/1通过。metadata/UI20 passed。
- Stage3：QG408/408、sections369/369、subquestions328/328、MISS/FP/MERGE/SPLIT=0、errors={}；exact87.7%，不称100% exact。
- Stage2真实四源：S12/S04 PASS、S01/S11 FAIL；不是39/39真实语料全部PASS。
- 原始27 source hashes27/27；冻结V0.9 assets10/10，最新再次核验10/10。
- full suite未通过：起点ca5e原件实测同23个Studentizer测试失败（辅助提交函数默认显式stable_v09、测试却期待XML行为）；同4个V1.1 API baseline failure。单独记录原始baseline日志，不当成新代码引入。
- 两个历史严格math alignment测试卡在已冻结canonical路径，被中断，未完成；旧COM扫描contract也未复跑。不能用focused PASS替代这些缺口。
- Python编译、JS语法、PowerShell parser、diff-check及包审计检查；证据日志保存在 `C:\xml-uat\product-rescue-*`。

## 已知问题与下一步

1. 氧气1v1教师源含文本框，XML bookmark scope拒绝后V0.9有真实遗漏，当前明确停止交付。兼容内核不是对所有有效DOCX无损的保证；该产品blocker尚未修好。
2. 9个物理专题XML unknown b1使用兼容，未继续OOXML研究。
3. 超限pair拒绝、三角色歧义拒绝有明确原因；独立提交更宽，但不能伪报pair成功。
4. 仅教师输入未证明去答案安全时不生成学生成品；成品有中文复核提示。
5. 原文保全层不保证教学模块精细分配或teacher/student逐题对应；题号保留。
6. 完整回归及所有语料内容验收未通过；本包供真人测试，C4 Release仍暂停。C盘空闲仍偏低（清理后约528MB），批量测试前需另行释放系统盘空间；本轮未删除用户资料。

下步应先解决已确认的文本框内容保全/安全拒绝边界及baseline测试隔离，再决定发布。没有创建tag、合并main、开始Installer或新研究分支；没有冒充Chief PASS。
