# 讲义生成器

当前接续入口：[项目规范](PROJECT_GUIDE.md)、[DEVLOG](DEVLOG.md)。本地修复工作基于1.2的C4发布分支；默认main上的早期归档说明不能代表正式包状态。

本仓库包含两个独立版本：

- `v1.1-stable`：Windows 桌面工作台，使用 Word COM 处理讲义。运行时和生成配置不纳入源码仓库。
- `v1.2-xml-experiment`：沿用早期目录名的1.2 XML工作台，生成接口已接通；质量限制与最新验证见[2026-10-26记录](docs/SPLITTER_VALIDATION_2026-10-26.md)。

训练材料、生成成品和本机运行时不属于源码仓库内容。

[离线 Splitter 复核工具](docs/SPLITTER_REVIEW.md)可从已有诊断目录生成逐块报告和人工清单，附可运行的合成示例。
