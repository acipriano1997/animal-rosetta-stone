# D0029 RDC-006 original audit recovery — verified archive, bounded tests

**Date:** 2026-10-19 (US Eastern)  
**Historical Git source commit:** `1553c60c4ec222c8305dbee02d098d8c1688515e` (founder-local branch `ars/d0029-source-history-v0.1`)  
**Scientific admission:** `HELD_RDC006_SCHEMA_TIMING_DEPENDENCE_REVIEW` — **UNCHANGED**  
**Remote reconstruction:** original eight audit files are **NOT yet restored** to current GitHub `main`.

## Private recovered archive

The founder exported exactly eight original audit/source-history artifacts using `git archive`; the uploaded Git ZIP was independently inspected and backed up to the canonical **personal**, not studio, private raw immutable Drive folder. It is **not** a Figshare original raw-data archive.

- ZIP: `ARS_D0029_original_1553c60c.zip`; size **159,401 bytes**
- ZIP SHA-256: `d018e8338326a8fd2874a3765becfa94e6244996dde2eb0daf003cc19ec7f831`
- Git ZIP embedded source commit: `1553c60c4ec222c8305dbee02d098d8c1688515e`
- ZIP integrity: **PASS**; independent private Drive re-download: **159,401 bytes, exact SHA-256 match**; Google reported `shared=false`.
- The private Drive object identifier and any original row-level source material are deliberately omitted from this public checkpoint.

| Original path | SHA-256 | Bytes |
| --- | --- | ---: |
| `contracts/d0029_rdc006_v4_crosswalk.json` | `06ded4663eec6fae94e4320f5bb0d9a54174fd327e8565935a6cd826a1a1daa7` | 1301720 |
| `contracts/d0029_version_history_source_snapshot.json` | `696dbd94d2b8511c545e961b428be7a159286253ca48e7ae19e2e02af719dc7a` | 308963 |
| `docs/d0029_rdc006_v4_admission.md` | `0e4e8852db87fb3c0574a98e1978126991415f0defccbbc429628848dac4c4f5` | 17141 |
| `docs/d0029_source_history_admission.md` | `2cbfc057baa0fbd7f89acc566ef459db6839355e681deb73593d1085360ed93d` | 15242 |
| `scripts/audit_d0029_rdc006.py` | `03a4fb9f3a7b03a3f8aa3cb7d3115b7093e17f63cc6c7f1eca3bdca3135bc68a` | 48327 |
| `scripts/probe_d0029_source_history.py` | `0918eddaa9fdc2cf50425fdfebe271c6dc52e1588a1b98ca6c0d925f2512fb93` | 26197 |
| `tests/test_d0029_rdc006.py` | `37d558414e426f7aba55cbbbd33eb53075fd1f0a98e37aae67c9f565330f659c` | 11001 |
| `tests/test_d0029_source_history.py` | `1e9839352a1786aafcb922ce043b7f3f0ac574096ce5e43890f1ef30336aa2df` | 10457 |

## Inspected frozen receipt and tests

Crosswalk `active_source` identifies Figshare `10.6084/m9.figshare.16910173.v4` file `36230763`; its `active_source.source_snapshot_sha256` exactly equals the independently measured SHA-256 of the recovered source-history JSON. The original crosswalk explicitly declares `admission.granted=false`. Its **321** field classifications have **zero** `baseline_eligible=true`. Historical descriptive cardinalities in that frozen receipt match the canonical ACEB summary. The six-exclusion ledger explicitly states not all six are reproducible.

**Isolated test receipt:** Python 3.13 / pytest 9.0.2, no third-party pytest plugins, exact original audit/script/test files unchanged. A missing shared dependency `scripts/inspect_d0025_headers.py` (not in the eight-file export) required a review-only matching helper-function subset transcribed from current GitHub `main`, blob `06da1a961040543bebad2e22142a8c7f927c98f2`. Initial isolated collection failed due that omitted helper; with it, **58 PASSED, 1 SKIPPED**. The skip is `test_cached_v4_regenerates_frozen_receipt_exactly_when_available` because original Figshare v4 source bytes are absent from the recovered ZIP/test runtime.

**What these tests DO NOT establish:** full rerun of Figshare v4 data, author GLMM or deposited R scripts; resolution of R0013 mismatched keys, timing origin, five-minute coverage or exclusion ledger; causal or semantic claims; permission to redistribute third-party audio/video. No actual raw research rows/media were committed by this validation.

## Main-path next gates

1. Use founder-local exact Git tree to restore **only reviewed** original audit/source-history artifacts on a new non-destructive branch of current remote main. Inspect original event-level source locators and confirm Figshare v4 item-level CC BY attribution and any file-specific caveats before public release. Do **not** cherry-pick the historical README or merge divergent old history.
2. Run the restored audit unit tests in the full current project environment; inspect exact PR diff and CI, and retain the source original SHA receipts.
3. Recover and verify original Figshare v4 source archives for the one skipped end-to-end regeneration test, if access permits. This is required to claim regenerated dataset-level results, not to establish original audit artifact fixity.
4. Resolve R0013 source-author joins, timestamp semantics, full observation coverage and six exclusions. **Until then: empirical admission HELD**, no receiver negative inference and no semantic promotion.

This source-free checkpoint preserves continuity with prior [recovery PR #67](https://github.com/acipriano1997/animal-rosetta-stone/pull/67) and [correction PR #68](https://github.com/acipriano1997/animal-rosetta-stone/pull/68).
