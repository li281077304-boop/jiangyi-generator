# DEVLOG

## 2026-10-25 — Codex 主智能体，Sol规划与两路独立核查
- 用户要求：讲义生成器1.2强制关联Chrome、分栏糟糕，询问解决方案；本地可能删除，GitHub有源码。
- 实际操作：克隆github.com/li281077304-boop/jiangyi-generator，取回远程分支与标签；确认c4发布分支6016a38为产品参考，建立本地audit/chrome-layout-20261025。未修改产品代码、未打包、未推送。
- 新增路径：PROJECT_GUIDE.md、DEVLOG.md，为现有规范和RUN_JOURNAL建立根入口。
- 根因证据：windows_launcher.pyw:271–289仅查找Chrome；tests/test_windows_launcher.py:210–229固化该限制；RUN_JOURNAL:639–640记录CLI自动化要求进入产品启动器。
- 方案：启动改系统默认浏览器，失败显示实际URL；同步测试及打包说明。首次/重复启动、动态端口、无Chrome和默认Edge/Firefox都需验收。
- 分栏：当前尚未确认是DOCX双栏、教学模块分配还是工作台布局。源码源节属性移除、模板主导版式及固定辅助栏宽度仅是排查证据，不等于用户症状已复现。
- 核查状态：源码/历史记录已读取；未运行应用、未生成文件、未视觉复核、未Windows实测、未取得本轮用户验收。
- 下一步：明确分栏所指；在确认的产品基线实施两项修复，使用真实失败样本回归，并保留旧版打包记录的未完成项。

## 2026-10-25 — Splitter Python/API可行性评估
- 执行者：Codex主智能体；Sol先规划，代码链与旧API两路独立审查。
- 用户澄清：核心是Splitter，询问固定Python能否完成，否则考虑API。此澄清覆盖上轮分栏含义未定。
- 实际改动：新增 docs/SPLITTER_FEASIBILITY_2026-10-25.md，更新PROJECT_GUIDE的当前入口；未改产品代码、未调用API、未读取密钥、未上传素材、未打包或推送。
- 核查证据：当前默认auto按角色独立处理，不要求严格canonical配对；xml_degradation的五级路径；exercise_partition无知识首题组及70:30策略；旧API强制三个连续区间，另有未接主流程的候选复核；docs仅4份源DOCX，无法据此复跑33/35主题。
- 结论：固定脚本对稳定格式可行，不建议继续无限补规则覆盖开放资料；建议Python保真/验证+API语义块判断，不能恢复旧三切块接口。JSON合法与SLOTTED均非语义正确证明。
- 验收状态：源码/历史证据审查完成；未新跑语料、未新测API效果/费用/耗时、未生成成品、未用户试用。历史2/33是当时全链XML结果，不是当前Splitter准确率。
- 下一步：恢复真实失败原稿及独立人工标准，对同一结构输入做固定脚本/API辅助的有限对照；新模型有效才接生产。Chrome修复仍独立待实施。

## 2026-10-26 — 有限修复、真实样本与前端交付
- 执行者：Codex主智能体整合；Sol规划/独立审查/启动器修复，launch_audit分题诊断与修复，layout_audit前端实现。
- 用户要求：继续评估固定Python与API；新增“狂拽酷帅吊炸天”的前端；后续再次要求继续。
- 实际修改：exercise_partition.py及tests/test_exercise_partition.py修小数误题号、公式/OLE答案误全局区并对首题歧义明确拒绝；windows_launcher.pyw及test_windows_launcher.py移除Chrome硬依赖；index.html/workspace.css/workspace.js重做深色工作台、主题与响应式，保留接口；新增tools/splitter_assessment_20261025.py、评估/验证报告，更新README与规范入口。
- 本地恢复：29份去重原稿，22份与历史11主题SHA匹配，`.local-evaluation/manifest.json`。run-01/02/03及comparison.json保留；本目录已本地Git排除。隔离.venv安装Flask，未全局安装依赖。
- 核查：45项限定测试通过，JS语法/diff-check通过。run-03双模板均14 SEMANTIC/10 PRESERVATION/3 PARTITION/2读入错误；29源SHA未变，仅S06/S29槽位变化。独立审查提出首题歧义/OLE测试缺口，修复后复核解除阻断。
- 浏览器：本机5129已开启；真实素材导入、清空撤销、深浅主题、模板预览、非法文件提示、历史恢复通过；一组原稿生成2DOCX且包可读。390–1920多尺寸无已测页面溢出。截图`.local-evaluation/ui-desktop.png`。预览进程当前session 26565；开发服务非正式安装包。
- 未完成：API供应商/配置未收到，未实际调用；原文保留10份及双版本剩余差异未解决；语义金标、全项目回归、当前产物逐页WPS、无Chrome Windows EXE试用均未通过或未执行。未提交/推送/发布。
- 下一步：用户指定API服务商/本地配置后，以可变node_id语义计划做同原稿对照；不恢复旧三连续段接口；按有限验证结果决定接生产。后续接手先读验证报告。

## 2026-10-26 — 用户否定换肤后，重做讲义制作台
- 要求：用户“你就换个颜色就狂拽酷帅掉渣天了？”；助手提出重做中央制作台，用户“嗯哼”、后续“继续”授权推进。
- 执行者：Sol先规划并实现状态桥/交互；layout_audit重写HTML/CSS；launch_audit只读分析接口及测试；主智能体整合、补留白折叠/真实章节卡/截断提示/对比度、浏览器验证。
- 实际改动：index.html、workspace.css、workspace.js、studio.js；app.py新增/api/inspect与inspection.py；test_source_inspection.py及启动器品牌断言。既有Splitter修补与生成请求契约保留。
- 核查：76项组合相关测试通过；最终响应字段调整后46项相关重跑通过；JS语法/diff-check通过。真实浏览器生成2DOCX完成、结构预览与返回块数一致、来源/模板变更清旧结果、纸张缩放、深浅主题、390–1440已测布局正常，无已观测console error。
- 产物：docs/STUDIO_REDESIGN_2026-10-26.md；截图.local-evaluation/studio-v2-paper.png、studio-v2-structure.png；上一版截图ui-before-studio-redesign.png保留。原稿与截图未提交公开仓库。
- 状态：本地预览进程session 60871，地址127.0.0.1:5129；已留浏览器交付标签。本地接口是当前规则暂定分块，不是外部大模型。保留/未解结果明确待核对。
- 未完成：用户审美与真实使用确认；外部模型对照、Windows重新打包/实机、Splitter全面质量验收。未推送/发布。
- 下一步：由用户实际操作新制作台评估视觉与交互；原API服务选择问题仍未收到答案，不把本地inspect视为大模型接入。


## 2026-10-27 — API后置决定
- 执行者：Codex主智能体。
- 用户原文：先完成离线诊断和前端，API 稍后配置。
- 实际改动：PROJECT_GUIDE.md追加当前范围，DEVLOG记录决策；未修改代码、运行测试或调用外部模型。
- 核查依据：已读取现行规范和前轮验证日志。前轮成果保留，未新增功能完成或用户验收声明。
- 未完成：离线Splitter语义正确性与用户体验验收、Windows打包/实机仍按既有记录；外部API配置/对照明确后置。
- 下一步：优先本地规则诊断及制作台实际核对；用户明确恢复API事项后再选择服务与配置。

## 2026-11-21 同步状态核查
Codex 按用户要求核对 git status、HEAD 和 git ls-remote。本地 HEAD 与远端 C4 均为 6016a38，远端 main 为 7161b52，无同名 audit 分支。9 个已跟踪文件有修改，另有 9 个未跟踪文件。本轮仅记录状态，未提交或推送。

## 2026-11-21 GitHub 同步
Codex 按用户要求整理制作台、启动器、Splitter、测试与接续文档，在当前独立分支提交并同步。提交前重跑相关测试，76 项通过。Windows 安装包仍待单独构建与验收。
