(function () {
  "use strict";

  var SUBJECTS = [
    ["book-open-text", "语文", "#c66464"], ["sigma", "数学", "#4280c5"],
    ["languages", "英语", "#8b71bd"], ["orbit", "物理", "#4b91a0"],
    ["flask-conical", "化学", "#4c9a70"], ["dna", "生物", "#69964d"],
    ["landmark", "历史", "#a17855"], ["earth", "地理", "#438995"],
    ["scale", "道德与法治", "#9a7157"]
  ];
  var GRADES = {"小学": ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"], "初中": ["七年级", "八年级", "九年级"], "高中": ["高一", "高二", "高三"]};
  var HANDOUT_TYPES = ["复习讲义", "同步讲义", "新课讲义", "期中复习", "期末复习", "中考复习", "高考复习"];
  var SPLIT_HELP = {
    smart: {
      title: "智能分块",
      badge: "推荐",
      description: "优先按原文明确的教学栏目分配内容；没有明确栏目时，仅将能够确认完整的练习块整体安排到训练区域。",
      steps: ["目录与正文标题定位", "知识类栏目进入“知识精讲”", "即时训练类栏目进入“即时训练”", "巩固或测试栏目及完整后部练习块进入“巩固练习”"],
      note: "每个槽内保持原文顺序；完整练习块、共享材料和不可拆表格不会被强拆。XML 受限模式遇到不支持内容会停止并说明原因；如需继续，请手动选择稳定模式（V0.9 引擎）。"
    },
    full: {
      title: "完整保留",
      badge: "原文优先",
      description: "适合纯知识清单、没有明确训练标题，或你希望整份素材完全连贯呈现的讲义。系统不寻找练习边界。",
      steps: ["不识别训练标题", "整份素材保持顺序", "全部放入“知识精讲”", "训练区域保持为空"],
      note: "不会拆开任何段落；适合先确保原有结构完整，再手动调整内容的场景。"
    }
  };
  var MAX_BYTES = 500 * 1024 * 1024;
  var state = {files: [], undo: [], jobs: [], selectedSubject: "数学", templateType: "1v1", engineMode: "stable_v09", currentJob: null, pollTimer: null, elapsedTimer: null, startedAt: 0, previewTemplate: "1v1"};
  var $ = function (id) { return document.getElementById(id); };

  function refreshIcons(root) {
    if (window.lucide) window.lucide.createIcons({attrs: {"aria-hidden": "true"}, root: root || document});
  }
  function makeIcon(name) {
    var node = document.createElement("i");
    node.setAttribute("data-lucide", name);
    return node;
  }
  function setText(id, value) { $(id).textContent = value == null ? "" : String(value); }
  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(bytes < 10240 ? 1 : 0) + " KB";
    return (bytes / 1048576).toFixed(bytes < 10485760 ? 1 : 0) + " MB";
  }
  function formatDate(timestamp) {
    if (!timestamp) return "本次运行";
    return new Intl.DateTimeFormat("zh-CN", {month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"}).format(new Date(timestamp * 1000));
  }
  function academicYear(offset) {
    var now = new Date(), start = now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1;
    start += offset || 0;
    return start + "-" + (start + 1) + "学年";
  }
  function toast(message) {
    var node = $("toast");
    node.textContent = message;
    node.hidden = false;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(function () { node.hidden = true; }, 2600);
  }
  function requestJson(url, options) {
    return fetch(url, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          var error = new Error(data.error || "服务暂时不可用");
          error.status = response.status;
          error.data = data;
          throw error;
        }
        return data;
      });
    });
  }

  function initializeOptions() {
    var handout = $("handoutType");
    HANDOUT_TYPES.forEach(function (value) {
      var option = document.createElement("option");
      option.value = option.textContent = value;
      handout.appendChild(option);
    });
    var years = $("academicYear");
    [-1, 0, 1].forEach(function (offset) {
      var option = document.createElement("option");
      option.value = option.textContent = academicYear(offset);
      if (offset === 0) option.selected = true;
      years.appendChild(option);
    });
    var grid = $("subjectGrid");
    SUBJECTS.forEach(function (subject) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "subject-button";
      button.dataset.subject = subject[1];
      button.style.setProperty("--subject-color", subject[2]);
      button.setAttribute("aria-pressed", subject[1] === state.selectedSubject ? "true" : "false");
      button.appendChild(makeIcon(subject[0]));
      button.appendChild(document.createTextNode(subject[1]));
      button.addEventListener("click", function () { selectSubject(subject[1]); });
      grid.appendChild(button);
    });
    updateGrades();
  }

  function loadPrefs() {
    var prefs = {};
    try { prefs = JSON.parse(localStorage.getItem("handout_workspace_prefs") || "{}"); } catch (error) {}
    if (SUBJECTS.some(function (item) { return item[1] === prefs.subject; })) state.selectedSubject = prefs.subject;
    if (GRADES[prefs.eduLevel]) $("eduLevel").value = prefs.eduLevel;
    updateGrades();
    if (GRADES[$("eduLevel").value].indexOf(prefs.grade) >= 0) $("gradeSelect").value = prefs.grade;
    if (HANDOUT_TYPES.indexOf(prefs.handoutType) >= 0) $("handoutType").value = prefs.handoutType;
    if (["1v1", "class"].indexOf(prefs.templateType) >= 0) state.templateType = prefs.templateType;
    if (["stable_v09", "xml_restricted"].indexOf(prefs.engineMode) >= 0) state.engineMode = prefs.engineMode;
    $("engineMode").value = state.engineMode;
    if (["smart", "full"].indexOf(prefs.splitMode) >= 0) $("splitMode").value = prefs.splitMode;
    if (["auto", "separate"].indexOf(prefs.docxMode) >= 0) $("docxMode").value = prefs.docxMode;
    $("compactFiles").checked = !!prefs.compactFiles;
    applyCompact();
    selectSubject(state.selectedSubject, true);
    setTemplate(state.templateType, true);
    updateEngineModeNote();
  }
  function savePrefs() {
    var prefs = {subject: state.selectedSubject, eduLevel: $("eduLevel").value, grade: $("gradeSelect").value, handoutType: $("handoutType").value, academicYear: $("academicYear").value, templateType: state.templateType, engineMode: state.engineMode, splitMode: $("splitMode").value, docxMode: $("docxMode").value, compactFiles: $("compactFiles").checked};
    localStorage.setItem("handout_workspace_prefs", JSON.stringify(prefs));
    setText("saveState", "配置已保存");
  }
  function updateEngineModeNote() {
    state.engineMode = $("engineMode").value || "stable_v09";
    var note = state.engineMode === "stable_v09"
      ? "使用已验证的 V0.9 引擎。XML 模式需要你手动选择，遇到不支持的文件会提示原因，不会自动切换。"
      : "受限实验模式：仅在 XML 能力范围内生成。遇到不支持的文件会显示原因；如需继续，请手动改选稳定模式（V0.9 引擎）。";
    setText("engineModeNote", note);
    $("splitMode").disabled = state.engineMode === "stable_v09";
    $("splitTitle").textContent = state.engineMode === "stable_v09" ? "V0.9 原有分块规则" : "智能分块";
    $("splitBadge").textContent = state.engineMode === "stable_v09" ? "稳定引擎" : "推荐";
    $("splitDescription").textContent = state.engineMode === "stable_v09"
      ? "稳定模式沿用 V0.9 引擎自己的处理规则，下面的分块选项不适用。"
      : (SPLIT_HELP[$("splitMode").value] || SPLIT_HELP.smart).description;
    if (state.engineMode === "stable_v09") setText("splitNote", "本任务使用 V0.9 原有规则；分块策略不会传入旧引擎。");
    $("splitSteps").replaceChildren();
    if (state.engineMode === "stable_v09") $("splitSteps").hidden = true;
    else { $("splitSteps").hidden = false; updateSplitExplainer(); }
  }
  function updateGrades(preferred) {
    var select = $("gradeSelect"), values = GRADES[$("eduLevel").value] || [];
    var old = preferred || select.value;
    select.replaceChildren();
    values.forEach(function (value) {
      var option = document.createElement("option");
      option.value = option.textContent = value;
      select.appendChild(option);
    });
    if (values.indexOf(old) >= 0) select.value = old;
  }
  function selectSubject(subject, quiet) {
    state.selectedSubject = subject;
    document.querySelectorAll(".subject-button").forEach(function (button) { button.setAttribute("aria-pressed", button.dataset.subject === subject ? "true" : "false"); });
    if (!quiet) configChanged();
    updateFilename();
  }
  function setTemplate(template, quiet) {
    state.templateType = template;
    document.querySelectorAll("[data-template]").forEach(function (button) { button.setAttribute("aria-pressed", button.dataset.template === template ? "true" : "false"); });
    var isClass = template === "class";
    $("templateThumb").src = "/static/previews/" + (isClass ? "class" : "1v1") + ".png";
    $("templateThumb").alt = (isClass ? "班课" : "1 对 1") + "讲义模板首页";
    setText("templateName", isClass ? "班课讲义" : "1 对 1 讲义");
    if (!quiet) configChanged();
  }
  function configChanged() {
    savePrefs();
    updateFilename();
    updateSplitExplainer();
    updateEngineModeNote();
  }
  function updateFilename() {
    setText("filenamePreview", [$("academicYear").value, $("gradeSelect").value, state.selectedSubject, "专题名", $("handoutType").value, "教师版.docx"].filter(Boolean).join(" "));
  }
  function updateSplitExplainer() {
    var help = SPLIT_HELP[$("splitMode").value] || SPLIT_HELP.smart;
    var knowledgeSlot = state.templateType === "class" ? "知识精讲&例题讲解" : "知识精讲";
    var finalSlot = state.templateType === "class" ? "六、出门测试" : "六、巩固练习";
    function templateText(value) {
      return value
        .replace(/知识精讲(?:&例题讲解)?/g, knowledgeSlot)
        .replace(/(?:六、)?巩固练习/g, finalSlot);
    }
    setText("splitTitle", help.title); setText("splitBadge", help.badge); setText("splitDescription", templateText(help.description)); setText("splitNote", templateText(help.note));
    $("splitExplainer").dataset.mode = $("splitMode").value;
    var steps = $("splitSteps"); steps.replaceChildren();
    help.steps.forEach(function (step, index) {
      var item = document.createElement("span");
      var indexNode = document.createElement("b"); indexNode.textContent = index + 1;
      item.append(indexNode, document.createTextNode(templateText(step))); steps.appendChild(item);
    });
  }
  function applyCompact() { $("fileList").classList.toggle("compact", $("compactFiles").checked); }

  function pushUndo() {
    state.undo.push(state.files.slice());
    if (state.undo.length > 10) state.undo.shift();
    $("undoFiles").disabled = false;
  }
  function addFiles(fileList) {
    var incoming = Array.prototype.slice.call(fileList), errors = [], accepted = [], names = {};
    state.files.forEach(function (file) { names[file.name.toLowerCase()] = true; });
    incoming.forEach(function (file) {
      var lower = file.name.toLowerCase();
      if (!(lower.endsWith(".docx") || lower.endsWith(".zip"))) errors.push(file.name + "：仅支持 DOCX 或 ZIP");
      else if (file.name.indexOf("~$") === 0) errors.push(file.name + "：已忽略 Word 临时文件");
      else if (names[lower]) errors.push(file.name + "：已在素材列表中");
      else { names[lower] = true; accepted.push(file); }
    });
    var nextBytes = state.files.concat(accepted).reduce(function (sum, file) { return sum + file.size; }, 0);
    if (nextBytes > MAX_BYTES) { errors.push("文件总大小超过 500 MB，请分批生成"); accepted = []; }
    if (accepted.length) { pushUndo(); state.files = state.files.concat(accepted); }
    renderFiles(errors);
  }
  function removeFile(index) { pushUndo(); state.files.splice(index, 1); renderFiles(); }
  function clearFiles() { if (!state.files.length) return; pushUndo(); state.files = []; renderFiles(); }
  function undoFiles() {
    if (!state.undo.length) return;
    state.files = state.undo.pop();
    $("undoFiles").disabled = !state.undo.length;
    renderFiles();
  }
  function renderFiles(errors) {
    var list = $("fileList"), query = $("fileSearch").value.trim().toLowerCase();
    list.replaceChildren();
    state.files.forEach(function (file, index) {
      if (query && file.name.toLowerCase().indexOf(query) < 0) return;
      var row = document.createElement("div"); row.className = "file-row";
      var fileIcon = document.createElement("span"); fileIcon.className = "file-icon" + (file.name.toLowerCase().endsWith(".zip") ? " zip" : ""); fileIcon.appendChild(makeIcon(file.name.toLowerCase().endsWith(".zip") ? "archive" : "file-text"));
      var info = document.createElement("div"); info.className = "file-info";
      var title = document.createElement("strong"); title.textContent = file.name;
      var meta = document.createElement("p"); meta.textContent = formatBytes(file.size) + " · " + (file.name.toLowerCase().endsWith(".zip") ? "压缩包" : "Word 文档");
      info.append(title, meta);
      var remove = document.createElement("button"); remove.className = "icon-button danger-hover"; remove.type = "button"; remove.setAttribute("aria-label", "移除 " + file.name); remove.dataset.tooltip = "移除"; remove.appendChild(makeIcon("x")); remove.addEventListener("click", function () { removeFile(index); });
      row.append(fileIcon, info, remove); list.appendChild(row);
    });
    var total = state.files.reduce(function (sum, file) { return sum + file.size; }, 0);
    setText("fileCount", state.files.length); setText("totalSize", formatBytes(total));
    $("fileTools").hidden = !state.files.length; $("clearFiles").disabled = !state.files.length; $("startButton").disabled = !state.files.length || !!activeJob();
    var errorBox = $("uploadErrors"); errorBox.hidden = !(errors && errors.length); errorBox.textContent = errors && errors.length ? errors.join("；") : "";
    updatePairing(); refreshIcons(list);
  }
  function updatePairing() {
    var docs = state.files.filter(function (file) { return file.name.toLowerCase().endsWith(".docx"); }).length;
    var zips = state.files.length - docs, text = "";
    if (!state.files.length) text = "尚未添加素材";
    else if ($("docxMode").value === "auto" && docs === 2 && !zips) text = "两个 DOCX 按文件名与答案结构配对；已有学生版优先使用，不会再次去答案";
    else if (docs === 1 && !zips) text = "单个 DOCX 按文件名与答案结构判断：教师版会准备学生版；学生版只生成学生版";
    else if (zips && $("docxMode").value === "separate") text = "ZIP 会递归查找 DOCX，每份 DOCX 各自生成；临时文件会忽略，教师版会准备学生版，学生版只生成学生版";
    else if (zips) text = "ZIP 会递归查找 DOCX，并按同一专题的教师版与学生版可靠配对；临时文件会忽略，每个专题独立生成";
    else if (docs >= 3 && $("docxMode").value === "separate") text = "每份 DOCX 各自生成；教师版会准备学生版，学生版只生成学生版";
    else if (docs >= 3) text = "按专题名称配对教师版与学生版；未配对的教师版或学生版各自生成，单个专题失败不影响其他成品";
    else text = "两个 DOCX 请使用“按专题配对”，并提供同一专题的教师版与学生版；独立专题可使用 ZIP 或一次上传至少三份 DOCX";
    setText("pairingNote", text);
  }

  function isActiveStatus(status) { return status === "queued" || status === "running"; }
  function activeJob() { return state.jobs.find(function (job) { return isActiveStatus(job.status); }); }
  function beginElapsed(createdAt) {
    clearInterval(state.elapsedTimer); state.startedAt = createdAt ? createdAt * 1000 : Date.now();
    function tick() { var seconds = Math.max(0, Math.floor((Date.now() - state.startedAt) / 1000)); setText("elapsedLabel", Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0")); }
    tick(); state.elapsedTimer = setInterval(tick, 1000);
  }
  function statusCell(value) {
    var span = document.createElement("span"), icon = "minus", label = value || "—";
    span.className = "result-status";
    if (value === "完成" || value === "成功") { span.classList.add("done"); icon = "check-circle-2"; }
    else if (value === "处理中") { span.classList.add("running"); icon = "loader-circle"; }
    else if (value && value.indexOf("失败") === 0) { span.classList.add("error"); icon = "circle-alert"; }
    span.appendChild(makeIcon(icon)); span.appendChild(document.createTextNode(label));
    if (value === "处理中") span.firstChild.classList.add("spin");
    return span;
  }
  function showJob(job) {
    state.currentJob = job.job_id;
    $("idleState").hidden = true; $("progressWrap").hidden = false;
    var percent = job.total ? Math.round((job.progress || 0) / job.total * 100) : 0;
    if (job.status === "done") percent = 100;
    setText("progressPercent", percent + "%"); $("barfill").style.width = percent + "%"; $("progressTrack").setAttribute("aria-valuenow", percent);
    var title = job.status === "done" ? "讲义已生成" : job.status === "partial" ? "部分讲义已生成" : job.status === "error" ? (job.is_batch ? "全部专题生成失败" : "生成未完成") : job.status === "queued" ? "任务排队中" : "正在生成";
    setText("progressTitle", title); setText("progressStage", job.error || job.stage || job.current || "正在准备 Word 文档");
    setText("footerStatus", title); $("progressTrack").classList.remove("disconnected");
    $("batchSummary").hidden = !job.is_batch;
    if (job.is_batch) {
      setText("batchTotal", job.total || 0); setText("batchCompleted", job.completed || 0); setText("batchFailed", job.failed || 0);
      setText("batchCurrent", job.current_topic || (isActiveStatus(job.status) ? "等待处理" : "已结束"));
    }
    var rows = $("resultRows"); rows.replaceChildren();
    (job.items || []).forEach(function (item) {
      var tr = document.createElement("tr"), topic = document.createElement("td"), teacher = document.createElement("td"), student = document.createElement("td"), renderer = document.createElement("td"), status = document.createElement("td");
      topic.textContent = item.topic || "识别中"; teacher.appendChild(statusCell(item.teacher)); student.appendChild(statusCell(item.student));
      var itemRenderer = item.renderer || (!job.is_batch && job.renderer);
      var itemStatus = item.status || job.status;
      var itemRoute = item.renderer_route || (!job.is_batch && job.renderer_route);
      renderer.textContent = itemRenderer === "XML" ? "XML 受限模式" : itemRenderer === "XML_UNSUPPORTED" ? "XML 不支持" : itemRenderer === "V0.9" ? (itemRoute === "STABLE_V09" ? "稳定模式（V0.9）" : "V0.9 回退") : itemStatus === "error" ? "未执行" : "待确定";
      if (item.renderer_reason_code || (!job.is_batch && job.renderer_reason_code)) renderer.title = "XML 未支持：" + (item.renderer_reason_code || job.renderer_reason_code) + (job.renderer_reason_detail ? "；" + job.renderer_reason_detail : "");
      else if (item.fallback_reason || (!job.is_batch && job.fallback_reason)) renderer.title = "回退原因：" + (item.fallback_detail || item.fallback_reason || job.fallback_reason);
      status.appendChild(statusCell(itemStatus === "done" ? "成功" : itemStatus === "error" ? "失败" : itemStatus === "running" ? "处理中" : "等待中"));
      if (item.error) status.title = item.error;
      tr.append(topic, teacher, student, renderer, status); rows.appendChild(tr);
    });
    var warnings = $("warnings"); warnings.hidden = !(job.warnings && job.warnings.length); warnings.textContent = job.warnings && job.warnings.length ? job.warnings.join("；") : "";
    var delivery = $("resultDelivery");
    delivery.hidden = !job.has_result;
    if (job.has_result) {
      var pathText = job.result_dir ? "本地输出路径：" + job.result_dir + "。" : "成品已保存在本地结果目录。";
      var generatedText = job.status === "partial" ? "已成功生成 " + job.completed + " 个专题，" + job.failed + " 个失败。成功成品已通过校验，不受失败项影响。" : isActiveStatus(job.status) ? "已完成专题的成品已保存并通过校验，其余专题正在处理。" : "成品已生成并通过校验。";
      delivery.textContent = generatedText + pathText + "可打开成品文件夹获取已完成的 DOCX。";
    } else { delivery.textContent = ""; }
    $("openResult").hidden = !job.has_result; $("reconnect").hidden = true;
    $("configFields").disabled = isActiveStatus(job.status); $("startButton").disabled = isActiveStatus(job.status) || !state.files.length;
    if (isActiveStatus(job.status)) beginElapsed(job.created_at);
    else { clearInterval(state.elapsedTimer); setText("elapsedLabel", job.produced ? "共 " + job.produced + " 份" : ""); localStorage.removeItem("handout_current_job"); }
    refreshIcons(rows); renderHistory();
  }
  function pollJob(jobId, immediate) {
    clearTimeout(state.pollTimer);
    function poll() {
      requestJson("/api/jobs/" + jobId).then(function (job) {
        setConnected(true); upsertJob(job); showJob(job);
        if (isActiveStatus(job.status)) state.pollTimer = setTimeout(poll, 1200);
      }).catch(function (error) {
        setConnected(false); $("progressTrack").classList.add("disconnected"); $("reconnect").hidden = false;
        setText("progressStage", error.message); refreshIcons($("progressWrap"));
      });
    }
    if (immediate) poll(); else state.pollTimer = setTimeout(poll, 1200);
  }
  function upsertJob(job) {
    var index = state.jobs.findIndex(function (item) { return item.job_id === job.job_id; });
    if (index >= 0) state.jobs[index] = job; else state.jobs.unshift(job);
  }
  function startJob(event) {
    event.preventDefault(); if (!state.files.length || activeJob()) return;
    var button = $("startButton"); button.disabled = true; setText("footerStatus", "正在上传素材");
    var data = new FormData(); state.files.forEach(function (file) { data.append("files", file); });
    data.append("subject", state.selectedSubject); data.append("grade", $("gradeSelect").value); data.append("handout_type", $("handoutType").value); data.append("academic_year", $("academicYear").value); data.append("template_type", state.templateType); data.append("engine_mode", state.engineMode); data.append("split_mode", $("splitMode").value); data.append("docx_mode", $("docxMode").value);
    requestJson("/api/jobs", {method: "POST", body: data}).then(function (response) {
      state.currentJob = response.job_id; localStorage.setItem("handout_current_job", response.job_id); beginElapsed();
      upsertJob(response); showJob(response);
      pollJob(response.job_id, false);
    }).catch(function (error) {
      button.disabled = false; setText("footerStatus", "就绪"); toast(error.message);
      if (error.data && error.data.job_id) { localStorage.setItem("handout_current_job", error.data.job_id); pollJob(error.data.job_id, true); }
    });
  }
  function setConnected(connected) {
    document.querySelector(".status-dot").classList.toggle("offline", !connected);
    setText("connectionLabel", connected ? "本地服务" : "连接中断");
  }
  function loadJobs() {
    return requestJson("/api/jobs").then(function (data) {
      state.jobs = data.jobs || []; setConnected(true); renderHistory();
      var stored = localStorage.getItem("handout_current_job"), active = state.jobs.find(function (job) { return isActiveStatus(job.status); });
      var target = state.jobs.find(function (job) { return job.job_id === stored; }) || active;
      if (target) { showJob(target); if (isActiveStatus(target.status)) pollJob(target.job_id, false); }
    }).catch(function () { setConnected(false); renderHistory(); });
  }

  function renderHistory() {
    setText("historyCount", state.jobs.length);
    var recent = $("recentTasks"); recent.replaceChildren();
    state.jobs.slice(0, 4).forEach(function (job) {
      var button = document.createElement("button"); button.className = "recent-task"; button.appendChild(makeIcon(job.status === "done" ? "file-check-2" : isActiveStatus(job.status) ? "loader-circle" : "file-warning"));
      var label = document.createElement("span"); label.textContent = job.filenames && job.filenames[0] ? job.filenames[0] : "讲义任务"; button.appendChild(label); button.addEventListener("click", function () { navigate("history"); }); recent.appendChild(button);
    });
    if (!state.jobs.length) { var empty = document.createElement("p"); empty.className = "sidebar-empty"; empty.textContent = "暂无任务"; recent.appendChild(empty); }
    var query = $("historySearch").value.trim().toLowerCase(), filter = $("historyFilter").value, list = $("historyList"); list.replaceChildren();
    var visible = state.jobs.filter(function (job) {
      var haystack = ((job.filenames || []).join(" ") + " " + ((job.options || {}).subject || "")).toLowerCase();
      return (!query || haystack.indexOf(query) >= 0) && (filter === "all" || job.status === filter);
    });
    visible.forEach(function (job) {
      var row = document.createElement("article"); row.className = "history-row";
      var icon = document.createElement("span"); icon.className = "file-icon"; icon.appendChild(makeIcon(job.status === "done" ? "file-check-2" : isActiveStatus(job.status) ? "loader-circle" : "file-warning"));
      var main = document.createElement("button"); main.className = "history-main";
      var title = document.createElement("strong"); title.textContent = job.filenames && job.filenames.length ? job.filenames.join("、") : "讲义任务";
      var meta = document.createElement("p"), options = job.options || {}; meta.textContent = [options.grade, options.subject, options.handoutType, formatDate(job.created_at)].filter(Boolean).join(" · "); main.append(title, meta); main.addEventListener("click", function () { navigate("workspace"); showJob(job); if (isActiveStatus(job.status)) pollJob(job.job_id, true); });
      var status = document.createElement("span"); status.className = "history-state " + job.status; status.textContent = job.status === "done" ? "已完成" : job.status === "partial" ? "部分完成" : job.status === "queued" ? "排队中" : job.status === "running" ? "生成中" : "未完成";
      var actions = document.createElement("div"); actions.className = "history-actions";
      if (job.has_result) {
        var open = document.createElement("button"); open.className = "icon-button"; open.setAttribute("aria-label", "打开成品位置"); open.dataset.tooltip = "成品位置"; open.appendChild(makeIcon("folder-open")); open.addEventListener("click", function () { openJob(job.job_id); }); actions.appendChild(open);
      }
      row.append(icon, main, status, actions); list.appendChild(row);
    });
    if (!visible.length) { var emptyView = document.createElement("div"); emptyView.className = "empty-view"; emptyView.appendChild(makeIcon("inbox")); var message = document.createElement("p"); message.textContent = state.jobs.length ? "没有符合条件的任务" : "生成完成的讲义会出现在这里"; emptyView.appendChild(message); list.appendChild(emptyView); }
    refreshIcons(recent); refreshIcons(list);
  }
  function openJob(jobId) { requestJson("/api/open/" + jobId).then(function (result) { toast("已打开成品文件夹：" + result.result_dir); }).catch(function (error) { toast(error.message); }); }

  function navigate(view) {
    ["workspace", "history", "templates"].forEach(function (name) { $(name + "View").hidden = name !== view; });
    document.querySelectorAll("[data-view]").forEach(function (button) { var active = button.dataset.view === view; button.classList.toggle("active", active); if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current"); });
    setText("viewTitle", view === "workspace" ? "工作区" : view === "history" ? "生成记录" : "讲义模板");
    if (view === "history") loadJobs();
  }
  function newTask() {
    if (activeJob()) { navigate("workspace"); toast("当前讲义生成完成后即可开始新任务"); return; }
    state.files = []; state.undo = []; $("fileSearch").value = ""; $("undoFiles").disabled = true; renderFiles();
    $("idleState").hidden = false; $("progressWrap").hidden = true; state.currentJob = null; clearInterval(state.elapsedTimer); setText("elapsedLabel", ""); setText("footerStatus", "就绪"); navigate("workspace");
  }

  function openPreview(template) {
    state.previewTemplate = template || state.templateType;
    var isClass = state.previewTemplate === "class";
    setText("previewTitle", isClass ? "班课讲义模板" : "1 对 1 讲义模板");
    $("previewImage").src = "/static/previews/" + (isClass ? "class" : "1v1") + ".png";
    $("previewImage").alt = (isClass ? "班课" : "1 对 1") + "讲义模板首页";
    $("templatePdf").href = "/static/previews/" + (isClass ? "class" : "1v1") + ".pdf";
    $("previewDialog").showModal();
  }

  function effectiveTheme(theme) {
    return theme === "system" ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : theme;
  }
  function applyTheme(theme) {
    localStorage.setItem("handout_theme", theme); $("themeSelect").value = theme;
    var effective = effectiveTheme(theme); document.documentElement.dataset.theme = effective;
    var button = $("themeButton"); button.replaceChildren(makeIcon(effective === "dark" ? "sun" : "moon")); button.setAttribute("aria-label", effective === "dark" ? "切换浅色外观" : "切换深色外观"); refreshIcons(button);
  }

  function bindEvents() {
    $("drop").addEventListener("click", function () { $("fileInput").click(); });
    $("fileInput").addEventListener("change", function () { addFiles(this.files); this.value = ""; });
    ["dragenter", "dragover"].forEach(function (name) { $("drop").addEventListener(name, function (event) { event.preventDefault(); $("drop").classList.add("dragover"); }); });
    ["dragleave", "drop"].forEach(function (name) { $("drop").addEventListener(name, function (event) { event.preventDefault(); $("drop").classList.remove("dragover"); }); });
    $("drop").addEventListener("drop", function (event) { addFiles(event.dataTransfer.files); });
    $("clearFiles").addEventListener("click", clearFiles); $("undoFiles").addEventListener("click", undoFiles); $("fileSearch").addEventListener("input", function () { renderFiles(); });
    $("docxMode").addEventListener("change", function () { configChanged(); updatePairing(); });
    $("engineMode").addEventListener("change", function () { state.engineMode = this.value; updateEngineModeNote(); configChanged(); });
    $("eduLevel").addEventListener("change", function () { updateGrades(); configChanged(); });
    ["gradeSelect", "handoutType", "academicYear", "splitMode"].forEach(function (id) { $(id).addEventListener("change", configChanged); });
    document.querySelectorAll("[data-template]").forEach(function (button) { button.addEventListener("click", function () { setTemplate(button.dataset.template); }); });
    $("configForm").addEventListener("submit", startJob); $("openResult").addEventListener("click", function () { if (state.currentJob) openJob(state.currentJob); }); $("reconnect").addEventListener("click", function () { if (state.currentJob) pollJob(state.currentJob, true); });
    document.querySelectorAll("[data-view]").forEach(function (button) { button.addEventListener("click", function () { navigate(button.dataset.view); }); });
    $("newTask").addEventListener("click", newTask); $("refreshHistory").addEventListener("click", loadJobs); $("historySearch").addEventListener("input", renderHistory); $("historyFilter").addEventListener("change", renderHistory);
    $("settingsButton").addEventListener("click", function () { $("settingsDialog").showModal(); });
    var exitApplication = $("exitApplication");
    if (exitApplication) exitApplication.addEventListener("click", function () {
      var token = document.querySelector('meta[name="launcher-token"]').content;
      requestJson("/api/launcher/shutdown", {method: "POST", headers: {"X-Launcher-Token": token}})
        .then(function () { $("settingsDialog").close(); toast("讲义生成器正在安全退出"); })
        .catch(function (error) { toast(error.message); });
    });
    $("themeButton").addEventListener("click", function () { applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"); });
    $("themeSelect").addEventListener("change", function () { applyTheme(this.value); });
    $("compactFiles").addEventListener("change", function () { applyCompact(); savePrefs(); });
    $("resetConfig").addEventListener("click", function () { $("eduLevel").value = "高中"; updateGrades("高一"); $("handoutType").value = "复习讲义"; $("academicYear").value = academicYear(); $("engineMode").value = "stable_v09"; state.engineMode = "stable_v09"; updateEngineModeNote(); $("splitMode").value = "smart"; $("docxMode").value = "auto"; selectSubject("数学", true); setTemplate("1v1", true); configChanged(); updatePairing(); toast("已恢复默认配置"); });
    $("previewButton").addEventListener("click", function () { openPreview(state.templateType); });
    document.querySelectorAll("[data-preview]").forEach(function (button) { button.addEventListener("click", function () { openPreview(button.dataset.preview); }); });
    document.querySelectorAll("[data-use-template]").forEach(function (button) { button.addEventListener("click", function () { setTemplate(button.dataset.useTemplate); navigate("workspace"); }); });
    $("closePreview").addEventListener("click", function () { $("previewDialog").close(); });
    $("usePreviewTemplate").addEventListener("click", function () { setTemplate(state.previewTemplate); $("previewDialog").close(); navigate("workspace"); });
  }

  function initialize() {
    initializeOptions(); loadPrefs(); bindEvents();
    setText("todayLabel", new Intl.DateTimeFormat("zh-CN", {month: "long", day: "numeric", weekday: "long"}).format(new Date()));
    applyTheme(localStorage.getItem("handout_theme") || "system"); updateFilename(); updateSplitExplainer(); updateEngineModeNote(); renderFiles(); refreshIcons(); loadJobs();
  }
  document.addEventListener("DOMContentLoaded", initialize);
}());
