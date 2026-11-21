(function () {
  "use strict";
  var state = {files: [], templateType: "1v1", job: null};
  var selectedFile = null, result = null, selectedSlot = "knowledge";
  var controller = null, requestVersion = 0, scale = 1, showBlankBlocks = false;
  var $ = function (id) { return document.getElementById(id); };
  function key(file) { return [file.name, file.size, file.lastModified || 0].join("\u0000"); }
  function docs() { return state.files.filter(function (file) { return file.name.toLowerCase().endsWith(".docx"); }); }
  function cancel() { requestVersion += 1; if (controller) controller.abort(); controller = null; }
  function status(text, kind) { var node = $("studioInspectStatus"); if (node) { node.textContent = text; node.dataset.state = kind || "idle"; } }
  function note(text) { if ($("studioInspectNote")) $("studioInspectNote").textContent = text; }
  function clearResult(message) {
    result = null;
    if ($("studioBlockList")) {
      var empty = document.createElement("div"); empty.className = "studio-empty";
      var title = document.createElement("h3"); title.textContent = "展开原稿的真实结构";
      var hint = document.createElement("p"); hint.textContent = "选择 DOCX，点击“分析原稿”，然后按章节展开核对。";
      empty.append(title, hint); $("studioBlockList").replaceChildren(empty);
    }
    document.querySelectorAll("#studioSlotTabs [data-slot]").forEach(function (button) {
      button.dataset.baseLabel = button.dataset.baseLabel || button.textContent.trim();
      button.textContent = button.dataset.baseLabel; button.hidden = false; button.disabled = true; button.setAttribute("aria-pressed", "false");
    });
    note(message || "选择原稿后可预览内容分区。");
  }
  function rebuildSources() {
    var select = $("studioSourceSelect"), available = docs(); if (!select) return;
    var previous = selectedFile ? key(selectedFile) : ""; select.replaceChildren();
    available.forEach(function (file) { var option = document.createElement("option"); option.value = key(file); option.textContent = file.name; select.appendChild(option); });
    selectedFile = available.find(function (file) { return key(file) === previous; }) || available[0] || null;
    if (selectedFile) select.value = key(selectedFile); select.disabled = !selectedFile;
    if ($("studioInspectButton")) $("studioInspectButton").disabled = !selectedFile;
  }
  function syncState(detail) {
    detail = detail || {};
    var nextFiles = Array.isArray(detail.files) ? detail.files : [], nextTemplate = detail.templateType === "class" ? "class" : "1v1";
    var changed = state.templateType !== nextTemplate || state.files.map(key).join("\u0001") !== nextFiles.map(key).join("\u0001");
    state = {files: nextFiles.slice(), templateType: nextTemplate, job: detail.job || null};
    if ($("studioDocumentTitle")) {
      var documentTitle = state.files.length ? state.files[0].name.replace(/\.(docx|zip)$/i, "").split(/[（(]/)[0] : "未命名讲义";
      $("studioDocumentTitle").textContent = documentTitle; $("studioDocumentTitle").title = documentTitle;
    }
    if (changed) {
      cancel(); rebuildSources();
      var onlyZip = !docs().length && state.files.some(function (file) { return file.name.toLowerCase().endsWith(".zip"); });
      clearResult(onlyZip ? "ZIP 仍可生成，但结构核对不会在浏览器端解压；请添加单个 DOCX。" : "素材或模板已变化，请按需重新分析真实结构。");
      status(selectedFile ? "原稿已就绪" : "请选择 DOCX 素材", "idle");
    }
    var image = $("studioTemplateImage");
    if (image) { image.src = "/static/previews/" + (nextTemplate === "class" ? "class" : "1v1") + ".png"; image.alt = (nextTemplate === "class" ? "班课" : "1 对 1") + "讲义模板首页"; }
    if ($("studioReadyLabel")) $("studioReadyLabel").textContent = docs().length ? docs().length + " 份 DOCX 可核对结构" : state.files.length ? "素材可生成，结构核对需要 DOCX" : "添加 DOCX 后可核对真实分块";
    if ($("studioResults")) $("studioResults").open = !!(state.job && (state.job.status || state.job.items || state.job.warnings));
  }
  function switchMode(mode) {
    var structure = mode === "structure";
    if ($("studioTemplateView")) $("studioTemplateView").hidden = structure;
    if ($("studioStructureView")) $("studioStructureView").hidden = !structure;
    document.querySelectorAll('.zoom-controls button').forEach(function (button) { button.disabled = structure; });
    document.querySelectorAll("#studioModeButtons [data-studio-mode]").forEach(function (button) { var active = button.dataset.studioMode === mode; button.classList.toggle("active", active); button.setAttribute("aria-pressed", active ? "true" : "false"); });
  }
  function setScale(next) {
    scale = Math.max(0.6, Math.min(1.3, Math.round(next * 10) / 10));
    if ($("studioPaperStage")) $("studioPaperStage").style.setProperty("--paper-scale", String(scale));
    if ($("studioZoomLabel")) $("studioZoomLabel").textContent = Math.round(scale * 100) + "%";
  }
  function slot(id) { return result && result.slots.find(function (item) { return item.id === id; }); }
  function renderBlocks(id) {
    var list = $("studioBlockList"), current = slot(id); if (!list) return; list.replaceChildren();
    if (!current || !current.blocks || !current.blocks.length) {
      var empty = document.createElement("p"); empty.className = "studio-empty";
      empty.textContent = current ? "该分区没有返回内容块。" : "该分区未出现在本次真实分析结果中。"; list.appendChild(empty); return;
    }
    var blank = function (block) { return !String(block.text || "").trim() && !block.math_count && !block.image_count; };
    var blankCount = current.blocks.filter(blank).length;
    var visible = showBlankBlocks ? current.blocks : current.blocks.filter(function (block) { return !blank(block); });
    var heading = document.createElement("div"); heading.className = "block-list-heading";
    var count = document.createElement("span"); count.textContent = "当前预览 " + visible.length + " / " + current.block_count + " 个原文块";
    heading.appendChild(count);
    if (blankCount) {
      var toggle = document.createElement("button"); toggle.type = "button"; toggle.className = "blank-block-toggle";
      toggle.textContent = showBlankBlocks ? "折叠版式留白" : "显示 " + blankCount + " 个留白/占位块";
      toggle.setAttribute("aria-pressed", String(showBlankBlocks));
      toggle.addEventListener("click", function () { showBlankBlocks = !showBlankBlocks; renderBlocks(id); }); heading.appendChild(toggle);
    }
    list.appendChild(heading);
    visible.forEach(function (block) {
      var details = document.createElement("details"); details.className = "studio-block";
      var summary = document.createElement("summary"), text = String(block.text || "");
      var reference = document.createElement("span"); reference.className = "block-reference";
      reference.textContent = block.id ? "原文 " + block.id.replace(/^b/, "#") : "原文内容";
      var excerpt = document.createElement("span"); excerpt.className = "block-excerpt";
      excerpt.textContent = text ? (text.length > 110 ? text.slice(0, 110) + "…" : text) : block.math_count ? "公式内容 · " + block.math_count + " 处" : block.image_count ? "图片内容 · " + block.image_count + " 处" : "版式留白 / 占位";
      summary.append(reference, excerpt);
      var body = document.createElement("div"); body.className = "studio-section";
      var full = document.createElement("p"); full.textContent = text || "此块仅含结构内容，请核对公式或图片计数。";
      var meta = document.createElement("p"); meta.className = "block-meta"; meta.textContent = [block.kind === "table" ? "表格" : "原文内容", "公式 " + Number(block.math_count || 0), "图片 " + Number(block.image_count || 0)].join(" · ");
      body.append(full, meta);
      if (block.text_truncated) { var truncation = document.createElement("p"); truncation.className = "block-meta"; truncation.textContent = "此块仅预览前 2000 字，完整内容请查看原稿。"; body.appendChild(truncation); }
      details.append(summary, body); list.appendChild(details);
    });
  }
  function methodLabel(payload) {
    if (payload.status === "preserved") return "原文保留";
    if (payload.status === "unresolved") return "存在待核对内容";
    return payload.method === "PRESERVATION" ? "原文保留" : "规则建议 · 待核对";
  }
  function renderResult(payload) {
    if (!payload || !payload.source || !Array.isArray(payload.slots)) throw new Error("分析结果格式不完整");
    result = payload; var available = {};
    payload.slots.forEach(function (item) { available[item.id] = item; });
    document.querySelectorAll("#studioSlotTabs [data-slot]").forEach(function (button) {
      var item = available[button.dataset.slot]; button.dataset.baseLabel = button.dataset.baseLabel || button.textContent.trim();
      var label = document.createElement("span"); label.className = "slot-card-label"; label.textContent = item && item.label ? item.label.replace(/^六、/, "") : button.dataset.baseLabel;
      var total = document.createElement("strong"); total.className = "slot-card-count"; total.textContent = Number(item ? item.block_count : 0);
      var unit = document.createElement("span"); unit.className = "slot-card-unit"; unit.textContent = "原文块";
      button.replaceChildren(label, total, unit); button.disabled = !item; button.hidden = !item;
    });
    if (!available[selectedSlot]) selectedSlot = payload.slots.length ? payload.slots[0].id : "knowledge";
    document.querySelectorAll("#studioSlotTabs [data-slot]").forEach(function (button) { button.setAttribute("aria-pressed", button.dataset.slot === selectedSlot ? "true" : "false"); });
    renderBlocks(selectedSlot); var notes = [];
    if (payload.provisional || payload.status === "ready") notes.push("这是结构建议，仍需人工核验");
    if (payload.status === "preserved") notes.push("原文已保留，分块未被证明");
    if (payload.status === "unresolved" || (available.unresolved && available.unresolved.block_count)) notes.push("存在待核对内容块");
    if (Array.isArray(payload.warnings)) notes = notes.concat(payload.warnings.map(String));
    if (payload.truncated) notes.push("这里只截断预览摘要，不会修改或截断生成内容");
    note(notes.length ? notes.join("；") : "请展开内容块，对照原文核验章节归属。");
    status(methodLabel(payload), "done");
    if ($("studioInspectStatus")) $("studioInspectStatus").title = "已分析：" + payload.source.name;
  }
  function inspect() {
    if (!selectedFile) { status("请选择一个 DOCX 文件", "error"); return; }
    cancel(); var version = requestVersion; controller = new AbortController(); var active = controller;
    var timer = setTimeout(function () { active.abort(); }, 60000), data = new FormData();
    data.append("file", selectedFile); data.append("template_type", state.templateType);
    var headers = {}, token = document.querySelector('meta[name="launcher-token"]');
    if (token && token.content) headers["X-Launcher-Token"] = token.content;
    if ($("studioInspectButton")) $("studioInspectButton").disabled = true; status("正在读取原稿…", "running");
    fetch("/api/inspect", {method: "POST", body: data, headers: headers, signal: active.signal, cache: "no-store"})
      .then(function (response) { return response.json().catch(function () { return {}; }).then(function (body) { if (!response.ok) throw new Error(body.error || "结构分析失败"); return body; }); })
      .then(function (payload) { if (version === requestVersion && active === controller) renderResult(payload); })
      .catch(function (error) { if (version === requestVersion && active === controller) status(error.name === "AbortError" ? "分析超时，请重试或更换文件" : (error.message || "结构分析失败"), "error"); })
      .finally(function () { clearTimeout(timer); if (active === controller) { controller = null; if ($("studioInspectButton")) $("studioInspectButton").disabled = !selectedFile; } });
  }
  function initialize() {
    document.querySelectorAll("#studioModeButtons [data-studio-mode]").forEach(function (button) { button.addEventListener("click", function () { switchMode(button.dataset.studioMode); }); });
    if ($("studioSourceSelect")) $("studioSourceSelect").addEventListener("change", function () {
      selectedFile = docs().find(function (file) { return key(file) === $("studioSourceSelect").value; }) || null;
      cancel(); clearResult("来源已变化，请重新分析真实结构。"); status(selectedFile ? "原稿已就绪" : "请选择 DOCX 素材", "idle");
    });
    if ($("studioInspectButton")) $("studioInspectButton").addEventListener("click", inspect);
    document.querySelectorAll("#studioSlotTabs [data-slot]").forEach(function (button) { button.addEventListener("click", function () {
      if (!result || button.disabled) return; selectedSlot = button.dataset.slot;
      document.querySelectorAll("#studioSlotTabs [data-slot]").forEach(function (item) { item.setAttribute("aria-pressed", item === button ? "true" : "false"); }); renderBlocks(selectedSlot);
    }); });
    if ($("studioZoomOut")) $("studioZoomOut").addEventListener("click", function () { setScale(scale - 0.1); });
    if ($("studioZoomIn")) $("studioZoomIn").addEventListener("click", function () { setScale(scale + 0.1); });
    if ($("studioZoomReset")) $("studioZoomReset").addEventListener("click", function () { setScale(1); });
    clearResult(); setScale(1); switchMode("template");
    window.addEventListener("studio:state", function (event) { syncState(event.detail); });
    window.dispatchEvent(new CustomEvent("studio:request-state"));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize); else initialize();
}());
