# Animal Rosetta Stone

Animal Rosetta Stone (ARS) is an open, evidence-grounded research project for studying animal communication without assuming that signals map cleanly to human-language translations.

This repository is the **canonical executable authority** for ARS code, tests, CI, executable fixtures, runtime manifests, and exact-head verification evidence. Google Drive remains the human-readable semantic authority for scientific method, research questions, preregistrations, evidence governance, claim ceilings, schedules, and accepted project documentation.

## Research scope and current scientific main path

ARS is a **scientific research program**, not a promise of a universal animal translator and not primarily a software product. Its goal is to describe, compare, test and, where receiver-facing or causal evidence permits, cautiously decipher situated animal communication. It accepts null, mixed, contrary and non-generalizing results as legitimate scientific outcomes. Translation-like glosses are conditional downstream summaries, not an initial target or semantic authority.

The canonical [Scope, Feasibility & Research Program Doctrine](https://docs.google.com/document/d/18_YGxDm6yhkPfuMjpAg0mAhJ62Y-JHTyWpLQ3yOMA98/edit) owns scientific scope and sequencing; this README describes executable implementation rather than redefining that research doctrine. The program stages are Foundation → Evidence Bank → Comparative Engine → Hypothesis Engine → Experiments → potentially Translation, with evidence-gated parallel work:

- **First-species pilot:** chimpanzee RQ0001 is frozen `COMPARISON_READY_BOUNDED`, not a species-wide semantic-decoding success.
- **Co-equal near-term scientific paths:** Bonobo RQ0005 close-comparator source admission and a *fixed ten-case* D0034–D0043 Cross-Modal Generalization Calibration. The latter tests GDM representability and scientific guardrails across contrasting modalities, not universal decoding or an authority to activate more species.
- **Current source ceiling (2026-10-19):** ACEB Q0031 retains only bounded real-provider GDM mapping PASS for D0036 chemical and D0042 visual. D0037 electrical and D0043 substrate Exp1 were parsed from founder-uploaded source-looking rows and preserved in private raw-byte archives with readback hashes; **independent Dryad provider-file identity and canonical GDM admission remain held**. Cross-modal generalization is `NOT_MET`.
- **Independent support lanes:** NBDC exposure-clean prospective benchmark, Pippo single-subject naturalistic longitudinal corpus, Bonobo research correspondence, welfare, literature/media observation-bias review, reproducibility and rights-bounded open-science publication. None automatically promotes species-general or semantic claims.

Cross-modal calibration must record a bounded `PASS`, `MIXED`, `HELD` or `FAIL` with limits; an unqualified success is **not** a mandatory prerequisite for useful science or selecting the next discriminating species question. Any full species activation still needs evidence, rights, welfare, operational feasibility and a defensible calibration disposition. No source-data download, CI pass or attractive demonstration by itself establishes biological generality.

## Current executable scope

The first executable slice is the chimpanzee receiver-corpus harness and hardened `PR0006` receiver-modality reanalysis path. It includes:

- fail-closed rights, provenance, schema, missingness, split, grouping, leakage, nuisance, and sanity gates;
- `RHF-001..035` synthetic/adversarial fixture execution;
- `HA-001..016` structural artifact-bundle generation for synthetic verification;
- five-fold dyad-grouped PR0006 validation with training-fold-only preprocessing;
- paired out-of-fold delta log loss, grouped bootstrap uncertainty, leave-signaller-out robustness, and deterministic modality-permutation sanity testing;
- explicit `ZERO_SYNTHETIC` separation: synthetic fixtures and verification outputs carry **no biological evidentiary weight**.

## Rosetta Research Workbench — Phase I

### Slice 1 — executable fixture surface

A deliberately barebones, read-only browser shell is implemented from a frozen chimpanzee RQ0001 view-model snapshot:

```bash
ars-workbench --host 127.0.0.1 --port 8765
```

The Slice 1 fallback displays species activation/gates, RQ0001 and competing hypotheses, D0018/D0020 corpus metadata, D0019/D0025 rights-gated metadata, RUN-001..006 state, segregated ZERO_SYNTHETIC software evidence, and navigable provenance pointers.

### Slice 2A — canonical-read adapter boundary

The Workbench can consume a validated `WORKBENCH-CANONICAL-READ-v0.1` JSON bundle instead of the packaged fixture. Set:

```bash
export ARS_WORKBENCH_CANONICAL_SOURCE=/path/to/canonical-read-bundle.json
ars-workbench --host 127.0.0.1 --port 8765
```

The source may be a local path, a `file://` URI, or an HTTP(S) endpoint. File-backed bundles are current as-of exports and are **not** labeled live. HTTP(S) sources are labeled live canonical-read transports. `/api/authority-status` exposes the source mode, transport, authority state, and semantic-owner bindings.

The adapter fails closed if the authority state is stale/conflicted, required domain bindings are missing, provenance references do not resolve, a dataset attempts to acquire semantic authority, or ZERO_SYNTHETIC software verification is presented as biological evidence.

### Slice 2B — canonical Workspace producer

Slice 2B adds a read-only canonical producer that can read the pinned Drive/ACEB authorities directly through Google Workspace REST when a short-lived OAuth bearer token is injected at runtime.

The producer stores no Google credential and accepts no bearer token as a command-line argument. It checks document identity, native Google Doc type, title, Drive head revision ID and file modification time before and after extraction, fails closed on durable pin drift, and validates its output through the Slice 2A adapter contract before export. ACEB and event-corpus modification-time pins are explicit authority pins and must be reconciled whenever those semantic sources legitimately change. CI exercises the producer with synthetic Workspace responses and drift failures; public CI does **not** contain a private Google token and therefore does not claim live-Drive operational verification.

To export from the live authorities, inject an approved read-only OAuth token through the environment and run:

```bash
python scripts/export_workbench_canonical_bundle.py --out /secure/local/path/workbench-canonical.json
export ARS_WORKBENCH_CANONICAL_SOURCE=/secure/local/path/workbench-canonical.json
ars-workbench --host 127.0.0.1 --port 8765
```

The token should be supplied by an approved local secret manager or OAuth flow, not typed into the command line, committed, written to Drive documentation, or placed in CI artifacts. The separate live-authenticated Phase I producer gate **CLOSED PASS on 2026-10-15**: clean repository SHA `d68c796b737f2a3caf085ec96777bae7a5cf73eb`, authority state `CURRENT`, deterministic rerun PASS, full D0018/D0020 canonical event coverage, adapter/provenance PASS and no embedded credentials. Subsequent legitimate ACEB updates require exact durable-pin refresh, not recertification of the completed historical gate.

For the final operational gate, use `--verify-live` on a clean committed checkout
and unused output paths. It executes the same REST producer twice, checks every
source again before returning, rejects credential-bearing output, compares all
authority/scientific content excluding only capture metadata, and writes private
bundles plus an exact-commit/hash receipt. The procedure works in approved local
or remote Python runtimes; see [the live-auth runbook](docs/workbench_live_auth_runbook.md).

### Slice 3 — event and provenance exploration

The Workbench event service exposes D0018 and D0020 through bounded `events.list` / `events.get` behavior with event-specific provenance resolution. The browser requests event rows separately from the landing snapshot, so the core page stays lightweight even when a canonical bundle carries all 4,259 currently registered event rows.

The packaged fallback contains only four real source-preserved sample rows and is explicitly labeled `STATIC_SAMPLE_ONLY`. The authenticated canonical producer owns full coverage: 36 D0018 events and 4,223 D0020 interaction events. Missingness, locked/development split state, source row/blob locators, D0020 goal anonymization, and the absence of released D0020 gesture forms remain visible. Event rows cannot contain generated meaning/translation/gloss fields.

### Slice 4 — evidence, contradiction and rights navigation

Slice 4 adds bounded claim/evidence navigation for the current RQ0001 presentation set, explicit contradiction/correction and disagreement-registry state, and rights-aware media placeholders.

Claim text, status, confidence, scope, do-not-overclaim ceilings, alternative explanations, and registered Claim-Evidence Links are read from ACEB without browser-local re-grading or ranking. If the canonical contradiction/correction or disagreement registries contain zero matching rows, the Workbench states only that no matching row is currently registered; it must not convert registry absence into evidence that contrary evidence or scientific disagreement does not exist.

D0018/D0020 raw-media surfaces are placeholders only. They expose rights/missingness metadata and scientific consequences while keeping `bytes_available=false` and `preview_allowed=false`. The Workbench does not fabricate thumbnails, reconstructed media, substitute imagery, or previews for unavailable source media.

### Slice 5 — provenance, stale-state and semantic firewall

Slice 5 is the final Phase I software-verification lane. It hardens the canonical adapter and runs adversarial checks across the complete Workbench surface rather than adding a new scientific feature.

Every displayed scientific record must carry nonempty resolvable provenance. Core, event and evidence provenance namespaces may not collide. Forbidden semantic fields (`meaning`, `translation`, `semantic_gloss`, `english_gloss`) are rejected recursively, including when nested inside event context, interaction structure, or Claim-Evidence Link records. Unknown/stale/conflicted authority, unknown adapter contracts and missing semantic owners fail closed.

The Slice 5 fallback fixture now mirrors the frozen chimp pilot’s bounded comparison state as of 2026-10-12: D0019 remains `D0019_PR0005_EMPIRICAL_CLOSED_MIXED`; RUN-005/RUN-006 remain `CLOSED` with full-path disposition `MIXED`. Group-2 development used 104 eligible rows / 69 unordered dyads and favored B2 over B1 (log-loss difference −0.08026925235617471). The locked Group-1 transfer used 68 eligible rows without model or preprocessing refit and reversed direction (B1 0.6361435247748188; B2 0.6847920995625079; difference +0.048648574787689025). CRG-A through CRG-I are `PASS`; overall is `COMPARISON_READY_BOUNDED`; `CHIMP-COMP-v1.0-2026-10-12` is frozen; Bonobo is `ACTIVE_COMPARATOR`. D0020 is recorded as approved for bounded use of the public GestureConversations data with citation required, while raw-row and row-level derivative redistribution remain unasserted. D0025/PR0006 remains `HELD_SCHEMA` as an optional replication/expansion lane and is not required by the frozen chimp package.

The producer and Slice 2B verifier retain the historical `EMPIRICAL_EXECUTION_HELD` / null-disposition regression alongside CLOSED/MIXED. Unknown or conflicting closure facts fail closed. Closure earns no replicated H0001 support, semantic meaning, translation, causal claim or species-wide compositionality. ZERO_SYNTHETIC remains non-biological; D0020 goal anonymization/unreleased gesture form and bounded null interpretation remain intact; empty contradiction/disagreement registries remain registry state only; media placeholders remain no-bytes/no-preview. The static snapshot and test response fixture are presentation/software inputs, not new scientific authorities.

Slice 5 software verification alone did not satisfy the separate Slice 2 live-auth gate at that earlier checkpoint. The required real authenticated producer execution was subsequently performed and recorded as `PHASE1_COMPLETE_LIVE_AUTHENTICATED_PRODUCER_PASS_2026-10-15`. This did not create biological evidence or confer semantic authority.

The initial 2026-10-09 reconciliation repeatedly encountered changing opaque Docs API revision tokens for RUN-002, harness verification, Species Activation Record and RUN-001 even while Drive file modification times were unchanged. This exposed a persistent-pin contract error: [Google documents](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents#Document) that Docs revision tokens are opaque, user-specific, guaranteed valid for only 24 hours and may change for internal reasons.

`WORKBENCH-CANONICAL-SOURCES-v0.2` now pins all seven current documents by `document_id`, `title`, `drive_revision_id` and `observed_modified_time`. Drive revision IDs come from the newest unambiguous revision across all revision-history pages; they are not Docs API tokens. Legacy manifests/fields are rejected explicitly. The producer rechecks durable Drive state after extracting content to reject edits during the bounded read, while a different ephemeral Docs token with unchanged Drive state passes. Current snapshot provenance and response fixtures use the same durable fields. `FAIL_CLOSED_ON_PIN_DRIFT` remains active.

All seven durable document pins remain independently verified through canonical
personal Drive. The ACEB modification-time pin was reconciled to the 2026-10-14
project-control and D0026 metadata-admission updates; the frozen chimp scientific
projection and D0018/D0020 event-corpus pins remain unchanged. Full connector
responses project all 36 D0018 and 4,223 D0020 events, five bounded claims and the
CLOSED/MIXED comparison state deterministically through the existing producer.
`contracts/workbench_connector_response_compatibility_receipt.json` explicitly
records this as an offline response-compatibility replay. Runtime bearer authorization was unavailable **at this historical offline-compatibility checkpoint**. The separate 2026-10-15 locally authenticated producer receipt later closed the live gate, without changing scientific evidence or the `ZERO_SYNTHETIC` firewall.

### Presentation language

The Workbench defaults to English and offers `en-XA`, a generated test-only pseudo-locale, through an accessible presentation-language selector. Only interface chrome changes; canonical scientific prose, identifiers, states, metrics and every API response remain unchanged. The preference is local to the browser. Unsupported locales fall back to English.

See [presentation ownership and localization procedure](docs/workbench_localization.md) for protected fields, future locale approval, accessibility checks and pseudo-localization verification. Scientific translations require explicit future governance.


### Core research workspaces — decipherment and experiment/analysis

The Workbench now exposes the two additional research surfaces defined by the canonical product architecture without adding a new scientific authority.

The **Decipherment Workspace** builds on the existing event service with dataset selection, exact canonical population/group and split filters, bounded pagination, presentation-only deep-link state, and side-by-side alignment of two to four source-preserved events. Alignment does not calculate semantic similarity, infer missing values, generate meanings or translations, or establish communicative equivalence.

The **Experiment & Analysis Workspace** expands canonical run inspection. Empirical and planned runs remain separate from `ZERO_SYNTHETIC` software verification; the inspector shows recorded run state, evidence class, disposition, metrics, interpretation ceiling or gate, associated dataset state, rights and provenance. Protocol/split/control/environment/reproducibility fields that are not present in the canonical run record are displayed as missing rather than invented.

Cross-navigation is identifier-based only: dataset → events/runs, event → dataset/provenance, and run → dataset/provenance. These surfaces have **scientific effect: NONE** and create no biological evidence.

## Canonical bindings

`contracts/canonical_bindings.json` pins Drive/ACEB bindings used by executable research paths. `contracts/workbench_canonical_read_contract.json` defines the Workbench adapter envelope and fail-closed transport semantics. `src/ars_workbench/data/workbench_canonical_sources.json` pins the current Workbench producer, event, evidence and rights authorities. `contracts/workbench_canonical_producer_contract.json`, `contracts/workbench_event_explorer_contract.json`, `contracts/workbench_evidence_navigation_contract.json`, and `contracts/workbench_slice5_firewall_contract.json` own the producer and Slice 3–5 executable boundaries. If Drive semantic authority changes, code is stale until reconciled; code never silently redefines the scientific rules.

## Verification

Use Python 3.13 and Node.js 22+ on `PATH`. Presentation JavaScript tests use Node's built-in modules, with no npm packages, browser, translation service or sockets.

```bash
python -m pip install -r requirements-lock.txt
python -m pip install -e .
python -m pytest -q
python scripts/generate_workbench_pseudolocale.py --check
python scripts/run_rhf_suite.py --out build/rhf_suite_receipt.json
python scripts/run_synthetic_verification.py --out-dir build/synthetic_verification
python scripts/verify_workbench_slice1.py
python scripts/verify_workbench_slice2_adapter.py
python scripts/verify_workbench_slice2_producer.py
python scripts/verify_workbench_slice3_events.py
python scripts/verify_workbench_slice4_evidence.py
python scripts/verify_workbench_slice5_firewall.py
```

GitHub Actions runs the same verification on pull requests and `main` and uploads exact-head receipts.

## Scientific boundary

Passing this software suite means only that the executable harness, Workbench adapters, projections, firewalls and browser surfaces behave as frozen on their registered software inputs. It does **not** establish animal-signal meaning, compositionality, syntax, cross-species generalization, welfare safety, or biological truth beyond the bounded evidence recorded by the scientific authorities. Future empirical execution remains rights-, provenance-, preregistration-, and claim-ceiling gated.

## License

No software license has been selected yet. Third-party rights and the intended open-source licensing boundary will be reviewed before a repository license is adopted.
