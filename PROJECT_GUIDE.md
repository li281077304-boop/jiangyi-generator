# 项目规范与接续入口

2026-10-25 新增入口；保留既有规范及历史，不替代它们。

## 基线
- 本轮只读诊断与修复方案，未授权扩展功能或发布新版。
- 正式产品参考分支：feature/v1.2-c4-release-engineering，6016a38582a6b7a41916e6a650fb41a166599498。
- 本地 audit/chrome-layout-20261025 从该分支建立。main 的 README 为早期归档说明，不代表正式产品现状。
- 正式包运行时代码 b3b1e660bcb06a2c98e1d20d32924632e436e54c。源码恢复不等于安装包恢复。

## 现有规范与证据入口
- docs/v2/integration/C0_INTEGRATION_CONTRACT.md：历史接口契约，阅读时结合后续实现，不能将历史缺口当当前状态。
- docs/v2/integration/C1_SLOT_ROUTING_BUSINESS_RULES.md：分区业务规则。
- docs/v2/integration/C2_LOCAL_RESULT_DELIVERY_RULES.md：本地交付规则。
- docs/v2/integration/V1.2_FORMAL_PACKAGE_2026-10-09.md：正式包及未完成验证。
- docs/v2/ralph/RUN_JOURNAL.md：既有执行日志，保留全部历史。
- DEVLOG.md：新接续日志入口。

## 当前修复边界与验收
启动器应使用系统默认浏览器，失败提供实际服务URL，不强依赖Chrome。保留服务认证、互斥锁、端口选择、任务恢复及结果路径。
分栏含义待用户确认：工作台响应式、DOCX双栏、教学模块分配是不同问题。不得混同。

2026-10-25 用户后续明确：“分栏”指核心 Splitter，要求评估固定 Python 脚本可行性，若不足则考虑 API。此澄清替代上句的待确认状态；不能继续按 CSS 或 Word 双栏推进。评估见 [Splitter可行性评估](docs/SPLITTER_FEASIBILITY_2026-10-25.md)。本轮仅评估；尚未实施 API 或验证模型效果。
测试通过、源码生成、成品可打开、内容与版式复核、用户确认、Windows真实使用分别记录。
当前Mac环境不得宣称Windows EXE已实测；旧打包记录未完成的全量和WPS验收不得提升为通过。

## 2026-10-26 当前状态

用户继续推进并要求很酷的前端；已实施前端、Chrome启动器与两项分题规则修复。原“本轮只评估”的范围描述属于10月25日初始阶段，不再代表当前代码状态。新入口：[有限修复与验证](docs/SPLITTER_VALIDATION_2026-10-26.md)。API尚未配置/接入，不能将界面或45项限定测试通过说成Splitter全面解决。

本机隔离预览（依赖已装在`.venv`，未全局安装）：

```sh
JIANGYI_RESULT_ROOT="$PWD/.local-evaluation/ui-results" JIANGYI_RUNTIME_ROOT="$PWD/.local-evaluation/ui-runtime" .venv/bin/python -m flask --app v1.2-xml-experiment/res/app/webapp/app.py run --host 127.0.0.1 --port 5129
```

源资料与节点转储仅放`.local-evaluation/`并本地Git排除，勿提交公开仓库。启动命令用于开发预览，不是正式安装包。

## 2026-10-26 制作台重做

用户否定前一版仅换肤，确认重做。当前前端为工具轨/素材坞/中央纸张与结构画布/侧边配置，新增本地临时`/api/inspect`供真实原稿核对；外部模型API仍未接入。详情与输入边界见[制作台重构记录](docs/STUDIO_REDESIGN_2026-10-26.md)。审美尚待用户验收，不能继续引用上一版“前端完成”作为用户接受证据。


## 2026-10-27 用户确定API后置

用户明确选择“先完成离线诊断和前端，API 稍后配置”。此决定替代此前等待服务商/密钥的下一步：当前优先离线诊断、制作台体验和实际核对，外部模型接入暂缓，不以缺少API配置阻塞本地工作。现有/api/inspect为本地规则预览。已完成的测试与尚未完成的语义/用户验收保持区分。
