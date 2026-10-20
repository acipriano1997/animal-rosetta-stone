# D0029 v4 RDC-006 timing, coverage and dependence review

Disposition: `D0029_ADMISSION=HELD_RDC006_SCHEMA_TIMING_DEPENDENCE_REVIEW`.
Source location and byte verification are complete; event eligibility is not.
`SEMANTIC_COMPOSITIONALITY=CONTESTED_UNRESOLVED` and
`EMPIRICAL_CONFIRMATORY_RUN=NOT_STARTED` remain unchanged. No deposited R code,
inferential model, or confirmatory RQ0005 analysis was executed.

The [machine-readable crosswalk](../contracts/d0029_rdc006_v4_crosswalk.json)
extends the twenty existing RDC-006 fields pinned in the
[source-history receipt](../contracts/d0029_version_history_source_snapshot.json).
It contains exact member names, sizes, MD5/SHA256, worksheet/header inventories,
missingness, candidate-key tests, joins in both directions, source row locators,
static R line snippets, and variable classifications. It is descriptive provenance,
not an admitted or repaired empirical corpus. Research archives remain in ignored
`build/`; no production tables are added to Git.

## Active package and provenance

Only item **16910173 v4**, DOI **10.6084/m9.figshare.16910173.v4**, archive
**36230763 / Data and R code.zip** supplies this review. Its MD5 is
`a7062549780317524cf0ffb2826f3b64`; SHA256 is
`7bbc28be52c24b6c8ada435838b671dea7bcaaff10d709206b04a2e62e577a10`.
The source snapshot's SHA256 remains
`696dbd94d2b8511c545e961b428be7a159286253ca48e7ae19e2e02af719dc7a`.
All archive members are reverified against that snapshot before inspection.
Item-level CC BY 4.0 is exposed; no separate file-level licence is exposed or inferred.
No historical v1–v3 bytes are used.

R0011 remains the historical incomplete-manifest observation. R0012 is the active
source-location correction supplied by the canonical user handoff. This repository
review neither invents a semantic-registry row nor changes the historical receipt.
The cause of the earlier ten-file observation remains unverified and outside scope.
R0010 and unrelated gates are unchanged.

## Frozen files and tables

Counts below describe deposited structure. Exact headers and hashes are in
`source_inventory`. Workbook header candidates are not promoted to semantic
codebooks; the multilevel Sheet1 cannot be treated as a flat observation table.

| Exact file | Table/sheet and rows × named columns | Apparent level |
|---|---|---|
| processed_dataset.txt | 469 × 43 | 144 displays + 325 bouts |
| processed_dataset.xlsx | processed_dataset: 469 × 43 | Same levels; native serialized values preserved |
| data_victimsignalling.txt | 469 × 59 | Display/bout export with demographic and binary fields |
| data_victimsignalling_BoutAso.txt | 329 × 60 | Preconstructed receiver-dependent bout/persistence table |
| raw_data_signaltypes_below5min.xlsx | raw_data_signaltypes: 9051 × 44; extent 45 | Sparse raw rows/annotation tiers, including receivers, components, bouts, displays and metadata |
| demographic_info.txt | 42 × 6 | Static individual metadata |
| BinaryPCons.txt | 44 × 6 | Derived individual/style/outcome summary |
| BinaryPRec.txt | 44 × 6 | Derived individual/style/outcome summary |
| BinaryPRenewedAG.txt | 44 × 6 | Derived individual/style/outcome summary |
| Prop_BoutAso_cons.txt | 47 × 6 | Derived individual/received-outcome/persistence summary |
| Prop_BoutAso_rec.txt | 37 × 6 | Derived individual/received-outcome/persistence summary |
| Signaltypes.txt | 108 × 4 | Derived individual/type summary |
| Signaltypes.xlsx | Sum: 108 × 4 | Derived individual/type summary |
| Signaltypes_classifier.txt | 82 × 4 | Derived individual/type summary |
| Signaltypes_classifier.xlsx | SumPASAG: 81 × 4; Sheet1: 31 nonempty stored rows, extent 26 | Summary plus unknown multilevel layout; no inferred flat Sheet1 schema |
| Sum.txt | 27 × 11 | Derived individual summary, separate leading row labels |
| SumPASAG.txt | 27 × 9 | Derived individual summary, separate leading row labels |
| VictimSignalling_Publication.R | Static text, 41460 bytes | Source analysis script, inspected only |
| Victim_signalling.Rproj | Static text, 236 bytes | Project configuration; format Version is not an R runtime version |

The raw workbook has two annotations with no named `File` value: rows **2674**
and **5542** store a filename in unheaded column 45. Their locations are retained;
the audit does not shift cells or repair them. The classifier text and SumPASAG
worksheet have different row counts; they are not interchangeable copies.

## Relationships and cardinalities

The text main table has a unique complete display key
`(Study_group, Study_year, PC_ID)`: **144 rows / 144 conflicts**. All **325** main
bouts have unique complete keys with `Bout_number` appended and map to those
144 displays. This establishes one display per deposited conflict; it does not
prove that a raw recording or bout is uniquely identified by `PC_ID` alone.
There are two groups, 27 victims and 23 aggressors. Demographic `Individual`
is unique across 42 records and covers all main-table victim/aggressor codes.
Identity fields remain grouping/dependence controls, without semantic interpretation.

The derived text export joins exactly on all 144 display and 325 bout keys,
with no differing common fields. The XLSX main table instead stores
`PC_ID=50.201099999999997` where the text table has `50.2011`; the exact join
therefore leaves one display and one bout unmatched in each direction. Numeric
precision differences in other XLSX fields are also retained, without coercion.

Persistence has **329 rows / 144 conflicts / 328 distinct bout keys**. The
main-to-persistence intersection is 324 unique keys: 323 one-to-one pairs and
one one-to-two pair. Thus **325 + 4 extra rows + 1 duplicate-key row − 1 missing
main-bout key = 329**. This is an accounting identity, not a source explanation.

| Exact key `(group, year, PC_ID, bout)` | Source evidence and disposition |
|---|---|
| `(2,2012,101,4)` | Persistence row 8; MS/KS; `PC101_MS_05.07.12.mov.eaf`. Raw filename candidate has bout 4 at 302500–305300 ms, row 2954. |
| `(2,2012,101,5)` | Persistence row 9; same identities/file; raw candidate bout 5 at 316093–320858 ms, row 2955. |
| `(2,2012,101,6)` | Persistence row 10; same identities/file; raw candidate bout 6 at 357158–362095 ms, row 2956. |
| `(2,2012,101,7)` | Persistence row 11; same identities/file; no same-number raw candidate. |
| `(1,2011,66,2)` | Persistence rows 285 and 286 differ in `Post_bout_event` (Consolation/Conflict_stop), `Consolation_afterbout` (1/0), and `Bout_persistence` (1/0). No persistence-table timestamps disambiguate them. Retain both. |
| `(1,2011,66,6)` | Main row 404 has no persistence key. Raw filename candidate contains six chronologically distinct bouts, including 6 at 261745–262590 ms. No deposited correction rule links this to duplicate 2. |

The four PC101 rows remain **unresolved source discrepancies**. Raw same-number
annotations are candidates, not proof of the same bout. PC101 has 3 main bouts,
7 persistence rows, and 6 candidate raw bouts. Two further discrepancies remain:
PC119 `(2,2012)` has 9 main/persistence bouts but 11 candidate raw bouts; PC49
`(2,2012)` has 9 main/persistence bouts, 10 candidate raw bouts and
`Total_bouts=10`. Display `Total_bouts` consequently sums to **326**, not 325.
Raw bout annotations total **333** across 145 files, including two in the
explicitly human-related exclusion candidate. These counts are not independent
sample sizes and must not be collapsed silently.

Seven matched main/persistence row pairs differ in outcome/persistence fields:
`(1,2011,199,1)`, `(1,2011,238,1)`, `(1,2011,66,2)` (the second persistence row),
`(2,2011,30,1)`, `(2,2011,32,4)`, `(2,2012,119,2)`, `(2,2012,39,1)`.
Exact left/right values and locators are in
`relational_crosswalk.main_bout_to_persistence.metadata_mismatches`.
Conflict `(1,2011,258)` additionally has display
`FileSource=PC258_KG_29.07.11.mov.eaf` versus bout/persistence
`PC258__KG_29.07.11.mov.eaf`; both strings are preserved.

### Raw-to-processed links

Only **124** exact conflict keys intersect between 144 main displays and 143
unambiguous raw-file metadata profiles: 20 main keys and 19 raw keys are unmatched.
Raw files for PC29 and PC91 have inconsistent `Study_year` annotation values.
Raw PC50 has `PC_ID=2011`; processed IDs also contain suffixes absent in raw IDs.
Seven matched native keys differ in victim/aggressor codes (including ML/MLK,
MS/MA, BIS/BS and KT/KG). No alias is certified from these observations.

An explicitly **ARS-derived**, unique filename PC-token/date anchor connects
144 display filenames to raw filename candidates. It is a diagnostic, not a
source-authored or admissible foreign key. Exact `(File, begin_ms, end_ms)` joins
between raw bout-number and modality/complexity tiers match 315 of 333 keys;
direction/post-bout/persistence tiers match 314 of 333. Unmatched intervals in
both directions remain visible. Tier proximity, numbering and row order do not
justify silent alignment.

Of 9051 raw rows, 7401 have one named tier value and 1650 have none. Named
`(File, tier, begin_ms, end_ms)` annotation keys are not universally unique;
three duplicate candidates and the two missing-File annotations are retained
in the crosswalk. Empty tier values are not interpreted as negative outcomes.

### Audience 144 → 142

The two records missing all of `N_friends_within10m`, `N_dominants_within10m`,
and `Kin_within10m.01` are `(1,2012,61)` (KT/EK,
`PC61_KT_29.05.12.mov.eaf`, export row 53) and `(1,2012,156)` (AP/FZ,
`PC156_AP_13.07.12.mov.eaf`, export row 75). Formula-input completeness is 142.
The source script line 624 explicitly says audience composition could not be
found for two conflicts. It reads the full table and specifies the models;
it does not code a separate `complete.cases`/row-exclusion operation. Therefore
142 is a supported descriptive reconstruction, not an executed model subset.

## Six reported exclusions

The published 150-coded/144-analyzed constraint is retained from the prior source
review. The deposit has 145 named raw files and no complete 150-record selection
ledger or raw-to-processed generation code.

One source-keyed exclusion candidate is
`PC120_WK_11.07.11 (Converted).mov_excluded as conflict was human related.eaf`:
raw group 1, year 2011, PC_ID 120, victim WK, aggressor T (metadata/video locators
6958/6961). The human-related reason is **source-authored filename evidence**;
its anti-join against processed filename candidates is **ARS reconstruction**.
The full selection-ledger relationship and exclusion decision time relative to
receiver outcomes remain unknown. It is absent from processed candidates and
therefore appears excluded from their analyses, but no executable source filter
establishes the procedure. The remaining five identities/reasons cannot be
located; their keys are null, not invented. All six exclusions are not reproducible.

## Temporal coverage and variable eligibility

Across all 145 raw files (including the human-related candidate), all **9051**
stored raw data rows have valid numeric millisecond start/end/duration fields; redundant
seconds and hh:mm:ss.ms agree. There are zero missing/invalid timestamps,
negative/reversed intervals, duration-identity failures or zero-length intervals.
All **287 PC_event annotations** (220 Consolation, 31 Reconciliation, 36
Renewed_aggression) also pass those checks.

PC_event annotation starts fall inside an ongoing display **176** times, after
display completion **108** times, and exactly at display end **3** times. None
fall before/on display onset. There are 124 starts strictly inside at least one
bout, 163 outside bout interiors, and 5 tied to a bout boundary (boundary ties
are an additional diagnostic, not a third disjoint bin). No receiver starts are
simultaneous within a file. These are annotation counts, not distinct conflicts
or certified five-minute outcomes. They demonstrate why full-display summaries
cannot automatically serve as baseline features.

File-local time units are verified; **conflict-end origin is not**. PC_event
starts are raw event-tier proxies whose active receiver definition still needs
source confirmation. Post_bout_event support intervals must not be substituted
for actual receiver onsets. A recording filename even specifies use of a second
aggression starting at 01.54. No universal conflict-end-at-zero rule is justified.
There are 53 files without a PC_event annotation; absence is not certified as a
negative outcome. Of 145 Video_dur intervals, 55 are shorter than 300000 ms;
none certify five-minute post-conflict observability. Thirteen facial annotations
explicitly say Out_of_sight. Coverage/censoring requires source clarification.

Every named candidate field has a source/table/level/timestamp/evidence/status
entry. Static demographic fields receive `BASELINE_STATIC` as a structural class,
but remain unselected pending coding/linkage review. Victim/aggressor/group,
conflict and bout identifiers receive `IDENTITY_OR_CLUSTERING_ONLY`. Receiver
fields are `OUTCOME`; their binary/count/proportion derivatives are
`DERIVED_FROM_OUTCOME`. Persistence and its summaries are
`POST_RECEIVER_DOWNSTREAM`. Components, total signal number, whole-display
duration and other aggregates are `TIMING_DEPENDENT_REQUIRES_EVENT_ORDER`.
Piloerection, audience and other uncertified measurements remain
`UNKNOWN_TIMING_HELD`. No field is granted baseline eligibility, and no
pre-signal/signal-time class is granted merely from annotation presence.

Signal number counts/sums individual components, including overlapping modalities;
it is not an independent-bout count. The script aggregates source component counts,
but does not deposit the raw-to-total construction. Display totals can extend past
receiver events. Piloerection may have timed annotation intervals, yet their mapping
to display/bout fields and modeled receiver endpoints is unverified. These remain
programmatically gated. Repository presence, model declarations or grouping do not
establish biological meaning or semantic compositionality.

## Static code evidence and validation

The crosswalk stores exact line-numbered snippets from the hash-pinned R member:
loading at 46/48; victim/aggressor merges at 51–52; binary outcomes at 55–57;
signal-presence coding at 59–61; renaming/export at 64–77; display/bout separation
at 80–82; component/style aggregation and NA-to-zero summaries at 116–157;
preconstructed persistence loading/coding at 489–492 and model declarations at
495–498; audience table/level/coding at 595–620, two-conflict comment at 624,
count formula at 625–629 and duration formula at 743–747. Factor/reference,
missingness, dependencies, seed and runtime/model-configuration cues are preserved
as static source references. No runtime is invoked to infer omitted defaults.
No raw-to-processed/persistence construction or six-record exclusion filter is
found in the deposited script; missingness handling in derived summaries does
not establish complete observation coverage.

Offline reproduction, with the existing verified archive available:

```bash
python scripts/audit_d0029_rdc006.py --out build/d0029_rdc006_crosswalk.json
python -m pytest -q tests/test_d0029_rdc006.py tests/test_d0029_source_history.py
```

Targeted tests cover frozen snapshot/member integrity, v4-only association,
cardinalities, duplicate/unmatched keys in both directions, tier misalignment,
timestamp units/order/ties, forbidden outcome/downstream promotion, static hostile
code inspection, unchanged provenance roles and exact offline receipt regeneration.
Synthetic and frozen tests need no network or production data; regeneration checks
use the ignored cache when available. The CLI fails closed on missing or changed
source bytes. No media acquisition is required.

Validation completed: **59 targeted tests passed; 287 full-suite tests passed**
(Python 3.13, bundled Node on PATH). A second offline run is byte-identical to
the frozen crosswalk, SHA256
`06ded4663eec6fae94e4320f5bb0d9a54174fd327e8565935a6cd826a1a1daa7`.
The original source snapshot remains unchanged, and `git diff --check` passes.
Only this validation note was added after the full-suite run; executable code,
source pins and the generated crosswalk did not change.

## Admission blockers and next main-path action

Keep D0029 held. Obtain source-authoritative clarification or a corrected,
version-pinned package/codebook covering: PC101/PC66 bout mapping and the seven
receiver-label disagreements; PC119/PC49 raw counts; raw/processed ID aliases and
tier interval alignment; conflict-end origins, active receiver-event definitions
and observation/censoring coverage; the complete six-record exclusion ledger;
and endpoint-specific timing for counts, duration, audience and arousal.
The two missing audience records are identified, but they do not remove these
other blockers. This is a provenance-ready clarification scope; no authors have
been contacted. Resolve these source gates before considering bounded receiver
corpus admission, and before any empirical or confirmatory RQ0005 work.
