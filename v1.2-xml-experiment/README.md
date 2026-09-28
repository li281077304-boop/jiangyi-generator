# 讲义生成器 · Flash 2（XML 实验版）

## 定位

Flash 1.2 实验版：去掉 Word COM 依赖，**纯 Python + lxml** 操作 docx。
- 速度预期：**1\~3 秒/份**（vs 1.1 COM 的 26\~45 秒，约 15\~30 倍提速）
- 不影响 1.1 稳定版（独立目录、互不干扰）

## 与 1.1 的关系

| | 1.1（稳定版） | 1.2（实验版，本目录） |
|---|---|---|
| 段落扫描 | Word COM（必装 Word） | XML body.iter（纯 Python） |
| 模板填充 | Word COM（_fill_com.ps1） | 模板对象 deepcopy + 通用关系迁移 |
| 学生版加工 | Word COM（_strip_answer） | 1.2 需新实现（XML 删段/重编号） |
| 模板格式保留 | 完美（COM 复制） | 已实测：段落/表格/公式（OLE）/图片全部正常 |
| 端口 | 5127 | 待定（与 1.1 隔离） |
| API 调用 | 完全停用 | 完全停用 |

## 当前状态（2026-08-10）

**已完成实验验证**：
- 段落扫描：XML 全量遍历（含文本框/表格内）自洽 ✓
- 模板填充：deepcopy 段落+图片关系迁移+OLE 关系迁移 ✓
- 封面表格填充：6 字段全部正确 ✓
- 知识精讲固定页首：pageBreakBefore ✓
- 图片归属修正：边界前装饰段并入下一块 ✓
- 字体保留：run 字体完全一致 ✓
- 表格复制：源 13 + 模板 1 = 成品 14 ✓
- OLE 公式（数学 1116 个）：成品 oleObject 关系 1116，Type=1 有效 ✓

以上是 **2026-08-10 的历史实验记录**。1116 个 OLE 的 Word 显示结果不由本轮自动化测试重新生成或复验。

## 2026-09-28 · XML Block Import spike

本轮在既有 `xml_engine` 上新增 block-level `BlockImporter` 与输出包 `package_validator`，仍使用 `python-docx + lxml`，不引入 `docxcompose` 运行依赖。关系图复制、按需样式迁移、编号冲突映射、书签/绘图 ID 修复等算法小范围适配自 docxcompose；Composer 整文档追加 API 不作为产品接口。MIT attribution 与许可证见本目录的 `THIRD_PARTY_NOTICES.md`、`LICENSES/docxcompose-MIT.txt`。

自动 fixture 覆盖文字/表格、图片、外链、样式与 basedOn/linked-style 依赖、numbering ID 冲突、递归 relationship、bookmarks、drawing IDs、VML/OLE preview，以及带 SHA256 对照的 dummy OLE embedding。`xml_engine.build()` 会验证已保存的 DOCX；validator 有 errors 时会抛错并删除失败产物。

dummy OLE 只验证 package relationship 与 embedding 二进制原样复制，不证明 MathType 可在 Word 渲染。下一阶段前仍需真实讲义压力测试；**`REAL_OLE_UAT_REQUIRED: YES`、`WINDOWS_WORD_UAT_REQUIRED: YES`**。目前不承诺 footnote/endnote/comment 内容合并、custom XML/data binding、跨所选 blocks 的 bookmark 或其他被 importer 明确列为 unsupported 的结构。

**未做**（正式开发时）：
- webapp（jobs.py 接入 xml_engine）
- 学生版 XML 加工（删答案段/重编号）
- 端到端网页测试

## 用法（CLI 试用）

```python
# 复制 1.1 的嵌入 Python 至此目录后可用：
python res/app/xml_engine.py <源.docx> <模板.docx> <输出.docx> [topic]
```

## 验证脚本

`tools/` 子目录保留 XML 方案各次实验/诊断脚本，可重新跑验证流程。
