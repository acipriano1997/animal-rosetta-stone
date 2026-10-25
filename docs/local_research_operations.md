# Local research integrity and offline verification

Use the existing Python 3.13 environment and Node 22+; these tools never install
dependencies, fetch data, change Drive authority, or grant rights. Python, Node
and the repository may be on an approved Mac or remote runtime.

One consolidated offline batch, from any working directory:

```sh
/path/to/repository/.venv/bin/python /path/to/repository/scripts/verify_local_research.py
```

If Node is installed outside PATH, add `--node /absolute/path/to/node`. Each run
creates a new private directory under `build/`, with dependency checks, pytest,
the offline Workbench verification scripts, RHF and ZERO_SYNTHETIC checks,
per-check logs, start/finish code fingerprints and a final receipt. No network
metadata probes or GitHub Actions are invoked. Check failures stop the batch.
Legacy scripts run in a fresh sandbox so previous build receipts are preserved.
Timeouts terminate the check's process group. A `started.json` without a final
`receipt.json` is an interrupted attempt, never a completed verification. A dirty
checkout remains labeled by its start/finish state; offline PASS is not a clean
commit, authenticated Drive verification, scientific admission or deployment.
Timeout and interruption flags always stop the batch with HELD, including when
the terminated check's shutdown handler exits with code zero.
Child environments also exclude API/access/private keys and authorization headers
(case insensitive), alongside token/secret/password/credential variables and ARS
configuration. This environment-name filter does not revoke filesystem access or
network access and is not a security sandbox.

## Byte inventory and transfer verification

`scripts/research_integrity.py inventory --root RAW --out PRIVATE_MANIFEST`
hashes every regular file without copying it. Run `verify --root DESTINATION
--manifest PRIVATE_MANIFEST --out NEW_PRIVATE_RECEIPT` after a separate authorized
transfer. Both commands require explicit paths; output must be outside the source
root, must not already exist, and is created with mode 0600. Use private directories
for receipts, which may contain sensitive filenames. Do not commit raw research
manifests or media without the ordinary rights/privacy review.

This detects byte-identical copies, changed/missing/extra files, unreadable files,
symlinks, special files, unsafe manifest paths and changes during hashing. Symlinks
and unreadable files produce HELD instead of silently reducing coverage. Repeated
inventory is deterministic when input bytes are unchanged. A partial manifest
cannot pass verification. No files are moved, deleted, deduplicated or repaired.

A matching SHA-256 establishes byte equality only. Provider identity needs the
independent version/file-specific provider record. Local filesystem timestamps
are not camera capture dates. An exported or restored copy is not automatically
an original master. Drive transfer completion requires full-byte readback; a
folder listing, matching filename or successful upload response is insufficient.
No local cloud mount is presumed synchronized.

Source-audit and probe CLI reports use the same exclusive mode-0600 writer.
Choose a fresh report path outside the source tree. Existing reports, source
files and symlink/hardlink aliases are refused, including on a HELD audit path.
This protects originals from an accidental `--out` collision; it does not change
the underlying audit, source data or scientific decisions.

## S0002 gesture supplement audit

`scripts/audit_s0002_gesture_deposit.py --workbook ORIGINAL_S2.xlsx
--code ORIGINAL_S1.R --table ORIGINAL_S1_TABLE.docx --out PRIVATE_RECEIPT`
checks the three exact publisher-source fingerprints acquired October 25 and
parses the original OOXML without changing it or executing the released R code.
The aggregate-only result is frozen in
`docs/evidence/s0002_deposit_audit_20261025.json`. Independent openpyxl counts
agreed with the standard-library workbook reader on all four worksheets.

The deposit contains 2,463 reduced Bonobo rows; published S1 Table sums to
2,321 instances / 33 gestures / 14 outcomes. Their 142-instance difference is
observed arithmetic, **not an identified play exclusion**. No play flag,
response-status column, sequence ID, timestamp or exclusion ledger is deposited.
The Bonobo identity header is `Recipient`, whereas the chimp header is
`signaller`; do not silently equate their roles. Repeated reduced triples cannot
be deduplicated without event identities. Three `Unknown` goals remain unknown.

Both deposited matrices have 22 gesture rows and 11 outcomes. Released S1 R
removes `Foot present`, all-zero in Bonobo, leaving 21 x 11. The latter has 31
shared positives, 141 shared zeros and 172 total matches. With fixed positive
totals, total matches are affine in shared positives, so counting shared zeros
alone is not a permutation-test defect. These are descriptive source checks,
not a rerun of the author's randomization or evidence of receptive transfer.
R0014 remains OPEN and unconditional receiver-response success remains
unidentifiable from this deposit. Source acquisition clears access, not the
unresolved sample flow, source-role/lineage questions or scientific admission.

## Reproduce existing receiver diagnostics

`scripts/replay_receiver_robustness.py --playback ORIGINAL_DATASET8.csv
--spider ORIGINAL_EXP1.csv --out PRIVATE_RECEIPT` reproduces the October 23/25
retrospective source-row calculations on exact frozen archival fingerprints.
`docs/evidence/receiver_robustness_replay_20261025.json` records aggregate outputs.
No new prospective test or provider re-attestation is claimed.

D0037 fits four stimulus-frequency models only on training fish, leaves one
whole fish out, and averages proper log/Brier losses equally over the 13 fish.
Jeffreys/Laplace smoothing and the two worse-performing held-out fish stay
visible. File layout is not chronological trial order. D0043 uses 18 source
pairs and exact rational-decimal enumeration of all 2^18 sign assignments,
retaining the counterexample and the R0015 time-budget exception, plus an
explicitly post-hoc exclusion sensitivity. Ties are not negative outcomes.
These reproduce existing bounded diagnostics; overlapping folds, post-data
selection, shared sites/donors, order and physical-cue confounds remain unresolved.
Q0031 remains NOT_MET. The two designs have no common biological estimand.

## Scientific and publication boundaries

Canonical personal Drive owns scientific state and source-specific reuse limits;
GitHub owns executable verification. Keep objective observations, owner context,
functional hypotheses and claim-admissible findings separate. Neither utility
annotates behavior, assigns meaning, validates a scientific null or promotes a
claim. Human judgments and canonical annotations stay under their existing owner.

IMG_8703 remains **elimination not observed; owner believes none occurred;
independently unconfirmed**. Neither confirmed elimination nor confirmed absence
is warranted. Export clocks cannot replace owner-confirmed dates.

The October 11 Hobaiter reply permits bounded use of public GestureConversations
data with citation; it does not grant unrestricted raw-row or derivative
redistribution. Before publication, independently check each input's version,
licence/consent, citation, redistribution scope and private-media restrictions.
Keep original bytes separate from reversible derivatives and retain uncertainty,
competing hypotheses and previous research decisions. Integrity PASS does not
remove any rights, blinding, dependence, temporal-leakage or evidence-level gate.
