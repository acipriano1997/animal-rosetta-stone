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

## Canonical bindings

`contracts/canonical_bindings.json` pins the Drive document revision IDs and ACEB registry ranges this executable slice consumes. If the Drive semantic authority changes, code is stale until reconciled; code never silently redefines the scientific rules.

## Verification

```bash
python -m pip install -r requirements-lock.txt
python -m pip install -e .
python -m pytest -q
python scripts/run_rhf_suite.py --out build/rhf_suite_receipt.json
python scripts/run_synthetic_verification.py --out-dir build/synthetic_verification
```

GitHub Actions runs the same verification on pull requests and `main` and uploads exact-head receipts.

## Scientific boundary

Passing this software suite means only that the executable harness behaves as frozen on synthetic/adversarial inputs. It does **not** establish animal-signal meaning, compositionality, syntax, cross-species generalization, welfare safety, or CRG-C biological credit. Real empirical execution remains rights-, provenance-, preregistration-, and claim-ceiling gated.

## License

No software license has been selected yet. Third-party rights and the intended open-source licensing boundary will be reviewed before a repository license is adopted.
