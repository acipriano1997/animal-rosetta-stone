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
