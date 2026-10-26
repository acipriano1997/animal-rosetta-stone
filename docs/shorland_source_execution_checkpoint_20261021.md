# Shorland source execution checkpoint — October 21, 2026

Issue #75's previous binary-access failure is superseded for the three publisher
supplements acquired on the Mac October 20. Existing private files and acquisition
receipts were inspected and their current bytes rehashed October 21. No source
rows or third-party code are included in this repository.

Source: Shorland et al. (2022), PLOS ONE 17:e0267574,
[publisher article](https://doi.org/10.1371/journal.pone.0267574).

| Publisher supplement | Bytes | SHA-256 |
| --- | ---: | --- |
| S1 Data, `.s019.csv` | 5,189 | `ca3de1351a6a4548fec86bc48130e71212f4b0f64e100e58e299afcd3b76cda8` |
| S1 File, `.s020.pdf` | 263,932 | `604149d2d273cfc2161de42f74b4f5c14438e6709626f89163e19e3d514edd69` |
| S2 File, `.s021.gz` | 10,168 | `4a6c2b184d4c692be248b03591e3c44e9180901094d7a78ed8efa9b125b934c8` |

The acquisition log identifies exact PLOS `article/file` supplement endpoints,
successful responses and redirect to publisher storage. Temporary signed download
URLs are excluded here. These are local complete-byte hashes, not independently
provided publisher checksums. Package DESCRIPTION states `shorlandetal` 1.0.1,
GPL-3, packaged March 28, 2022. This package declaration does not resolve every
CSV, separate stimulus/audio or redistribution scenario.

The private descriptive source-formula replay was rerun October 21, with output
redirected to a fresh private directory and originals preserved. It found 114 CSV
and package rows, 10 subjects, 12 playback IDs, no duplicated inspected composite
keys and agreement of all eight shared columns. The package additionally contains
precomputed response/offset fields not all regenerated from the CSV. R was 4.6.1,
lme4 2.0.6. The exploratory exploration model's null fit was singular; this remains
an explicit diagnostic rather than being hidden behind a completed process.

The two source formulas executed and reproduced the previous local numerical
outputs. That establishes software execution only. It does not independently
validate the source design, exclusions, stimulus identity, response/offset
construction, caller balance, receiver inference or biological claims. It is not
the full interactive package's validated reproduction, nor a new confirmatory run.

After that replay, all three unmodified publisher assets were preserved in the
verified personal `04.1 — Raw Data — Immutable` folder. Metadata readback confirmed
the intended parent and `shared=false`; complete streaming reads matched every
size/hash above. The private archive manifest retains exact file IDs and source
endpoints. This closes private preservation, not scientific admission or public
redistribution. Local originals remain intact.

Next gate: source-specific rights/embedded-exception and original-stimulus review,
then an explicit bounded admission proposal under existing ACEB owners. The candidate does not
receive invented Source/Study/Dataset identifiers or expand the frozen calibration
tranche. Any RQ0005 secondary receiver/context challenge needs its own justified
dependence units and plan. Sequence order, compositionality, semantic translation
and species-general receiver success remain unsupported by materialization.

## October 26 source-model gate disposition

The original CSV/package were reused, not reacquired. The source-pinned
`scripts/reproduce_shorland_models.py` launcher reads only the trusted package's
data member, never executes its app, and runs the four published default formulas
through `reproduce_shorland_models.R`. Fresh private output is mandatory, outside
source directories. Existing outputs, source aliases and ancestor destinations
are refused. Originals retain their complete-byte fingerprints. The aggregate
receipt is `docs/evidence/shorland_model_audit_20261026.json`; individual fitted
values, model-frame diagnostics and exclusion results remain private.

R 4.6.1 / lme4 2.0.6 / Matrix 1.7.6 reproduce the published rounded LRTs:

| Endpoint | Full/null log likelihood | LRT, 3 df | p |
| --- | --- | --- | --- |
| Exploration | -55.358361 / -58.843668 | 6.970614 | 0.07284033 |
| Expectation | -436.481669 / -438.580603 | 4.197867 | 0.24087553 |

This is numerical source-software concordance with the
[published results](https://doi.org/10.1371/journal.pone.0267574), not independent
biological replication. The original 114 rows comprise 57 paired subject-session
units, 10 subjects and 12 playback assignments. They are not 114 independent
animals or assignments. The source's 4.5-versus-4.75 attendance denominator remains
unreconciled; no source rows were altered to match the prose.

**Zero-time measurement boundary closed in this runtime:** all 114 exploration
rows have unit Bernoulli prior weight and finite log1p-time offsets, including 41
unvisited-zone records. Expectation retains 114 rows in `model.frame`/`nobs`, but
only 73 have positive binomial weight; 41 `cbind(0,0)` rows contribute exactly zero
conditional binomial log likelihood. Total binomial weight 15,593 is recorded time,
not a biological sample size or evidence of independent time observations.
Dropping those rows changes the expectation full-model log likelihood by about
4.2e-12 and positive-row fitted probabilities by at most 6.4e-10. A zero-time row
is not a measured 0% looking rate. Exploration's zero-time conditional contribution
is nonzero; its positive-time-only sensitivity failed with PIRLS step-halving.
That numerical failure is preserved, without substituting a fitted estimate.

The exploration null is singular; both baseline expectation fits are nonsingular.
Default-versus-bobyqa LRTs agree within 6e-9; maximum full-model fitted probability
differences are 3.4e-6 (exploration) and 1.2e-6 (expectation). Conditional and fixed
effect-only fitted values are retained separately. These comparisons establish
optimizer stability here, not software-version equivalence.

All 10 leave-subject-out and all 12 leave-session-out comparisons completed for
each endpoint. Exploration p ranges are 0.01867–0.36117 across subjects and
0.02912–0.21770 across sessions; expectation ranges are 0.01951–0.24247 and
0.000518–0.38354. Six exploration subject omissions and eight session omissions
have at least one singular-fit message. These are post-data exploratory
sensitivities, not confidence intervals, multiple independent tests, or a reason
to select an omission that crosses 0.05. No baseline null establishes absence of
an effect, and no favorable omission establishes receiver understanding.

**Historical runtime gate remains HELD.** The CRAN lme4 1.1-15 source and official
R 3.4.3 `stats/R/family.R` were inspected: the former invokes the family initializer;
the latter maps zero-total two-column binomial rows to internal zero response and
zero weight. That corroborates the zero-trial interpretation statically. An
isolated lme4 1.1-15 build fails against the available modern Eigen API; no R 3.4.3
runtime was restored and the working library was not changed. Source archive
digests and the precise limitation are in the aggregate receipt. Do not claim a
successful historical-version rerun.

The official Figshare API item route returned HTTP 404 on October 26. This is an
access result, not proof that the stimulus library never existed or is withdrawn.
Original stimulus identities, rights and playback assignment remain HELD. No audio
was acquired and the three established PLOS originals were not downloaded again.

**Scientific red team:** the model measures location-specific exploration and
looking time within a selected learned-foraging setting. Session-level caller
condition, repeated subjects, paired zones, post-stimulus occupancy/offset and
interest-selected inclusion limit interpretation. Caller identity remains
perfectly confounded with training status; side learning, caller familiarity and
social access remain competing explanations. A source-faithful discrepancy in
the fixed transformations or likelihoods would falsify numerical concordance;
independent evidence crossing caller identity and learning history is needed to
distinguish a preference-learning interpretation. This archive has no order
manipulation or verified chronology and cannot make that distinction. Maximum
claim: the released formulas reproduce the reported bounded receiver/context
statistics in the stated modern runtime, with explicit opportunity and stability
limits. No causal caller-preference effect, call-order semantics or general
animal decoder is identified. Scientific admission and Q0031 NOT_MET are unchanged.
