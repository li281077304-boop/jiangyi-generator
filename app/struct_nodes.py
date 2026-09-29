# -*- coding: utf-8 -*-
"""
struct_nodes.py —— StructDoc 的「可寻址内容节点」层（Splitter V2 预备）

解决的问题
----------
Stage 1 实测：约 38% 的段落位于表格单元格内部（「全文一表」的讲义里甚至 100%）。
若把整张表当作一个不可分割的块，就无法标注表格内部的章节 / 题组 / 材料结构。
本模块为每个**内容节点**（段落 / 未识别块）以及每个**容器**（表格 / 单元格 / body）
生成稳定、可重复定位的身份，供 gold 标注与对照工具引用。

节点身份（node id）语法
----------------------
    b{seq}                       body 顶层块（seq = StructDoc.Block.seq，稠密块序号）
    {父}.r{row}c{col}             表格的第 row 行第 col 列**单元格容器**
    {父}.n{k}                     单元格容器内第 k 个块（k = Cell.blocks 中的下标）

示例
----
    b12                     第 12 个顶层块
    b12.r1c0                第 12 块（表格）第 1 行第 0 列单元格
    b12.r1c0.n2             该单元格内第 2 个块
    b12.r1c0.n2.r0c1.n0     该块（嵌套表格）第 0 行第 1 列单元格内第 0 个块

为什么这样设计
--------------
1. **不破坏顶层标注**：顶层块仍是 `b{seq}`，现有 gold 里的整数区间含义不变。
2. **不依赖易变的纯序号**：容器路径只用来「定位到哪个容器」，
   容器内的边界推荐用 `scope` + `anchor`（锚点文本）表达，见 gold_compare。
3. **稳定可重复**：同一文件同一份 StructDoc 解析，节点 id 恒定；
   路径按结构（表→行列→子块）而非按出现顺序编号。
4. **支持重排**：节点是集合成员，gold/compare 的所有判定都是集合运算。

容器与内容
----------
- 容器（body / 表格 / 单元格）**本身不是内容**，只提供范围。
- 内容节点 = 段落 / 未知块。表格的扁平文本只是 rollup，
  不参与内容统计（否则会与单元格内节点重复计数）。
- 因此「覆盖 b3（表格）」= 覆盖 b3 的全部后代内容节点（端点自动扩展到
  容器的首/末后代），语义上等价于「这几块里的所有内容」。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from struct_doc import Block, Cell, StructDoc, iter_all_paragraphs  # noqa: F401

ROOT = "body"


@dataclass
class Node:
    """一个内容节点。"""
    id: str
    kind: str                 # paragraph | unknown
    text: str
    container: str            # 直接所属容器 id（单元格容器 或 body）
    order: int                # 文档序（在 NodeIndex.order_ids 中的下标）
    block: Block = None       # 原始 Block（承载 eff_sz/bold/num/images 等特征）
    has_content: bool = True


class NodeIndex(object):
    """把 StructDoc 摊平为「容器 + 内容节点」的可寻址索引。"""

    def __init__(self, doc: StructDoc):
        self.doc = doc
        self.nodes: List[Node] = []                 # 文档序
        self.by_id: Dict[str, Node] = {}
        self.containers: Dict[str, str] = {ROOT: "body"}   # id -> kind
        self.container_parent: Dict[str, str] = {}
        self.descendants: Dict[str, List[str]] = {}        # 容器 -> 后代内容节点（有序）
        self._build()

    # ---------------- 构建 ----------------
    def _build(self):
        order = [0]

        def add_content(nid, kind, text, container, block):
            node = Node(id=nid, kind=kind, text=text, container=container,
                        order=order[0], block=block,
                        has_content=_block_has_content(block))
            order[0] += 1
            self.nodes.append(node)
            self.by_id[nid] = node

        def walk_cell(cell: Cell, cell_id: str, parent_container: str):
            self.containers[cell_id] = "cell"
            self.container_parent[cell_id] = parent_container
            for k, blk in enumerate(cell.blocks):
                nid = "%s.n%d" % (cell_id, k)
                if blk.kind == "table":
                    walk_table(blk, nid, cell_id)
                else:
                    add_content(nid, blk.kind, blk.text, cell_id, blk)

        def walk_table(tbl_block: Block, tid: str, parent_container: str):
            self.containers[tid] = "table"
            self.container_parent[tid] = parent_container
            tb = tbl_block.table
            if tb is None:
                return
            for r, row in enumerate(tb.rows):
                for c, cell in enumerate(row):
                    walk_cell(cell, "%s.r%dc%d" % (tid, r, c), tid)

        for blk in self.doc.blocks:
            nid = "b%d" % blk.seq
            if blk.kind == "table":
                walk_table(blk, nid, ROOT)
            else:
                add_content(nid, blk.kind, blk.text, ROOT, blk)

        # 容器 → 后代内容节点（有序）
        for cid in self.containers:
            self.descendants[cid] = []
        for node in self.nodes:
            anc = node.container
            while anc is not None:
                self.descendants.setdefault(anc, []).append(node.id)
                if anc == ROOT:
                    break
                anc = self.container_parent.get(anc)
        self.descendants.setdefault(ROOT, [n.id for n in self.nodes])

    # ---------------- 查询 ----------------
    @property
    def order_ids(self) -> List[str]:
        return [n.id for n in self.nodes]

    @property
    def content_ids(self) -> Set[str]:
        return {n.id for n in self.nodes if n.has_content}

    def is_container(self, nid: str) -> bool:
        return nid in self.containers

    def text_of(self, nid: str) -> str:
        n = self.by_id.get(nid)
        return n.text if n else ""

    def order_of(self, nid: str) -> Optional[int]:
        n = self.by_id.get(nid)
        return n.order if n else None

    def first_content(self, cid: str) -> Optional[str]:
        d = self.descendants.get(cid)
        return d[0] if d else None

    def last_content(self, cid: str) -> Optional[str]:
        d = self.descendants.get(cid)
        return d[-1] if d else None

    def expand(self, nid: str) -> Set[str]:
        """把一个 id 展开成内容节点集合：容器→全部后代；内容节点→自身。"""
        if nid in self.containers:
            return set(self.descendants.get(nid, []))
        return {nid} if nid in self.by_id else set()

    def interval(self, start, end) -> Set[str]:
        """[start, end] 之间的全部内容节点（按文档序，端点会做容器扩展）。

        端点可以是 int（顶层块号）、节点 id 或容器 id；容器取它的首/末后代。
        无法定位时返回空集。
        """
        start = self.resolve_ref(start)
        end = self.resolve_ref(end)
        s = start if start in self.by_id else self.first_content(start)
        e = end if end in self.by_id else self.last_content(end)
        if s is None or e is None:
            return set()
        a, b = self.order_of(s), self.order_of(e)
        if a is None or b is None:
            return set()
        if a > b:
            a, b = b, a
        return {n.id for n in self.nodes[a:b + 1]}

    def resolve_ref(self, ref) -> Optional[str]:
        """把 int / str 引用统一成 node id。

        int              → "b{int}"（顶层块号，向后兼容 gold 里的整数区间）
        "12"             → "b12"（容错：数字字符串）
        "b12" / "b12.r0c0" / "b12.r0c0.n3" → 原样
        """
        if isinstance(ref, bool):
            return None
        if isinstance(ref, int):
            return "b%d" % ref
        s = str(ref).strip()
        if not s:
            return None
        if s.isdigit():
            return "b%s" % s
        return s

    def exists(self, ref) -> bool:
        r = self.resolve_ref(ref)
        return r is not None and (r in self.by_id or r in self.containers)

    def within(self, container: str, needle: str) -> Optional[str]:
        """在容器内按文本查找第一个匹配的内容节点（归一化后子串匹配）。"""
        from gold_compare import _norm  # 延迟导入避免循环
        n = _norm(needle)
        if not n:
            return None
        for nid in self.descendants.get(container, []):
            if n in _norm(self.by_id[nid].text):
                return nid
        return None


def _block_has_content(block: Block) -> bool:
    if block is None:
        return False
    if (block.text or "").strip():
        return True
    return bool(block.images) or bool(block.oles) or bool(block.math_count)


def iter_nodes(doc: StructDoc) -> List[Node]:
    """便利函数：按文档序返回全部内容节点。"""
    return NodeIndex(doc).nodes


def node_id_of_block(block: Block) -> str:
    """顶层块 → node id。"""
    return "b%d" % block.seq
