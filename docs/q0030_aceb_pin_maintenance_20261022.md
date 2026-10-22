# Q0030 ACEB freshness maintenance — 2026-10-22

The Workbench producer's ACEB pin is behind legitimate registry updates.
Personal-Drive connector metadata before and after a complete bounded read
identified the native Evidence Bank with modification time
`2026-10-21T19:48:17.553Z`. The prior pin was
`2026-10-20T01:18:38.915Z`.

The only executable change is `aceb.observed_modified_time` in
`src/ars_workbench/data/workbench_canonical_sources.json`. This note records
its verification. All seven document identities, native types, titles, Drive
head revisions and modification times matched their existing pins. Both event
corpus identities, titles, native types and modification times also matched.
All ten authorities had unchanged identities/titles/types/times at the final
metadata check. No scientific authority was edited.

Private replay used the current connector reads for every manifest-selected
ACEB range, all seven documents, and all event/provenance/missingness ranges.
The D0020 event read used four consecutive bounded chunks. It projected all
36 D0018 and 4,223 D0020 events, five evidence items and the frozen
`COMPARISON_READY_BOUNDED` state through the existing producer and adapter.
The old pin rejected the current responses. The refreshed pin passed, and two
projections matched using the existing capture-metadata exclusion helper.
After those same exclusions, the complete projection also matched the private
2026-10-15 authenticated bundle: no scientific projection changed.

Connector JSON nulls for empty cells were normalized to empty strings at the
private replay boundary. No nonempty cell changed. Direct CellData inspection
confirmed that Claim-Evidence Links F58 is empty; the replay must not render
that blank Dataset_ID as the literal string `None`.

This is **offline replay of authenticated connector responses**, not a new
runtime-bearer REST producer certification. The historical 2026-10-15 live
producer PASS remains historical. Private source responses, row-level events,
documents and generated bundles stay outside Git. The accepted private receipt
is `freshness-replay-receipt-v3.json`; prior diagnostic outputs are superseded
and preserved. A local JSON-normalization/comparison helper was corrected
before the accepted replay; no producer code was changed.

`FAIL_CLOSED_ON_PIN_DRIFT` remains active. Scientific admission, rights,
uncertainty, evidence ceilings and the Q0031 `NOT_MET` disposition are
unchanged. Any later authority edit requires fresh reconciliation.

Merge remains subject to the existing exact-head verification and independent
review gate. A passing local replay does not deploy this candidate.
