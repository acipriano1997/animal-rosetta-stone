# D0036 chemical payload calibration — 2026-10-17

Exact Figshare v1 source bytes now pass bounded representability in GDM v1.14.
The chemical case adds a second substantially different real-payload system
alongside D0042's visual-playback mirror exemplar. The Cross-Modal
Generalization Gate remains **NOT_MET**: D0037 electrical/eavesdropping and
D0043 substrate-cue/source-agent payloads remain transport-held. No schema
extension, scientific claim promotion or independent reanalysis follows.

## Source integrity and preservation

[Figshare v1](https://api.figshare.com/v2/articles/28764965/versions/1) lists
one file, `Alarm pheromone_Data.xlsx`, file 53547134, 44,443 bytes. The
downloaded original matches provider MD5
`f3cef5e2bcd1718fb3e44a851b49a348`; its independently computed SHA-256 is
`db31cda214c893f3da8b910668b98babb37922c1fe9dcf1128964125556b24ed`.
The unchanged XLSX is archived in canonical personal Drive Raw Data as
file `1LpIOYTyDowPGvYl00saNNhYhOcgXFZcN`; an independent post-upload
download matches that SHA-256. Raw source rows and files are excluded from
this repository receipt.

The exact v1 provider record specifies CC BY 4.0. Attribution: Córdoba-Aguilar,
Alex; Cruz-López, Leopoldo (2025). *Supporting database for the alarm pheromone
paper*. Figshare. https://doi.org/10.6084/m9.figshare.28764965.v1.
The source workbook is unchanged; the ARS mapping is a derivative. No
additional reuse notice was found in the inspected workbook.

## What was tested

The workbook contains 300 records on each of three behavioral sheets and 88
on EAG: 988 source records, not 988 independent animals or trials. Seven
representative source rows span natural volatiles, synthetic isobutyric and
propanoic acid, empty-chamber control, EAG response and explicit DCM control.
One additional genuinely blank source cell tests missingness separately.

Canonical GDM records are PRV0055, seven intervention records, 33 measurement
records and two rigor records. Exact connector readback verified all 923
written values. The mapping uses existing fields; no event, token or
individual identity is fabricated. Source-cell coordinates are locators,
not biological identifiers. Stimulus concentration and sex codes retain
their source meaning. Synthetic chemical delivery does not imply a
communicative sender.

The workbook defines `NA` as **No response**. Literal NA remains recorded
nonresponse; undefined duration/latency uses NOT_APPLICABLE and is never
silently changed to zero. Isobutyric C112 is a true blank and remains
NOT_RECORDED, without an inferred response state. Distance units are
supported by the published methods; behavioral time units are left explicit
as source-unit-unresolved rather than guessed.

## Boundaries that remain

The [published methods](https://doi.org/10.1111/phen.12497) describe separate
behavioral and avoidance assays. Row alignment does not prove a shared
animal across those assays. Individual IDs, day/block/order keys and EAG
antenna/exposure linkage are absent. Synthetic behavioral control rows say
Empty while the methods describe dichloromethane; their exact correspondence
is unresolved. EAG places DCM in the Sex column for controls, and the
deposited concentration-group counts do not directly recover the reported
six-male/six-female design. These are retained source-admission/reanalysis
questions, not repaired values or a claim of an erroneous publication.

No deposited R analysis, source model or inferential test was executed.
PASS applies only to bounded source-to-GDM representability. The ten-case
purposive tranche does not estimate literature prevalence, activate taxa or
establish semantic, translation, causal or replication claims.

ACEB D0036, SRC0096, SURV-010 and Q0031 now distinguish this verified payload
advance from full reproducibility. Eight other calibration dataset rows had
stale metadata-only scientific-extraction wording reconciled to the already
registered experiments/claims; their bytes remain held. D0042's existing
mirror disposition is preserved.

## Next discriminating work

D0037 v12 file 4640875 and D0043 v3 files 3376157–3376159 have current
provider identities and SHA-256 metadata. API downloads returned 401 and
public file streams returned 403 in this runtime. Actual bytes remain
unacquired. When materializable, match provider digests and map real rows
before reassessing the broad generalization gate. Large archives are not
required for these small-file tests.

Machine-readable aggregate provenance and preserved holds are in
[`evidence/d0036_payload_calibration_20261017.json`](evidence/d0036_payload_calibration_20261017.json).
