# D0029 / R0013 — published clock rules and exclusion-scope reconciliation

**Status:** `PUBLIC_METHODS_RECOVERED_BOUNDED / SOURCE_EVENT_ALIGNMENT_HELD`  
**Date:** 2026-10-19  
**Scientific authority:** original D0029 historical audit and source crosswalk are preserved unchanged. This is an additive paper-to-audit method reconciliation, **not a source-data rerun**.

## Sources, versions, and scope

**Final published paper (primary method authority):** Heesen, R., Austry, D. A., Upton, Z., & Clay, Z. (2022). *Flexible signalling strategies by victims mediate post-conflict interactions in bonobos.* **Philosophical Transactions of the Royal Society B** 377:20210310. https://doi.org/10.1098/rstb.2021.0310 (especially Methods §§2b, 2c(v), 2c(vii)); [open archival article](https://pmc.ncbi.nlm.nih.gov/articles/PMC9358318/).

**Historically earlier, non-peer-reviewed version (secondary evidence only):** Heesen et al., *Tactical signalling by victims increases bystander consolation in bonobos*, January 2022 bioRxiv preprint, https://doi.org/10.1101/2022.01.18.476740. The preprint explicitly reports 150 conflicts considered, six exclusions, with **insufficient visibility or involvement of humans** as the two reason classes; the later published paper reports 144 analysed conflicts and its inclusion conditions. The preprint source has a **distinct version and reuse boundary**; paraphrased source-method facts are not a licence to redistribute it or make it the final source version.

**Frozen deposited audit:** `contracts/d0029_rdc006_v4_crosswalk.json` and `docs/d0029_rdc006_v4_admission.md`, exact original Git blobs restored to `main` in PR #70; Figshare v4 DOI https://doi.org/10.6084/m9.figshare.16910173.v4. Data claims below retain the source's original HELD status; ARS does **not** merge preprint methods/record identities into the v4 deposit.

## Three distinct clocks / denominators

| Concept | Paper-defined rule | What original RDC-006 receipt can and cannot verify |
| --- | --- | --- |
| **Conflict-level inclusion and follow-up** | Include independent conspecific conflicts with the victim fully visible from the **start of aggression until five minutes after the conflict** | Paper-level inclusion rule known. The original crosswalk does not identify a certified conflict-start/end anchor, continuously visible follow-up per conflict or a complete case-selection ledger. **Do not equate the signalling duration or Video_dur with visibility coverage.** |
| **Victim signal-display construction** | Individual signal bouts separated by at least **5 s** response-waiting gap; final bout after **2 min** without further signals; signal display measured first through last bout. Signal display coding normally capped at five minutes, with an ongoing bout allowed to finish beyond the boundary | The original raw ELAN/file-local millisecond durations are internally valid, but source mapping of aggression end, raw tier segmentation, bout ordering, and across-tier labels remains unverified. **A display shorter than five minutes does not prove loss of five-minute follow-up.** |
| **Bout-level consolation/reconciliation persistence** | Look for consolation or reconciliation within **one minute after bout start**, ending earlier if a subsequent bout begins; when two eligible such events occur, the **first** is used | The original main/persistence keys and raw annotations do not establish a unique source-authored cross-tier join for every bout or receiver event. The generic PC_event annotation alone is not a certified source-model endpoint, and raw PC_event totals are **not independent model trials**. |

**Clocks must not be silently interchanged.** It is wrong to use the one-minute *bout-start* response window as a five-minute *conflict-end* follow-up, to use a complete display's component count as if measured before every receiver event, or to count a source event merely because it fell near a bout in file-local milliseconds.

A prospective implementation must preserve source-authored variables for: `conflict_start`, `conflict_end`, `visibility_end`, `signal_bout_start`, `next_bout_start`, `display_start/end`, `PC_event_start`, `event_type` and `event initiator`; unknown values stay **unknown**. After independently validated time origin and joins, an admissible within-bout candidate receiver window would be `[bout_start, min(bout_start + 60s, next_bout_start))` *only as an operational transcription for independent review*, not as an author-confirmed inclusive/exclusive boundary convention. The 'first event only' rule and actual sender/receiver role would then need to be reconstructed from source-coded events rather than filled by guess.

## What the recovered crosswalk does establish

Frozen original record: **144** processed display/conflict keys, **325** main bouts and **329** persistence rows (with unresolved duplicate/unmatched keys), **287** raw PC_event annotations. Within file-local recorded intervals: 176 PC_event starts during ongoing victim signalling displays, 108 after completion, 3 exactly at display end. These are **annotation comparisons**, not 287 independent receiver outcomes, and not measured distances after certified conflict ends. Raw-source `Video_dur` includes 55/145 intervals shorter than five minutes, but that variable must **not** be treated as certified total recording/follow-up coverage. All event eligibility stays HELD.

The archived ARS crosswalk source-identifies **one** candidate raw file whose filename indicates a conflict involving a human. The preprint's high-level 150 → 144 reason-class statement is consistent with the published inclusion restrictions but **does not identify the other five excluded cases, assign their individual reason classes, or prove one-to-one raw-file-to-conflict accounting**. Counts 145 named raw files and 150 reported coded conflicts are not interchangeable case frames. The source-dependent six-record exclusion ledger remains incomplete.

## Priority resolution sequence — source-facing, minimal

1. **Mapping truth:** determine which of the processed/persistence duplicated or unmatched PC/bout records are coding edits versus separate true bouts: PC101 (persistence 4 extra, three with same-number raw candidates), PC66 (one duplicate nonidentical persistence 2; absent main/persistence 6), PC119/PC49 candidate raw count discrepancies, and seven outcome-field disagreements. Require original coding/log or author-specified rules, not index proximity.
2. **Independent temporal anchor and censoring:** obtain the source definitions/locators for aggression/conflict end, file-local time zero, visibility across the five-minute conflict follow-up, why some `Video_dur` intervals are short, and whether the candidate PC_event starts represent the paper's active receiver endpoint. Never code absence of a PC_event tier as an observed negative without coverage/definition.
3. **Decision ledger:** get case IDs and source-coded reason for all six exclusions, with independent conspecific/single-conflict and full-visibility criteria, not inferred missingness.
4. **Endpoint covariate ordering:** require time-relative construction for per-display signal totals, duration, piloerection and audience, as appropriate to each published analysis, before classifying predictors as pre-response or baseline.
5. **Reproducibility:** run exact Figshare v4 archived-source regeneration test after obtaining the publisher-matching archive; isolated 58-pass/1-skip and GitHub CI success verify frozen software contracts, not source model reproducibility.

## Evidence governance

- **Newly resolved:** the three *published method clocks* and the preprint's **exclusion reason categories** at source-document level.
- **Not resolved:** source case identities for the remaining five exclusions; source-authored cross-tier keys; 7 mismatched outcome records; conflict-end timestamp; five-minute true visibility/censoring; raw-to-derived receiver-event mapping; explicit inclusion/exclusion endpoints; source-code reproduction.
- **Scientific state:** `D0029_ADMISSION=HELD_RDC006_SCHEMA_TIMING_DEPENDENCE_REVIEW`; `admission.granted=false`; baseline eligibility 0/321. Bonobo RQ0005 confirmatory run not started, D0026 independent rights/version hold, and frozen cross-modal Q0031 remains **NOT_MET**.

Corresponding author Raphaela Heesen acknowledged the existing source questions October 14, 2026 and indicated a substantive reply would take time. Do not send another follow-up without a later reason and user authorization; these reconciled methods should be used to narrow the eventual answer request, **not** pressure the author or presume consent.
