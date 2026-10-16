# Q0030 — Post-certification ACEB authority-pin maintenance — 2026-10-15

Status: bounded maintenance candidate.

Purpose: refresh the Rosetta Research Workbench canonical ACEB modification-time pin after legitimate post-certification ACEB registry updates. This maintenance preserves `FAIL_CLOSED_ON_PIN_DRIFT` and does not reopen or alter the historical 2026-10-15 Workbench Phase I live-authenticated PASS.

Verified authority facts at preparation time:

- ACEB: `Animal Rosetta Stone — Experimental Evidence Bank v1.0`
- Spreadsheet ID: `1OXXnv9Q5Gse3D-r9EZNSR9H8FXugiHyRqndF3pv9czQ`
- Current Drive `modifiedTime`: `2026-10-15T23:57:56.888Z`
- Prior manifest pin: `2026-10-14T18:44:27.107Z`
- Base canonical main before maintenance: `d68c796b737f2a3caf085ec96777bae7a5cf73eb`

Scope is intentionally narrow: only the ACEB durable `observed_modified_time` pin changes in `src/ars_workbench/data/workbench_canonical_sources.json`. No scientific content, event counts, source selection, evidence states, rights conclusions, claim ceilings, or Workbench presentation logic change in this maintenance.

Required disposition before merge:

1. exact-head CI/verification passes;
2. no unexpected authority drift appears;
3. changed-file review confirms one semantic change to the ACEB modification-time pin;
4. if a current authenticated Workbench snapshot is required, produce a fresh private live receipt after merge; otherwise retain the historical Phase I receipt as certification evidence and treat this PR as freshness maintenance only.

If any unexpected authority or scientific-content drift is discovered, fail closed and do not broaden this maintenance PR to absorb unrelated changes.
