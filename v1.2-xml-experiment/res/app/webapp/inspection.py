"""Bounded, ephemeral source routing inspection; never creates a generation job."""
from __future__ import annotations

from hashlib import sha256
import io
from pathlib import Path, PurePosixPath
import stat
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from batch_inputs import MAX_ARCHIVE_ENTRIES, MAX_EXPANDED_BYTES, _archive_path
from job_service import JobService, UnsupportedInput

MAX_UPLOAD_BYTES = 32 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 1024 * 1024
MAX_DOCUMENT_XML_BYTES = 16 * 1024 * 1024
# The real S29 maths source contains 156,680 XML nodes (4.3 MB document.xml).
# Keep a finite parse budget while supporting that existing regression source.
MAX_XML_NODES = 250000
MAX_SOURCE_BLOCKS = 6000
MAX_DISPLAY_BLOCKS = 400
MAX_TEXT_CHARS = 2000


class InspectionError(ValueError):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.status = code, status


def _validate_package(name, payload):
    """Apply existing DOCX rules plus bounds before any semantic parsing."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as package:
            entries = package.infolist()
            if len(entries) > MAX_ARCHIVE_ENTRIES or sum(i.file_size for i in entries) > MAX_EXPANDED_BYTES:
                raise InspectionError('INSPECT_EXPANDED_LIMIT', '文件展开后过大，暂不能在制作台核对。', 413)
            seen = set()
            for entry in entries:
                try:
                    path = _archive_path(entry.filename)
                except ValueError:
                    raise InspectionError('INSPECT_INVALID_PACKAGE', 'DOCX 包含不安全的内部路径。') from None
                if path.casefold() in seen or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                    raise InspectionError('INSPECT_INVALID_PACKAGE', 'DOCX 包含重复、加密或不支持的内部条目。')
                seen.add(path.casefold())
                if 'vbaproject' in path.casefold():
                    raise InspectionError('INSPECT_MACRO_UNSUPPORTED', '请使用不含宏的 DOCX 文件。')
                if path.lower().endswith(('.xml', '.rels')):
                    if entry.file_size > MAX_DOCUMENT_XML_BYTES:
                        raise InspectionError('INSPECT_XML_LIMIT', '文档结构过大，请拆分后核对。', 413)
                    xml = package.read(entry)
                    declaration_scan = xml.replace(b'\x00', b'').upper()
                    if b'<!DOCTYPE' in declaration_scan or b'<!ENTITY' in declaration_scan:
                        raise InspectionError('INSPECT_INVALID_XML', '文档包含不支持的 XML 声明。')
            if 'word/document.xml' not in seen:
                raise InspectionError('INSPECT_INVALID_PACKAGE', '这不是有效的 DOCX 文档。')
            document_xml = package.read('word/document.xml')
            nodes = 0
            depth = 0
            for event, node in ET.iterparse(io.BytesIO(document_xml), events=('start', 'end')):
                if event == 'start':
                    nodes += 1
                    depth += 1
                    if nodes > MAX_XML_NODES or depth > 128:
                        raise InspectionError('INSPECT_STRUCTURE_LIMIT', '文档结构过于复杂，请拆分后核对。', 413)
                else:
                    depth -= 1
                    node.clear()
        JobService.validate_docx(name, payload)
    except InspectionError:
        raise
    except (ValueError, KeyError, OSError, RuntimeError, zipfile.BadZipFile, ET.ParseError, UnsupportedInput):
        raise InspectionError('INSPECT_INVALID_PACKAGE', 'DOCX 文件损坏或结构不受支持，请重新保存为 DOCX 后再试。') from None


def _display_slots(snapshot, plan, preserved):
    labels = {'knowledge': '知识精讲', 'immediate': '即时训练', 'final': '巩固练习',
              'unresolved': '原文待核对'}
    if plan is not None:
        labels.update(plan.slot_labels)
    grouped = {key: [] for key in (['unresolved'] if preserved else ['knowledge', 'immediate', 'final'])}
    if preserved:
        grouped['unresolved'] = list(range(len(snapshot.document.blocks)))
    else:
        for record in plan.block_records:
            slot = record.get('destination_slot')
            if slot in grouped:
                grouped[slot].append(record['source_index'])
    allowance = MAX_DISPLAY_BLOCKS // len(grouped)
    truncated = False
    slots = []
    for key, indexes in grouped.items():
        blocks = []
        truncated |= len(indexes) > allowance
        for index in indexes[:allowance]:
            block = snapshot.document.blocks[index]
            text = block.text or ''
            truncated |= len(text) > MAX_TEXT_CHARS
            blocks.append({'id': 'b%d' % index, 'text': text[:MAX_TEXT_CHARS], 'kind': block.kind,
                           'math_count': block.math_count, 'image_count': len(block.images),
                           'text_truncated': len(text) > MAX_TEXT_CHARS})
        slots.append({'id': key, 'label': labels[key], 'block_count': len(indexes), 'blocks': blocks})
    return slots, truncated


def inspect_docx(filename, payload, template_type):
    if template_type not in ('1v1', 'class'):
        raise InspectionError('INSPECT_INVALID_TEMPLATE', '请选择一对一或班课模板。', 400)
    name = PurePosixPath((filename or '').replace('\\', '/')).name
    if not name or Path(name).suffix.lower() != '.docx':
        raise InspectionError('INSPECT_DOCX_REQUIRED', '请选择一个 DOCX 文件进行内容核对。', 400)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise InspectionError('INSPECT_UPLOAD_LIMIT', '内容核对仅支持不超过 32 MiB 的 DOCX 文件。', 413)
    if not payload:
        raise InspectionError('INSPECT_EMPTY_FILE', '所选文件为空。', 400)
    _validate_package(name, payload)
    from semantic_facade import analyze_source
    from xml_degradation import structural_snapshot, build_degraded_plan
    from slot_router import SlotRoutingError
    digest = sha256(payload).hexdigest()
    warnings = ['这是规则产生的暂定分块，尚未经过人工核对，也未生成讲义。',
                '核对仅针对当前原稿，不验证教师学生逐题对应；公式、图片请结合原文查看。']
    with tempfile.TemporaryDirectory(prefix='jiangyi-inspect-') as directory:
        # Never derive a filesystem path from the client-provided filename.
        source = Path(directory) / 'source.docx'
        source.write_bytes(payload)
        try:
            structural = structural_snapshot(source)
            if len(structural.document.blocks) > MAX_SOURCE_BLOCKS:
                raise InspectionError('INSPECT_BLOCK_LIMIT', '文档内容块过多，请拆分后核对。', 413)
            try:
                snapshot = analyze_source(source)
            except Exception:
                snapshot = structural
                warnings.append('部分语义结构无法识别，已使用原文结构进行核对。')
            plan, method = None, None
            try:
                try:
                    plan, evidence = build_degraded_plan(source, template_type, snapshot=snapshot, navigation_only=True)
                except SlotRoutingError:
                    plan, evidence = build_degraded_plan(source, template_type, snapshot=snapshot)
                method = evidence['selected_tier']
            except Exception:
                warnings.append('当前规则无法可靠分块，原文列入待核对区。')
            status = 'unresolved' if plan is None else ('preserved' if method == 'PRESERVATION' else 'ready')
            if status == 'preserved':
                warnings.append('当前仅完整保留原文，未完成教学模块分配。')
            if method == 'PARTITION':
                warnings.append('当前按完整题组及既定比例暂分；例题选择和练习分配仍需核对。')
            if status == 'ready':
                excluded = sum(record.get('destination_slot') not in ('knowledge', 'immediate', 'final')
                               for record in plan.block_records)
                if excluded:
                    warnings.append('有 %d 个封面或元信息块不属于正文教学模块，未列入下方分块。' % excluded)
            slots, truncated = _display_slots(snapshot, plan, status != 'ready')
            if truncated:
                warnings.append('展示已截断：总计最多 400 块，各区独立限额，每块最多 2000 字；块数仍为完整数量。')
            if sha256(source.read_bytes()).hexdigest() != digest:
                raise InspectionError('INSPECT_SOURCE_CHANGED', '核对过程中原稿校验异常，请重试。')
            return {'source': {'name': name, 'sha256': digest}, 'status': status, 'method': method,
                    'template_type': template_type, 'slots': slots, 'warnings': warnings,
                    'truncated': truncated, 'provisional': True}
        except InspectionError:
            raise
        except Exception:
            raise InspectionError('INSPECT_ANALYSIS_FAILED', '暂时无法读取此文档的内容结构，请重新保存为 DOCX 后再试。') from None
