# Windows Word UAT checklist

Run this only after the corpus XML run has produced isolated outputs and a
JSON/CSV evidence report. Work on output copies; never edit source corpus files
or the stable v1.1 template.

For each report row:

- [ ] Output exists and `package_validation.valid` is true with zero errors.
- [ ] If selected source blocks contain OLE embeddings, all expected SHA256
      hashes appear in output; any missing or changed hash is a blocker.
- [ ] Open the output in Microsoft Word with repair disabled. Record whether
      Word reports unreadable content or requests repair.
- [ ] Save to a separate UAT copy, close Word, reopen that saved copy, and
      record any error or repair prompt.
- [ ] Visually compare source and output: no silent body omissions; check
      paragraph order, tables, images, Chinese characters, numbering, OMML,
      MathType/OLE display, page breaks, and layout.
- [ ] Record the Word build, Windows version, template path, sample id, and
      pass/fail observations next to the generated report.

Word opening and saving successfully is necessary but does not replace visual
review. A dummy OLE fixture or matching embedding hash is not MathType render
verification. Do not mark the real-corpus engine gate PASS until every
supported sample has validator-zero-error output, no Word repair prompt,
retained content, and verified OLE/render results.
