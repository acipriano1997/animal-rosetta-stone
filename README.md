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

The Workbench can now consume a validated `WORKBENCH-CANONICAL-READ-v0.1` JSON bundle instead of the packaged fixture. Set:

```bash
export ARS_WORKBENCH_CANONICAL_SOURCE=/path/to/canonical-read-bundle.json
ars-workbench --host 127.0.0.1 --port 8765
```

The source may be a local path, a `file://` URI, or an HTTP(S) endpoint. File-backed bundles are current as-of exports and are **not** labeled live. HTTP(S) sources are labeled live canonical-read transports. `/api/authority-status` exposes the source mode, transport, authority state, and semantic-owner bindings.

The adapter fails closed if the authority state is stale/conflicted, required domain bindings are missing, provenance references do not resolve, a dataset attempts to acquire semantic authority, or ZERO_SYNTHETIC software verification is presented as biological evidence.

Slice 2A establishes the transport and validation boundary. Slice 2B adds a read-only canonical producer that can read the pinned Drive/ACEB authorities directly through Google Workspace REST when a short-lived OAuth bearer token is injected at runtime.

The producer stores no Google credential, accepts no bearer token as a command-line argument, fails closed when any pinned Google Doc revision or the pinned ACEB modified time drifts, and validates its output through the Slice 2A adapter contract before export. CI exercises the entire producer with synthetic Workspace responses and drift failures; public CI does **not** contain a private Google token and therefore does not claim live-Drive operational verification.

To export from the live authorities, inject an approved read-only OAuth token through the environment and run:

```bash
python scripts/export_workbench_canonical_bundle.py --out /secure/local/path/workbench-canonical.json
export ARS_WORKBENCH_CANONICAL_SOURCE=/secure/local/path/workbench-canonical.json
ars-workbench --host 127.0.0.1 --port 8765
```

The token should be supplied by an approved local secret manager or OAuth flow, not typed into the command line, committed, written to Drive documentation, or placed in CI artifacts. Full Slice 2 remains open until the authenticated producer is exercised against the live pinned authorities and that exact-head result is recorded.

### Slice 3 — event and provenance exploration

The Workbench event service now exposes D0018 and D0020 through bounded `events.list` / `events.get` behavior with event-specific provenance resolution. The browser requests event rows separately from the landing snapshot, so the core page stays lightweight even when a canonical bundle carries all 4,259 currently registered event rows.

The packaged fallback contains only four real source-preserved sample rows and is explicitly labeled `STATIC_SAMPLE_ONLY`. The authenticated canonical producer owns full coverage: 36 D0018 events and 4,223 D0020 interaction events. Missingness, locked/development split state, source row/blob locators, D0020 goal anonymization, and the absence of released D0020 gesture forms remain visible. Event rows cannot contain generated meaning/translation/gloss fields.


## Canonical bindings

`contracts/canonical_bindings.json` pins Drive/ACEB bindings used by executable research paths. `contracts/workbench_canonical_read_contract.json` defines the Workbench adapter envelope and its fail-closed transport semantics. `src/ars_workbench/data/workbench_canonical_sources.json` pins the current Workbench producer and event authorities; `contracts/workbench_canonical_producer_contract.json` defines the credential, drift, projection, and scientific-firewall rules for direct reads; `contracts/workbench_event_explorer_contract.json` owns the Slice 3 event/provenance presentation boundary. If Drive semantic authority changes, code is stale until reconciled; code never silently redefines the scientific rules.

## Verification

```bash
python -m pip install -r requirements-lock.txt
python -m pip install -e .
python -m pytest -q
python scripts/run_rhf_suite.py --out build/rhf_suite_receipt.json
python scripts/run_synthetic_verification.py --out-dir build/synthetic_verification
python scripts/verify_workbench_slice1.py
python scripts/verify_workbench_slice2_adapter.py
python scripts/verify_workbench_slice2_producer.py
python scripts/verify_workbench_slice3_events.py
```

GitHub Actions runs the same verification on pull requests and `main` and uploads exact-head receipts.

## Scientific boundary

Passing this software suite means only that the executable harness, Workbench adapter, and canonical producer behave as frozen on their registered software inputs. It does **not** establish animal-signal meaning, compositionality, syntax, cross-species generalization, welfare safety, or CRG-C biological credit. Real empirical execution remains rights-, provenance-, preregistration-, and claim-ceiling gated.

## License

No software license has been selected yet. Third-party rights and the intended open-source licensing boundary will be reviewed before a repository license is adopted.
