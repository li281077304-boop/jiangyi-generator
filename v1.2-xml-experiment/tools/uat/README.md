# v1.2 real-corpus UAT preparation

This folder prepares the next Windows UAT; it does not contain or copy user
documents. The example manifest contains only a placeholder path. The Mac
preparation stage may inventory names/sizes, but must not open or generate from
real corpus files. Programmatic DOCX fixtures test the evidence helpers only.

## Safe default

`corpus_uat.py` is metadata-only unless `--run` is explicitly supplied. Dry
run checks the selected manifest paths and file sizes without opening DOCX
packages or creating outputs:

```powershell
python v1.2-xml-experiment/tools/uat/corpus_uat.py `
  --manifest v1.2-xml-experiment/tools/uat/corpus_manifest.example.json `
  --corpus-root D:\LectureCorpus `
  --repo-root .
```

Before a run, copy the example manifest to a private location, select 8–10
real teacher handouts, set source paths relative to the corpus root, choose a
read-only template path, and fill in each sample's cover metadata. The stable
v1.1 template may be read as a reference; nothing writes into `v1.1-stable`.

## Explicit XML run

The corpus source remains read-only. `--output-dir` and `--report-dir` are
required, must be empty/new, and must sit outside both the repository and the
corpus tree. Each sample gets a unique output directory. The runner records
source/template/output sizes, selected block counts, package relationship and
style/numbering references, validator report, generation time, and selected
OLE embedding SHA256 comparison. It rejects an output path overlapping
`v1.1-stable`.

```powershell
python v1.2-xml-experiment/tools/uat/corpus_uat.py `
  --manifest C:\xml-uat\corpus.json `
  --corpus-root D:\LectureCorpus `
  --repo-root . `
  --output-dir C:\xml-uat\outputs `
  --report-dir C:\xml-uat\reports `
  --run
```

`XML_PACKAGE_PASS_WORD_UAT_PENDING` means only that generation, OLE package
hash checks (when applicable), and package validation passed. It is not a Word
rendering pass. A non-empty failed record fails closed and receives a failure
category. Reports are written as JSON and CSV.

## Required Word checks

For every generated output, use Microsoft Word on a copy of the output: open
with repair disabled, verify there is no repair prompt, save to a separate
copy, close, and reopen. Check images, tables, numbering, Chinese text, OMML,
and MathType/OLE appearance. Record open/save/reopen errors and do a human
visual review. An unchanged embedding SHA256 proves package bytes were
preserved; it does not prove Word can render a MathType object.

Current host was macOS and had no Microsoft Word, `pwsh`, or `powershell`.
Consequently this preparation stage must not be reported as real-corpus UAT,
MathType UAT, or Word UAT.

## Mac-side corpus availability check (2026-09-28)

Only directory entries and file sizes were inspected; no DOCX package was
opened or generated. `/Users/macos/Documents/05-讲义教材` contains 1,677 DOCX
files. `教学与讲义/暑期讲义检查` contains 222 DOCX files (88 filenames
matched the current teacher-version name filter; this is a candidate heuristic,
not package verification). The v1.2 experiment directory has no real DOCX
corpus. The Windows preflight must select 8–10 samples by actual package
features and then retain their report manifest; the Mac name/size inventory
does not establish OLE, VML, OMML, or numbering coverage.
