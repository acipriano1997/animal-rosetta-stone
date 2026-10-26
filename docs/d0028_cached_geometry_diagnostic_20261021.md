# D0028: bounded cached-geometry diagnostic — October 21, 2026

This is an **exploratory algorithm diagnostic**, not an exact execution of the
published source at 10,000 permutations, an author-result reproduction, a
biological finding, a correction to the published null, or scientific admission.
ACEB owns D0028 and RQ0005 state; no status or claim was promoted.

The private October 20 full-recomputation attempt ended after about 5,800 MCA
calls. No live process or final receipt remained. Its durable checkpoint has
5,798 completed permutations; it lacks the full runtime state needed for direct
resumption. The original launcher still says RUNNING and must not be treated as
completion evidence. All original attempts and checkpoints were preserved.

`scripts/audit_d0028_cached_geometry.R` supplies a separate, explicitly derived
diagnostic for that verified private archive layout. It checks exact SHA-256 of
D0027 xdata and source script03, requires R 4.6.1 / FactoMineR 2.18, never modifies
those inputs, and requires a new output directory. It reuses the active geometry
only after checking equality of active features, row weights and MCA arguments.
It does not regenerate supplementary projections.

Skipping MCA also skips its internal random draws. An initial attempted cache
that replayed only graphics randomness failed its B100 equivalence check and was
rejected. The accepted diagnostic determines the headless normal-draw count by
matching complete RNG states (688 draws in this runtime), then preserves that
consumption and the audited one plot-only sample per MCA call. It requires:

- agreement of all B100 statistics with the original completed source run within
  absolute tolerance 1e-10, plus identical final RNG state;
- agreement of every one of the saved 5,798 prefix statistics within 1e-10 and
  identical exceedance classifications;
- unchanged active inputs and weights on every cached call.

The accepted local diagnostic returned observed R approximately
0.12121511331160148 and 2,540/10,000 exceedances (p=0.254; Monte Carlo SE about
0.004353). Maximum absolute differences were 6.27e-11 against B100 and 7.62e-11
against the interrupted prefix. This does **not** reproduce the paper's exact
0.2597, nor does that difference establish an error: runtime, source parameters
and the intended author implementation remain separate reproducibility questions.
The cached result is not a completed full-recomputation attempt.

Reproduction, on the existing verified private archive and installed R library:

```sh
R_LIBS_USER=/private/archive/rlib Rscript --vanilla scripts/audit_d0028_cached_geometry.R /private/archive /private/new-diagnostic-directory
```

The archive must contain `sources/xdata.txt`, exact `sources/03_weighted_mca_permutation_test.R`,
`original-100-managed/source-results.rds` and
`derivative-10000-guarded-20261020T211358Z/permutation-checkpoint.rds`.
Use only trusted local RDS inputs. The tool is source-specific, not a general
permutation engine or a validation of biological exchangeability. No source rows,
original author code, RDS files or media are distributed in this repository.
Retain the original dataset/code attribution and source-specific rights gates.
The 700-versus-735 source-count discrepancy, post-call feature leakage constraints,
caller/session dependence, null validity and semantic ceiling remain unresolved.
