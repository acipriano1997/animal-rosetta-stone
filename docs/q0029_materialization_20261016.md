# D0026 / Q0029 source-byte execution — 2026-10-16

Starting live main: `f6cbe7d4c2bfc836f7e05b3077666d3da70592ae`; no open PRs at start. Exact-main receiver-harness-ci run [38929027372](https://github.com/acipriano1997/animal-rosetta-stone/actions/runs/38929027372) was SUCCESS.

Personal Drive only was used. ACEB modified time and Workbench pin both read `2026-10-16T15:19:36.045Z` before edits. Current scope/audit authorities and General Data Model prose/workbook confirmed v1.13/v1.14. Bonobo stays ACTIVE_COMPARATOR; calibration taxa stay unactivated; the frozen ten-case tranche stays staged outside ACEB.

## Actual acquisition and existing-verifier results

Q0029's existing `scripts/audit_q0029_materialization.py` passed for all 17 provider objects: four Mendeley D0031 objects, twelve exact D0032 Springer ZIPs, and one Figshare D0033 workbook. All four D0031 provider SHA-256 values matched; D0033's provider MD5 matched. D0032 has local SHA-256 inventory, without a claimed independent provider checksum comparison. ZIP safety validation covered top-level central directories only; nested ZIP safety and payload validity remain unassessed. No archive member was extracted, and no source code was executed. The materialization receipt keeps `admission_ready=false`, `scientific_effect=NONE`, and no replication-credit change.

D0026 acquired 0/5 objects. OSF's file-metadata API and pinned WaterButler download route both returned HTTP 503 with the provider's scheduled-maintenance notice. The existing D0026 verifier was run and returned HELD_SOURCE_BYTE_INTEGRITY with all five expected files missing. This is a provider transport hold, not a hash mismatch or biological uncertainty. No license, UNCONFIRMED final-analysis equivalence, schema/runtime hold, ACOUSTIC_PRODUCTION_TAXONOMY_ONLY, biological_evidence=false and scientific_effect=NONE remain unchanged. No author draft was sent.

## Rights and runtime limits

Mendeley's exact dataset API independently reports CC BY 4.0, with an explicit third-party-content caveat. Data/code were inspected under this dataset disposition. Separate embedded/example-media rights review is incomplete; no video redistribution permission is asserted. The R script imports dplyr, Rmisc, brms, bayestestR, emmeans, marginaleffects, ggplot2 and tidybayes and reads repair_df.csv. No version lock/session information is in the four-file deposit; empirical runtime remains unexecuted.

Figshare item 28302725, version 1, explicitly reports dataset-level CC BY 4.0. This resolves the prior item-licence hold from the provider record, independently of the paper licence. Its single file is TT_social.xlsx; no code/environment is deposited in this item. The workbook has no custom document properties or description supplying an additional licence instrument. This does not establish complete runtime reproducibility.

D0032 supplementary file-level terms remain unresolved. Its article CC BY-NC-ND 4.0 licence is not projected onto archives. No archive payload, internal table, DOCX licence text or nested ZIP was extracted/read. Zenodo APIs for calibration deposits 10892587 and 15425872 returned HTTP 403; both dataset-licence holds remain unresolved. No calibration raw package was downloaded.

## Structural findings and dependence

D0031 repair_df.csv has 377 repair/negotiation records, 16 columns, 144 interaction IDs and 96 unordered identity pairs. D0033 TT_social has 6,334 signal/action rows, 17 columns, 311 interaction IDs, 157 source dyad IDs and 156 unordered identity pairs. One unordered pair has two distinct source dyad IDs. Preserve source dyad IDs and canonical pair keys separately; do not silently merge, relabel or infer an error.

All 377 D0031 rows match a D0033 interaction ID, source dyad ID and canonical unordered animal pair; all 144 D0031 interaction/pair keys occur in D0033, with no conflicting pair on a shared interaction ID. This strengthens corpus linkage but does not make different analytical row units identical. Neither deposit supplies recording/interaction dates. Disposition remains HELD_INSUFFICIENT_KEYS for full duplication/overlap adjudication; exact row equality remains unresolved; evidence weighting remains NON_INDEPENDENT and independent_replication_credit=false. Missing/NA annotation is not treated as a negative biological outcome.

The byte inventory exposes incorrect prebyte D0032 provider-label mappings. MOESM12 contains ESM12, MOESM13 ESM13, MOESM14 ESM14, and MOESM15 ESM15. MOESM16 is the bundled OR16 package, containing seven nested ZIP names. MOESM14 and MOESM19 are byte-identical, as are MOESM15 and MOESM20. The existing contract's display labels/content descriptions were corrected from actual central-directory evidence; all twelve provider URLs/identities remain unchanged. No duplicate object earns extra evidence weight. The filename word CORRECTION in a function matrix is merely a source filename, not a scientific correction notice.

## Validation and continuation

Both original verifiers were executed against the actual local directories. All nine existing D0026/Q0029 test functions passed using workspace-scoped temporary fixture directories. The first attempt could not use the sandbox's default temp directory; rerunning in the workspace resolved that environment issue. Full repository CI is tracked on the resulting PR and exact merged main; local fixture checks do not substitute for it. No new verifier, inference engine or scientific authority was created.

Canonical ACEB source/control rows are to reflect this bounded byte/schema/rights state, followed by a separate one-field Workbench pin-refresh PR, exact-head CI, immediate ACEB freshness recheck, exact-head merge and exact-main CI. Final timestamps/SHAs/CI dispositions belong to the resulting PR and canonical audit continuation; this report is the source-execution snapshot, not a later CI assertion.

Next highest-value action: reconcile the source dyad-ID alias and obtain the missing date/source-codebook linkage for D0031/D0033, preserving the current non-independent weighting. D0026 can resume from the existing frozen five-file verifier when OSF maintenance clears; no founder-only login/CAPTCHA/licence action was encountered.

No CRG-C/CRG-D, receiver-comprehension, causal, semantic, translation or species-generalization promotion occurred. D0031/D0033 remain interaction/turn-taking sources; D0032 remains observational/associative. No NBDC/blind evaluation or outreach was run.

## Exact object inventory

| Dataset | Provider filename | Bytes | Local SHA-256 |
| --- | --- | ---: | --- |
| D0031 | repair_df.csv | 27153 | `a9ad25ca506eff8aefa1a1f87ec5abe93832470829afbe30e5c171cd43808e34` |
| D0031 | repair.R | 12883 | `9dadfbdf6652d738880959c3702cbb65fef11992101a097eecba8e2932f106ef` |
| D0031 | Video S1.mp4 | 133892543 | `7d31e0be7d8910452431045c581d21f5dc15eb3ecab990e1b00f7cc649c56434` |
| D0031 | Video S2.mp4 | 81180248 | `815d0f9226da6b031753aa0d9bfdd8ab147dfde493dc9b44acba54b213a0ce9a` |
| D0032 | 265_2026_3796_MOESM11_ESM.zip | 98383 | `3ca9a8ddae8dff8a4493b0c9e6aceb12c852f462ecf44f4f9f213ea0516aa0ac` |
| D0032 | 265_2026_3796_MOESM12_ESM.zip | 402382 | `9f3c439312a890845fb4154681fc2d7fbf20bcf5469d88b4174cd92a3dd71665` |
| D0032 | 265_2026_3796_MOESM13_ESM.zip | 74716 | `3f85ceccc330fc70acda52a0125fe8a76e29776a4ca3b3207a8318db247ce263` |
| D0032 | 265_2026_3796_MOESM14_ESM.zip | 69016 | `2b3453684368341ea12603b497e00ac650eef453ba5cad992fe03f9f3fde530a` |
| D0032 | 265_2026_3796_MOESM15_ESM.zip | 48581 | `2abd9221a1ca31ec8ac4bb720fb896815726446d1d8a67a64419da81774b2f5c` |
| D0032 | 265_2026_3796_MOESM16_ESM.zip | 96948 | `fc0524a942899f0db576fa50dbb159cb01a986c785fa807ed091e1692e08f806` |
| D0032 | 265_2026_3796_MOESM17_ESM.zip | 25704 | `7f0a71c5e5e7fdb2e14885255b4e5928f7fb79a369498990fbeae55a754a600c` |
| D0032 | 265_2026_3796_MOESM18_ESM.zip | 11450 | `f0a5552e520152b0fffe73de36731bb430545f7fbda59451f7bb3c5ab29187f7` |
| D0032 | 265_2026_3796_MOESM19_ESM.zip | 69016 | `2b3453684368341ea12603b497e00ac650eef453ba5cad992fe03f9f3fde530a` |
| D0032 | 265_2026_3796_MOESM20_ESM.zip | 48581 | `2abd9221a1ca31ec8ac4bb720fb896815726446d1d8a67a64419da81774b2f5c` |
| D0032 | 265_2026_3796_MOESM21_ESM.zip | 25753 | `96795d0e8bb16b9cd096a01f8e16e4de105cccc688916d846793ed22a0f9a334` |
| D0032 | 265_2026_3796_MOESM22_ESM.zip | 13057 | `62fd677e3b0e07f98d47981368e34d8e9ca4e54eab27ed67d57239dd71707207` |
| D0033 | TT_social.xlsx | 444526 | `1cbafc00066c2e860b453715ae5f202fc2fb299404947efe5de17c9e5bc80bca` |

Machine-readable materialization and aggregate schema/crosswalk evidence are in [materialization receipt](evidence/q0029_materialization_20261016.json) and [schema/crosswalk summary](evidence/q0029_schema_crosswalk_20261016.json). Source bytes and rows are excluded from Git.
