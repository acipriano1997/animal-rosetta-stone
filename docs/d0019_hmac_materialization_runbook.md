# D0019 persistent HMAC and materialization runbook

Status: operational runbook only. This document contains no secret value and must never be used to store one.

## Purpose

D0019 has passed the scientific, provenance, eligibility, and grouped-split pre-model gates, but the canonical 104-row Group-2 normalized corpus is intentionally not created until a persistent identity namespace exists. The same namespace must later be reused for the locked Group-1 transfer so that pseudonymized individual and dyad identifiers are stable across RUN-005 and RUN-006.

## Required secret

Provision one persistent secret named `ARS_D0019_HMAC_KEY`.

Requirements:

- at least 32 bytes of cryptographically random material;
- stored only in an approved secret manager or protected runtime-secret facility;
- never committed to Git;
- never placed in Drive documents, spreadsheets, issue bodies, pull requests, CI artifacts, shell scripts, notebooks, or chat;
- never passed as a command-line argument;
- never regenerated between Group 2 and Group 1;
- access limited to the process performing canonical D0019 materialization/transfer.

Only a non-secret namespace fingerprint is written to the materialization manifest.

## Readiness check before materialization

Use the repository readiness checker before the first empirical materialization:

`scripts/check_d0019_materialization_readiness.py`

The checker reads `ARS_D0019_HMAC_KEY` only from the process environment. It never prints or writes the secret. It may emit the non-secret identity-namespace fingerprint.

Invocation pattern:

```bash
python scripts/check_d0019_materialization_readiness.py \
  --output-dir /path/outside/the/repository/ars-d0019-restricted \
  --expected-head <REVIEWED_COMMIT_SHA>
```

Launch that process from an approved OS/runtime secret manager that injects `ARS_D0019_HMAC_KEY` into the environment. Do not type the real secret into an interactive shell command, where it may enter shell history. Do not paste it into chat, GitHub, Drive, a notebook, a shell script, a command-line argument, or a CI artifact. The readiness checker refuses to report ready unless `--expected-head` is supplied and exactly matches the clean checked-out commit.

The readiness checker must report:

`READY_FOR_SECRET_BACKED_MATERIALIZATION`

It also requires the restricted output path to be outside the Git repository and rejects common cloud-sync folder names. If the repository is dirty, the secret is missing/short/obviously placeholder-like, the frozen source/row-digest contracts drift, or `--expected-head` does not match the reviewed Git commit, stop without materializing.

## Canonical materialization

The executable owner is:

`scripts/admit_d0019_rdc004.py`

The source, crosswalk, eligibility, split, and transfer contracts are already bound in that script. A real materialization must run from an exact reviewed Git commit containing:

- `contracts/d0019_v1_verified_source_snapshot.json`
- `contracts/d0019_rdc004_source_crosswalk_v0_2.json`
- `contracts/pr0005_pd_001_grouping_amendment.json`
- `contracts/d0019_group2_eligibility_rules_v0_1.json`
- `contracts/pr0005_pd_002_split_policy.json`
- `contracts/d0019_rdc004_final_admission_v0_1.json`
- `contracts/d0019_group1_transfer_procedure_v0_1.json`

Set `ARS_D0019_HMAC_KEY` in the process environment through the secret manager, then invoke the materializer with a restricted output directory. Do not echo or print the secret.

The successful state must be:

`RDC004_GROUP2_MATERIALIZED_PR0005_READY`

Expected materialized artifacts:

- `d0019_group2_normalized.csv` — 104 eligible Group-2 rows, pseudonymized identities only;
- `d0019_group2_restricted_provenance.jsonl` — restricted source-identity bridge;
- `d0019_group2_materialization_manifest.json` — source hash, normalized artifact hashes, row count, and non-secret identity-namespace fingerprint.

## Verification before RUN-005

Do not run PR0005 until all of the following are true:

1. normalized row count is exactly 104;
2. eligible source-row digest remains `d6d004eb5a685eed1875e5a430cfb7bb0b6638bb315cf5bf2e2b998588c2be63`;
3. source SHA-256 remains `26f69ee04f5d017d46f72430c0e18e5be960dd77432542644688acd88317075e`;
4. normalized table contains no raw source identity values;
5. Event_IDs are unique and source-row derived;
6. unordered Dyad_ID uses the PD-PR0005-001 identity namespace;
7. the materialization manifest and restricted provenance ledger hashes are preserved;
8. Group 1 has not been materialized or inspected;
9. exact Git commit/runtime versions are recorded;
10. `rdc004_empirical_admission=true` is earned only by the successful materialization, not by the pre-model CI receipt.

## Group-1 firewall

The persistent secret must remain available until RUN-006. Do not rotate or regenerate the D0019 identity namespace between runs unless the entire Group-2 corpus, models, artifacts, and preregistered transfer procedure are invalidated and rebuilt under a logged protocol revision.

RUN-006 may begin only after RUN-005 is fully frozen. It must use the same source pin, crosswalk, eligibility rules, HMAC namespace, and fitted Group-2 preprocessing/model artifacts. Group-1 results may not feed back into RUN-005.

## Failure behavior

If the secret is unavailable, lost, changed, too short, or cannot be safely provided to the runtime, stop at:

`RDC004_PREMODEL_GATES_PASS_READY_FOR_SECRET_BACKED_MATERIALIZATION`

Do not substitute an ephemeral key, plain hashing of identities, raw identities, a different pseudonymization scheme, or a manually edited normalized table.
