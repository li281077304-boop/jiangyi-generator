# 讲义生成器

本仓库包含两个独立版本：

- `v1.1-stable`：Windows 桌面工作台，使用 Word COM 处理讲义。运行时和生成配置不纳入源码仓库。
- `v1.2-xml-experiment`：XML 引擎实验版，工作台界面已纳入；网页生成任务接口仍待接入 XML 引擎。

训练材料、生成成品和本机运行时不属于源码仓库内容。

## V1.1 Windows 发布包

`v1.1-stable/res/python/` 按设计不提交到 Git；它由发布脚本从官方 CPython 3.12.10 Windows x64 embeddable package 构建，并安装锁定的运行依赖。发布 ZIP 会同时包含应用源码、标准库、Python DLL 和依赖包，因此普通使用者不需要单独安装 Python。

在 Windows x64 构建机上需要 PowerShell 5.1、Git、网络连接，以及 Python 3.12 x64（仅供构建时安装依赖）。从干净检出执行：

```powershell
.\scripts\build_v1_1_release.ps1
```

脚本只打包当前干净 HEAD 中受 Git 跟踪的 `v1.1-stable` 文件，下载并校验官方嵌入式运行时，安装 `packaging/requirements-v1.1.lock` 中的固定版本依赖，运行发布前检查，最终输出到 `dist/`。ZIP 中的启动路径为 `v1.1-stable/启动讲义生成器.vbs`；解压后双击该脚本即可启动。
