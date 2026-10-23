# Q0030 ACEB freshness maintenance — 2026-10-22

## October 23 reconciliation

Fresh personal-Drive reads observed ACEB modification time
`2026-10-23T15:15:25.169Z`. The October 22 candidate now rejects these responses
with ACEB modified-time drift, as do the two older pins. The manifest pins the
new value; producer logic and every other authority pin remain unchanged.

Read all nine selected ACEB ranges, all seven documents and complete Drive
revision listings before/after, and both full event/provenance/missingness
corpora. D0020 was read in four contiguous chunks covering rows 1–4300. All ten
authorities retained their identity, title, native type and modification time
across the read. All seven durable document head revisions match their pins.

Prospective replay through the unchanged producer/adapter projects 4,259 events
and five evidence items deterministically. The complete scientific projection
matches the historical October 15 authenticated bundle after excluding only
capture metadata. Private connector responses and replay evidence are retained
outside Git in `ars-main-path-20261023`. Final exact-head verification must
confirm that the committed manifest equals the replayed candidate.

This is offline replay of current authenticated connector responses, not a new
runtime-bearer REST certification. No scientific source, rights, claim ceiling
or Q0031 disposition changes. Later authority edits require fresh reconciliation;
independent review and approved integration remain required.

## October 22 reconciliation — historical

A second complete personal-Drive read observed ACEB modification time
`2026-10-22T23:16:36.775Z`. This supersedes the earlier same-day checkpoint below.
The manifest now pins that value; the original main-branch value and the first
candidate value both reject the current responses with ACEB modified-time drift.

Read all nine manifest-selected ACEB ranges, all seven documents and their full
Drive revision listings, and both event/provenance/missingness corpora. D0020 was
read as four contiguous chunks covering rows 1–4300. All ten authorities matched
identity, title, native type and modification time before and after extraction;
all seven document head revisions matched their pins before and after reading.
Only ACEB modification time changed relative to the manifest. No semantic source
was edited by this maintenance.

The refreshed projection passes the unchanged producer and adapter: 4,259 events,
five evidence items and frozen `COMPARISON_READY_BOUNDED` state. Two projections
match deterministically, and the complete projection equals the historical
October 15 authenticated bundle after excluding only capture metadata. Empty
connector cells retain the earlier null-to-empty-string replay normalization.

Private current source responses and exact-head replay receipts are retained in
the local `ars-main-path-20261022` execution directory, outside Git. Prospective
replay preceded the pin edit; final validation must identify the committed head
and assert that the actual manifest equals the replayed candidate. This remains
offline connector-response replay, not a new runtime-bearer REST certification.
Later authority edits require another reconciliation. Merge remains subject to
independent review; this receipt grants no scientific admission or deployment.

## Earlier same-day checkpoint — historical

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
