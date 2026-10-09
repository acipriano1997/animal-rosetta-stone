# Animal Rosetta Stone

Animal Rosetta Stone (ARS) is an open, evidence-grounded research project for studying animal communication without assuming that signals map cleanly to human-language translations.

This repository is the **canonical executable authority** for ARS code, tests, CI, executable fixtures, runtime manifests, and exact-head verification evidence. Google Drive remains the human-readable semantic authority for scientific method, research questions, preregistrations, evidence governance, claim ceilings, schedules, and accepted project documentation.

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

The producer stores no Google credential, accepts no bearer token as a command-line argument, fails closed when any pinned Google Doc revision or ACEB/event-corpus modified-time pin drifts, and validates its output through the Slice 2A adapter contract before export. CI exercises the producer with synthetic Workspace responses and drift failures; public CI does **not** contain a private Google token and therefore does not claim live-Drive operational verification.

To export from the live authorities, inject an approved read-only OAuth token through the environment and run:

```bash
python scripts/export_workbench_canonical_bundle.py --out /secure/local/path/workbench-canonical.json
export ARS_WORKBENCH_CANONICAL_SOURCE=/secure/local/path/workbench-canonical.json
ars-workbench --host 127.0.0.1 --port 8765
```

The token should be supplied by an approved local secret manager or OAuth flow, not typed into the command line, committed, written to Drive documentation, or placed in CI artifacts. Full Slice 2 remains open until the authenticated producer is exercised against the live pinned authorities and that exact-head result is recorded.

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

The Slice 5 fixture checks freeze the current chimp pilot’s bounded state: D0019 is `D0019_PR0005_EMPIRICAL_CLOSED_MIXED`; RUN-005/RUN-006 are `CLOSED` with full-path disposition `MIXED`. Group-2 development used 104 eligible rows / 69 unordered dyads and favored B2 over B1 (log-loss difference −0.08026925235617471). The locked Group-1 transfer used 68 eligible rows without model or preprocessing refit and reversed direction (B1 0.6361435247748188; B2 0.6847920995625079; difference +0.048648574787689025). CRG-C is `PASS`; CRG-D is `PARTIAL` and controlling; overall remains `NOT_COMPARISON_READY`; Bonobo remains `DEFERRED`. D0025/PR0006 remains `HELD_SCHEMA`, a parallel independent-source route relevant to CRG-D.

The producer and Slice 2B verifier retain the historical `EMPIRICAL_EXECUTION_HELD` / null-disposition regression alongside CLOSED/MIXED. Unknown or conflicting closure facts fail closed. Closure earns no replicated H0001 support, semantic meaning, translation, causal claim or species-wide compositionality. ZERO_SYNTHETIC remains non-biological; D0020 goal anonymization/unreleased gesture form and bounded null interpretation remain intact; empty contradiction/disagreement registries remain registry state only; media placeholders remain no-bytes/no-preview. The static snapshot and test response fixture are presentation/software inputs, not new scientific authorities.

Slice 5 completion does not satisfy the separate Slice 2 live-auth gate. Full canonical operational verification still requires one authenticated producer execution against the pinned live Drive/ACEB authorities.

The initial 2026-10-09 reconciliation verified the supplied ACEB, species, RUN-001/003/004, execution-contract and harness pins through read-only Drive access; D0018/D0020 event pins were unchanged. RUN-002 returned revision `ANLCKQlAepEEbhUCZJypcvlGWmZsA3mbHbGhyfoOXE3bgtB3gSTAJACNjXVOkJ52JXT7U3PjWAzOanX6I82uBwsNhnRkbTXNZ9nWWE5D5OQ` on two reads, conflicting with the previously supplied pin. A subsequent independent read confirmed this revision and the unchanged September 29 file modified time, so the RUN-002 pin is now reconciled. The stale token remains a rejection regression; `FAIL_CLOSED_ON_PIN_DRIFT` is unchanged.

The subsequent full-manifest audit found a separate harness-verification pin conflict: document `1u9YOZCFWLSm4znq3sg0a1Qo2Nnuo-o0FcLh6ikQ42Rw` returned revision `AHj4eMSSV1cBzJ1kUJBmCl7XR64M16PDwNfqOdClZ-EqOIVmI_Agqr3TEdgk29iBiGWfFgYGw1_5D59uK5b02gwrcxF0VyhqDy2yzsi11Ik` in both metadata-only and full-document reads, differing from the supplied `ANLCKQkT990…` pin. That pin remains unchanged pending authority reconciliation. Live export and merge remain held on this conflict. Runtime Google OAuth credentials were unavailable, so `LIVE_AUTH_VERIFICATION=NOT_AVAILABLE`; no full authenticated producer execution or live bundle is claimed.

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

Passing this software suite means only that the executable harness, Workbench adapters, projections, firewalls and browser surfaces behave as frozen on their registered software inputs. It does **not** establish animal-signal meaning, compositionality, syntax, cross-species generalization, welfare safety, or CRG-C biological credit. Real empirical execution remains rights-, provenance-, preregistration-, and claim-ceiling gated.

## License

No software license has been selected yet. Third-party rights and the intended open-source licensing boundary will be reviewed before a repository license is adopted.
