# D0029 Figshare source history and admission

Outcome **A**: the public Figshare version history exposes analysis data and R
code in **v1, v2 and v3**. The independently retrieved **v4 also exposes an
analysis archive**. Source location is resolved for this inspection; empirical
admission is not granted. The bounded disposition is
`D0029_ADMISSION=HELD_RDC006_SCHEMA_TIMING_DEPENDENCE_REVIEW`.

This is a source audit of Heesen et al. (2022), *Flexible signalling strategies by
victims mediate post-conflict interactions in bonobos*. No deposited R code,
inferential model, D0027 analysis or confirmatory RQ0005 analysis was executed.
BONOBO remains ACTIVE_COMPARATOR; RQ0005/H0013–H0015 and
SEMANTIC_COMPOSITIONALITY=CONTESTED_UNRESOLVED remain unchanged.

The immutable [source snapshot](../contracts/d0029_version_history_source_snapshot.json)
contains complete manifests, API endpoints and retrieval times, source timestamps,
item licences, download routes, Figshare MD5s, acquired-file and archive-member
hashes, exact table headers, descriptive missingness, static code cues, deterministic
diffs, candidate identifier checks and all twenty RDC-006 field assessments.
Source bytes remain outside Git in ignored `build/d0029_source_history/`.

## Authoritative versions

The [public version listing](https://api.figshare.com/v2/articles/16910173/versions)
returns exactly v1–v4. Each version was retrieved from its own listed endpoint;
no unversioned item response substitutes for a historical manifest.

| Version | Publication timestamp UTC | Files | Scientific archives and file IDs |
| --- | --- | --- | --- |
| [v1](https://api.figshare.com/v2/articles/16910173/versions/1) | 2022-04-08 09:38:10 | 19 | `Data_and_R_script.zip` 31662422; `Data and R code.zip` 34737973 |
| [v2](https://api.figshare.com/v2/articles/16910173/versions/2) | 2022-05-06 10:37:05 | 19 | `Data_and_R_script.zip` 31662422; `Data and R code.zip` 35025454 |
| [v3](https://api.figshare.com/v2/articles/16910173/versions/3) | 2022-05-06 11:12:36 | 19 | `Data_and_R_script.zip` 31662422; `Data and R code.zip` 35025694 |
| [v4](https://api.figshare.com/v2/articles/16910173/versions/4) | 2022-07-11 10:28:16 | 18 | `Data and R code.zip` 36230763 |

DOIs are `10.6084/m9.figshare.16910173.v1` through `.v4`. v1's title is
*Conflict resolution in bonobos: Flexible emotion signalling following aggression*;
v2–v4 use the final article title. Each exposed `created_date` equals that version's
publication timestamp. All four expose `modified_date=2022-07-11T10:28:16Z`;
that shared field does not date individual file changes or prove a later re-upload.
All four item-level licence records report CC BY 4.0 (value 1 and its licence URL).

The following **17 media files occur unchanged by ID, name, size and API MD5 in
every version**. Their bytes were not downloaded.

| File ID | Name | Bytes |
| --- | --- | ---: |
| 31662425 | Agonisticpeep_MU.wav | 333666 |
| 31662428 | Contesthoot_AP.wav | 2212034 |
| 31662431 | Peep_KT.wav | 233968 |
| 31662434 | Peepshriek_LM.wav | 375868 |
| 31662437 | Poutmoan_YL.wav | 498308 |
| 31662440 | Poutwhimper_MLK.wav | 94354 |
| 31662443 | Threatbark_SL.wav | 1367638 |
| 31662446 | Victimscream_MS.wav | 923116 |
| 31662449 | Movie s1_annotated.mp4 | 23363607 |
| 31662452 | Movie s1_raw.mov | 13392888 |
| 31662455 | Movie s2_annotated.mp4 | 27078379 |
| 31662458 | Movie s2_raw.mov | 49380722 |
| 31662461 | Movie s3_annotated.mp4 | 100792506 |
| 31662464 | Movie s3_raw.mov | 205274510 |
| 31662467 | movie s4_annotated.mp4 | 276738440 |
| 31662470 | Movie s4_raw.mov | 567917227 |
| 31662473 | Movie s5_annotated.mp4 | 56540250 |

Thus each version's full manifest is this common media set plus the archive(s)
listed above. The snapshot preserves supplied and computed MD5s and exact
download URLs for every file, including unacquired media.

## Manifest and archive transitions

* **v1 → v2:** 34737973 removed; 35025454 added under the same archive filename,
  with different size/hash. Inside it, `data_victimsignalling.txt`,
  `processed_dataset.txt` and `processed_dataset.xlsx` changed.
* **v2 → v3:** 35025454 removed; 35025694 added under the same name, with different
  size/hash. `Signaltypes.txt`, `Signaltypes_classifier.txt`, `Sum.txt` and
  `SumPASAG.txt` were added. `Signaltypes_classifier.xlsx`,
  `VictimSignalling_Publication.R` and `Victim_signalling.Rproj` changed.
* **v3 → v4:** 31662422 and 35025694 removed; 36230763 added under the modern
  archive name, with different size/hash. `demographic_info.txt` was added;
  `data_victimsignalling.txt` and `VictimSignalling_Publication.R` changed.

No same-ID renames, same-ID hash/size changes, or media additions/removals occurred.
Replacement archives remain distinct source files; historical materials are never
pooled with v4 materials into an invented version. The legacy archive contains
`VictimSignalling_Publication1.R`; modern archives contain
`VictimSignalling_Publication.R`.

## Acquired bytes and licences

Each local MD5 matched **both** authoritative Figshare MD5 fields. The SHA256s
below are locally calculated. Archive-member SHA256/MD5 hashes are also in the
snapshot; member hashes are local evidence, not claimed Figshare metadata.

| File ID (version association) | Bytes | Local/API MD5 | Local SHA256 |
| --- | ---: | --- | --- |
| 31662422 (v1/v2/v3) | 748578 | c489ae675800b34b4abaed7498a9a450 | 25d885c6f350c29ea1a9317d16baed232f67384c229c669cb66ae9e916ce7544 |
| 34737973 (v1) | 736075 | 58f10d02cf7f6dcc3bee28f212638a49 | 00f1a676bb96c774557f03f0cac7fe4a95524ab577ceddd08e10d6c9d440fd14 |
| 35025454 (v2) | 739946 | 95380b84f30a89395360101cf8796711 | e1a1328cd1834de2903cf2fe6b7ab1070ffc0b816a162f93775d175478b683ae |
| 35025694 (v3) | 744630 | 118a811837b750b0768b42910f1acb06 | e76261bc46fd38ee86561c978888e67c1ac6dbe057939d884206e6281adbf065 |
| 36230763 (v4) | 747639 | a7062549780317524cf0ffb2826f3b64 | 7bbc28be52c24b6c8ada435838b671dea7bcaaff10d709206b04a2e62e577a10 |
| 36314798 (supplement item 20131650 v2) | 2117891 | 9f4c4400b6600529acdd8325eb6c1ad6 | da491f94452fd5b0d38b499d2a197c138abd495c3d16794030b013d0737e8a74 |

The supplementary item's exposed licence is also CC BY 4.0. Separate file-level
licence fields are not surfaced by these API records, and no README/licence member
was found in the archives. The snapshot records file/member licence as null rather
than copying article or item terms into invented file-level metadata. This source
inspection makes no blanket redistribution decision for media or research rows.

The hash-verified supplementary DOCX contains a **Supplementary data** entry naming
`Data_and_R_script.zip` and the v3 DOI. Its hyperlinks also point to v3. This is a
precise source-authoritative locator for file 31662422 in v3, rather than generic
availability prose. The earlier collection-v2 enumeration is retained as supplied;
this task verified the exact member-v2 DOCX without reopening the collection gate.

## Conservative source inspection

The v4 archive supplies the complete candidate source package without borrowing
v3 bytes. Its principal deposited tables are:

| Member | Stored data rows × named columns | Role |
| --- | --- | --- |
| processed_dataset.txt | 469 × 43 | 144 Display + 325 Bout rows |
| data_victimsignalling.txt | 469 × 59 | Demographic/binary derived export; 144 Display + 325 Bout rows |
| data_victimsignalling_BoutAso.txt | 329 × 60 | Persistence/bout table |
| demographic_info.txt | 42 × 6 | Source-native individual covariates |
| BinaryPCons.txt / BinaryPRec.txt / BinaryPRenewedAG.txt | 44 × 6 each | Deposited victim-level aggregate tables |
| Prop_BoutAso_cons.txt / Prop_BoutAso_rec.txt | 47 × 6 / 37 × 6 | Deposited persistence aggregates |
| Signaltypes.txt / Signaltypes_classifier.txt | 108 × 4 / 82 × 4 | Deposited signal summaries |
| Sum.txt / SumPASAG.txt | 27 × 11 / 27 × 9 | Deposited component/style sums |

R `write.table` exports can have an unnamed leading row-name field. The inspector
records it separately; it neither shifts named columns nor promotes the row label
to conflict identity. Exact headers and per-column missing-token counts for every
distinct tabular content hash across all five archives are preserved.

`processed_dataset.xlsx` has 469 data rows and 43 named columns. The raw
`raw_data_signaltypes_below5min.xlsx` sheet has 9,051 nonempty rows after its header,
44 named headers and a 45-column stored value extent, including two nonempty cells
outside the named headers. These are stored annotation rows, not certified
independent conflicts/bouts. It contains Begin/End/Duration fields in multiple
time units, PC/event fields, group/year, victim/aggressor/consoler IDs, component
codes, `File`, and `Video_dur`. The classifier workbook has multilevel headers
requiring a source mapping; its `SumPASAG` sheet has 81 nonempty data rows while the
related text export has 82. Formatting dimensions are kept distinct from counted
nonempty rows. No spreadsheet formulas were executed.

Candidate conflict key `(Study_group, Study_year, PC_ID)` uniquely identifies the
144 display rows. The source exposes 2 groups, 27 victims and 23 aggressors.
All main/persistence bout rows match a display conflict on that candidate key.
However, the main table has 325 unique bout keys while the persistence table has
329 rows and 328 unique `(Study_group, Study_year, PC_ID, Bout_number)` keys. Four
persistence rows (physical rows 8–11, header counted) lack a matching main-table
bout key. Main-table row 236 and persistence-table row 169 disagree with display
row 237 on `FileSource`. These records are retained, not deduplicated or repaired.
They prevent an unconditional conflict/bout dependence admission.

Two display rows lack friend/dominant/kin audience-composition fields, consistent
with the published 142-conflict audience subset. The R script explicitly comments
on two conflicts with unavailable original audience information. This is source
structure evidence, not execution of the audience models. Exact row-level
exclusions from 150 coded to 144 analyzed conflicts and observation-completeness
rules still require a source crosswalk.

Static R inspection records all dependencies and source-line cues. The script
uses `brms`/`rstan`, with Bernoulli, negative-binomial and lognormal families and
explicit 4 chains, 10,000 iterations, 2,000 warmup and adapt_delta 0.99. R/package
versions are not pinned. `set.seed(8)` appears in a plotting section after earlier
model declarations; it is not a universal model seed. The `.Rproj` format Version
field is not an R runtime version. The initial path reads `processed_dataset.txt`
and `demographic_info.txt`, merges demographic information by victim/aggressor,
derives binary fields, and separates Display/Bout records. Historical v1–v3
archives lack the expected demographic file; v4 adds it. Some later expected
marginal-effects files are absent; some are generated earlier by the script, so
an absent read filename alone does not establish a missing original input. The
script's aggregate zero-fill and manual plotting summaries are recorded as source
operations, not adopted as ARS missingness or modeling rules.

## RDC-006 disposition and R0011 audit history

The current RDC-006 authority was read from ACEB's **Receiver Minimal Data
Contracts!A115:S150**; all twenty field IDs were assessed. Byte integrity and
schema discovery can advance beyond the source-location hold, but no empirical
admission is granted:

* Exact v4 archive/member/physical-row provenance can be pinned; candidate keys
  still require source definitions and the dependence discrepancies above.
* Raw timestamps exist, but a tier/event/conflict/bout timebase crosswalk has not
  established which measurements precede a receiver event. Whole-display counts,
  durations, signal components and piloerection remain timing-gated.
* Persistence and whether consolation/reconciliation was received remain downstream
  interaction variables. They are not baseline prospective predictors.
* Signal number is a component count/sum, including overlapping multimodal
  components; it is not the number of independent bouts.
* Consolation, reconciliation and renewed aggression remain distinct locked
  outcomes within the source five-minute post-conflict window. Missing outcome or
  coverage information cannot be converted to a negative response.

Canonical citation provenance remains **v4**. The historical v3 packages remain
exactly identified and separate, including the DOCX-named legacy archive. This
transition does **not** explain data disappearing from v4: the v4 endpoint inspected
here exposes its own revised archive.

R0011's prior registry row is preserved verbatim in the snapshot. Its ten-file v4
observation differs from the current complete 18-file response. Source unavailability
is contradicted by the present source evidence, but the reason for that earlier
enumeration discrepancy is unverified. Do not assert that Figshare changed after
the prior audit. R0011 remains an auditable routing/verification discrepancy with
source location now established; no registry history was deleted. R0010 was not
reused or edited. The activation document also contains a residual R0010 reference
in its Next gate prose; this task records no correction to that unrelated ID.

Drive/ACEB semantic records were read only. This repository receipt does not silently
rewrite their current D0029 hold or refresh unrelated Workbench pins. D0027/R0009,
D0028's parameter mismatch, S0092/D0030/R0008 and D0026's OSF state remain unchanged.

## Reproduction and next gate

Run the deterministic provenance replay with the local cache:

```bash
python scripts/probe_d0029_source_history.py
python -m pytest -q tests/test_d0029_source_history.py
```

Explicit `--refresh` retrieves the version listing, each listed version and the
exact supplementary item, then acquires only small non-media files. Missing
versions, unexpected routes, invalid schemas or byte/hash drift fail closed with
Outcome C and a diagnostic receipt. Default replay uses no network. Receipts are
written to ignored `build/`; freezing a new durable snapshot is a separate reviewed
action. Never publish/upload the source cache, including as a CI `build/` artifact.

The inspected canonical repository was a clean local clone of
`acipriano1997/animal-rosetta-stone`, with its base HEAD verified against remote
main at `b12743b7fbd2896719433cbf7bfde9ae145b9d0c`. No remote execution connection was
available in this session, so remote execution, remote tests and canonical
Drive/ACEB reconciliation are not claimed.

Next ARS main-path action: review this complete provenance package and reconcile
R0011/D0029's source-location wording in the semantic authority, then create the
bounded RDC-006 raw-timebase/coverage/dependence crosswalk using **v4 only**. Source
clarification, if still needed, should ask about the 325/329 bout relation,
duplicate bout key, `FileSource` mismatch, six exclusion records and timing/coverage
definitions. The former missing-file question no longer warrants author outreach.
No author was contacted and no empirical reanalysis should start at this gate.
