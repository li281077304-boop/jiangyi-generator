# KNOWN_GOOD_V0.9_BASELINE

此 baseline 来自用户实际运行成功的 Windows 目录。内部版本文本可能不一致，不作为版本身份判断依据。

- 用户确认：程序可以正常运行，1v1 和班课均可以导出。
- 原目录：`C:\Users\Administrator\Desktop\工作\讲义生成器\讲义生成器V0.9`
- 实际包根：该目录下的同名子目录（包含 `res`、launcher 和使用说明）。
- 仓库归档目录：`known-good-v0.9/`
- 原始目录保持只读；上传文件按 SHA256 校验。
- Python 运行时 `res/python` 按用户要求不进入 Git。manifest 保留该目录全部文件的相对路径、大小和 SHA256。
- 运行时版本为 CPython 3.12.10；依赖版本见 `KNOWN_GOOD_V0.9_RUNTIME_REQUIREMENTS.lock`。重建需使用官方 CPython 3.12.10 Windows x64 embeddable runtime，并将锁定依赖安装到 `Lib/site-packages`；重建后仍需真实 Windows UAT。
- Python / PowerShell / WebUI 源码、启动 EXE、配置及 1v1 / 班课模板均按源包内容原样归档。

Manifest: `KNOWN_GOOD_V0.9_MANIFEST.json`
