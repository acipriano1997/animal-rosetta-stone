# D0029 RDC-006 — source attribution and bounded public audit scope

**Source work:** Heesen, R., Austry, D. A., Upton, Z., & Clay, Z. (2022). *Flexible signalling strategies by victims mediate post-conflict interactions in bonobos.* Philosophical Transactions of the Royal Society B: Biological Sciences, 377, 20210310. https://doi.org/10.1098/rstb.2021.0310

**Cited deposited research object:** Figshare item **16910173, version 4**, https://doi.org/10.6084/m9.figshare.16910173.v4; analysis archive file **36230763**, `Data and R code.zip`.

**Rights as exposed by the frozen source record:** Figshare **item-level CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/). **A separate file-level licence was not exposed** in the original source manifest. This record does not assert an independently verified file-specific grant, alter source authorship, or supersede narrower third-party rights if subsequently identified. Please preserve attribution and identify changes when reusing adapted source-derived elements.

## What is restored here

The following were created as an **ARS descriptive source audit and adaptation**, not as the publication's raw dataset or author statistical results:

- `contracts/d0029_rdc006_v4_crosswalk.json` — source-derived keys, join candidates, row locators, conflict records and candidate field eligibility restrictions;
- `contracts/d0029_version_history_source_snapshot.json` — original archive versions and member hashes;
- `docs/d0029_rdc006_v4_admission.md` and `docs/d0029_source_history_admission.md` — historical source reconciliation and scientific restrictions;
- `scripts/audit_d0029_rdc006.py`, `scripts/probe_d0029_source_history.py` and corresponding tests — ARS-created audit code, not the deposited authors' R analytical code.

**Modifications relative to source:** ARS inventoried version history, verified archived source-file identities in the historical audit environment, analyzed file/bout/receiver crosswalk candidates, and preserved source ambiguities and timestamp/missingness constraints. The restored files are unchanged bytes from ARS historical Git commit `1553c60c4ec222c8305dbee02d098d8c1688515e`; restoration does not alter the source publisher's data.

**Not present in this GitHub restoration:** unmodified Figshare research archives, ELAN media/video/audio, complete raw trial/annotation tables, or a rerun of the deposited inferential R code. The source-derived crosswalk does identify individual animal codes, source event/bout IDs, filenames and timing ranges; it must not be mistaken for a deidentified statistical aggregate.

## Reproducibility and scientific ceiling

An independently validated private ZIP backup preserves the eight historical files (ZIP SHA-256 `d018e8338326a8fd2874a3765becfa94e6244996dde2eb0daf003cc19ec7f831`). The original eight Git blob IDs were each checked against the uploaded branch. Bounded historical tests passed **58**, with **1 skipped** for lack of the exact raw Figshare-v4 archive needed for end-to-end regeneration. The skipped test is **not a pass**.

The contract's `admission.granted` remains `false`; no fields are eligible as baseline predictors, and R0013/RDC-006 unresolved linkage, five-minute observation coverage, timestamp origin, exclusion mapping and downstream-outcome restrictions remain **HELD**. No meaning/semantic/compositionality conclusion, causal claim, or species-general result is established by making an audit receipt accessible.

Any rights concern, provenance discrepancy, or independently verified replacement source version should trigger separate explicit review before further source-derived public distribution. Do not silently amend this historical audit's original blobs.
