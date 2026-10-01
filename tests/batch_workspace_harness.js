"use strict";
// Execute the real private workbench functions against a small in-memory DOM.
// This is a focused state-mapping test, not browser or real application UAT.
const fs = require("node:fs");
const vm = require("node:vm");
const input = JSON.parse(fs.readFileSync(0, "utf8"));

class Element {
  constructor(tag) {
    this.tag = tag; this.children = []; this._text = ""; this.hidden = false;
    this.value = ""; this.dataset = {}; this.style = {}; this.attrs = {};
    this.className = "";
    this.classList = {add() {}, remove() {}, toggle() {}};
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(node => node.textContent).join(""); }
  appendChild(node) { this.children.push(node); return node; }
  append(...nodes) { nodes.forEach(node => this.appendChild(node)); }
  replaceChildren(...nodes) { this.children = []; this._text = ""; this.append(...nodes); }
  setAttribute(key, value) { this.attrs[key] = String(value); }
  removeAttribute(key) { delete this.attrs[key]; }
  addEventListener() {}
  get firstChild() { return this.children[0]; }
}
const nodes = new Map();
function element(id) {
  if (!nodes.has(id)) nodes.set(id, new Element("div"));
  return nodes.get(id);
}
element("docxMode").value = input.mode || "auto";
element("historyFilter").value = input.historyFilter || "all";
element("academicYear").value = "2026-2027学年";
element("gradeSelect").value = "高一";
element("handoutType").value = "复习讲义";
element("splitMode").value = "smart";
const stored = new Map([["handout_current_job", "initial"]]);
const requests = [];
class FormData {
  constructor() { this.entries = []; }
  append(name, value) { this.entries.push([name, value]); }
}
const context = {
  document: {
    getElementById: element, createElement: tag => new Element(tag),
    createTextNode: text => { const node = new Element("text"); node.textContent = text; return node; },
    querySelectorAll: () => [], querySelector: element, addEventListener() {}
  }, window: {}, Intl, Date, Math, FormData,
  localStorage: {getItem: key => stored.get(key), setItem: (key, value) => stored.set(key, value),
                 removeItem: key => stored.delete(key)},
  setInterval: () => 1, clearInterval() {}, setTimeout: () => 1, clearTimeout() {},
  fetch: (url, options) => {
    requests.push({url, files: options.body.entries.filter(item => item[0] === "files").map(item => item[1].name)});
    return Promise.resolve({ok: true, json: () => Promise.resolve(input.submitResponse)});
  }
};
let source = fs.readFileSync(process.argv[2], "utf8");
source = source.replace("document.addEventListener(\"DOMContentLoaded\", initialize);",
  "globalThis.testUI = {showJob: showJob, upsertJob: upsertJob, addFiles: addFiles, startJob: startJob};");
vm.runInNewContext(source, context);

async function run() {
  if (input.files) context.testUI.addFiles(input.files.map(name => ({name, size: 100})));
  for (const job of input.extraJobs || []) context.testUI.upsertJob(job);
  if (input.job) { context.testUI.upsertJob(input.job); context.testUI.showJob(input.job); }
  if (input.submitResponse) {
    context.testUI.startJob({preventDefault() {}});
    // Drain the fetch→JSON→showJob promise chain without invoking timer polling.
    await new Promise(resolve => setImmediate(resolve));
  }
  const result = {
    title: element("progressTitle").textContent,
    percent: element("progressPercent").textContent,
    batchHidden: element("batchSummary").hidden,
    total: element("batchTotal").textContent, completed: element("batchCompleted").textContent,
    failed: element("batchFailed").textContent, current: element("batchCurrent").textContent,
    rows: element("resultRows").children.map(row => row.children.map(cell => cell.textContent)),
    deliveryHidden: element("resultDelivery").hidden, delivery: element("resultDelivery").textContent,
    openHidden: element("openResult").hidden,
    downloadElements: [...nodes.values()].filter(node => (node.href || "").startsWith("/api/download/")).length + Number(nodes.has("downloadResult")),
    configDisabled: element("configFields").disabled, startDisabled: element("startButton").disabled,
    pairing: element("pairingNote").textContent,
    historyStatuses: element("historyList").children.filter(row => row.children.length === 4)
      .map(row => row.children[2].textContent),
    currentStored: stored.has("handout_current_job"), requests
  };
  process.stdout.write(JSON.stringify(result));
}
run().catch(error => { process.stderr.write(error.stack); process.exitCode = 1; });
