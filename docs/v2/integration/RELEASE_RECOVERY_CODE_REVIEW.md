# Release Recovery independent code review

Date: 2026-10-08 (Asia/Shanghai).

Reviewer: Codex GPT-6.1 Sol, independent read-only subagent
`/root/recovery_code_review`. Worker: GPT-6 Luna. Reviewed the working-tree
candidate based on `a7c37d8e0c55322b3d90246aa1117eb0065c02f2`.

Decision: **PASS for code scope; real release acceptance remains pending.**

No concrete P0/P1 blocker was found in:

- Default `stable_v09` selection and propagation to batch children.
- Direct frozen V0.9 generation; XML explicitly refuses unsupported inputs
  without switching engines.
- Teacher-only preparation, supplied pairs, student-only role dispatch.
- Persisted missing-metadata warnings and validated local publication.
- Module-local subprocess proxy without process-wide subprocess mutation.
- Restored frozen runtime asset bytes: independently checked 10/10 hashes,
  including `handout.py` SHA-256
  `e35a45e871acbacb8f3e3c8da297c141e9bcf6e083fa1136171480dced92ce6d`.
- Packaging helper and frozen template allowlist/hash checks.

The reviewer did not edit files, run tests, invoke COM, or build an EXE.
This review does not establish Windows/WPS layout correctness or portable
package usability. Those must be recorded by the actual Gate A/B/C evidence.
