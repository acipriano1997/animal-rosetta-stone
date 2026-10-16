# Frozen cross-modal calibration metadata intake — 2026-10-16

## Disposition

Exactly ten preselected cases were registered in the canonical ACEB as metadata-only candidates: SRC0091–SRC0110, S0104–S0113, D0034–D0043, SURV-008–SURV-017 and Q0031. The 51 new rows were read back field-for-field, with wrapping/alignment and absence of unintended formulas, validation or chips checked. Browser/local rendering was unavailable; visual verification is limited to native cell-format readback.

This is a purposive, open-data-enriched framework stress-test tranche, not a representative literature sample. No new species/workstream activation, experiment, claim, claim–evidence link, empirical reanalysis or scientific admission occurred. No calibration payload was downloaded. No source rows or provider payloads are included in Git.

## Registered cases

| Case | Study / dataset | Article DOI | Dataset DOI | Record-level rights | Version state |
| --- | --- | --- | --- | --- | --- |
| 1: Honey bee | S0104 / D0034 | 10.1073/pnas.2518687123 | 10.5281/zenodo.10892587 | CC BY 4.0 | record DOI; numeric version label not exposed by DataCite |
| 2: Treehopper | S0105 / D0035 | 10.1093/jeb/voad010 | 10.6078/D1QF08 | CC0 | versionNumber 6; immutable /api/v2/versions/296605 |
| 3: Kissing bug | S0106 / D0036 | 10.1111/phen.12497 | 10.6084/m9.figshare.28764965.v1 | CC BY 4.0 | 1 |
| 4: Electric eel and knifefish | S0107 / D0037 | 10.1016/j.cub.2026.02.026 | 10.5061/dryad.1ns1rn95w | CC0 | versionNumber 12; immutable /api/v2/versions/429568 |
| 5: Siberian jay | S0108 / D0038 | 10.1098/rsos.250960 | 10.5061/dryad.kwh70rzjm | CC0 | versionNumber 3; immutable-version URI to be recovered from saved receipt before acquisition |
| 6: Rummy-nose tetra | S0109 / D0039 | 10.1242/jeb.247507 | 10.5061/dryad.ngf1vhj2g | CC0 | versionNumber 5; immutable-version URI to be recovered from saved receipt before acquisition |
| 7: African elephant | S0110 / D0040 | 10.1098/rsos.242203 | 10.5281/zenodo.15425872 | CC BY 4.0 | record DOI; numeric version label not exposed by DataCite |
| 8: Common cuttlefish | S0111 / D0041 | 10.1086/677545 | 10.5061/dryad.c6011 | CC0 | versionNumber 1; immutable /api/v2/versions/19540 |
| 9: Bioluminescent ostracod | S0112 / D0042 | 10.1098/rspb.2023.2311 | 10.5061/dryad.6m905qg6c | CC0 | versionNumber 3; immutable /api/v2/versions/264673 |
| 10: Jumping spider | S0113 / D0043 | 10.1098/rsos.240658 | 10.5061/dryad.pc866t1xc | CC0 | versionNumber 3; immutable /api/v2/versions/309318 |

## Provenance and bounded changes

Primary Crossref article metadata and repository metadata were checked on 2026-10-16. The seven Dryad API records explicitly state CC0, public visibility and curationStatus Published. Their native versionStatus field says submitted; that field was preserved without mislabeling the public records as unpublished. The Figshare v1 API explicitly states CC BY 4.0; its one listed workbook has provider MD5 f3cef5e2bcd1718fb3e44a851b49a348, not locally byte-verified.

Both Zenodo landing records returned HTTP 403, but their exact DOI records in the DataCite API explicitly register CC BY 4.0 through cern.zenodo. This resolves the two prior dataset-record license gaps without projecting article rights. It does not verify a current Zenodo file inventory, numeric version label, embedded rights or payload bytes. The honeybee record is related to concept DOI 10.5281/zenodo.10892586 and the elephant record to 10.5281/zenodo.15425871; the frozen record DOIs above remain the targets.

Primary article data availability connects the honeybee, kissing-bug and elephant records; Dryad primary_article relations connect the other seven. Wiley full-page fetch was subsequently blocked (403); its indexed primary Data Availability statement identifies the exact Figshare v1 DOI, while a full scientific extraction remains held. The elephant full text is available as PMC12308342.

Metadata endpoints:
- Crossref: https://api.crossref.org/works/{URL-encoded article DOI}
- Dryad: https://datadryad.org/api/v2/datasets/{URL-encoded doi:dataset DOI}
- Figshare: https://api.figshare.com/v2/articles/28764965
- DataCite: https://api.datacite.org/dois/10.5281/zenodo.10892587 and https://api.datacite.org/dois/10.5281/zenodo.15425872

## Scientific and acquisition gates

Full primary methods/status/critique review, experiment splitting, sample and population details, controls, exclusions, funding/conflicts, scoped positive/null/contrary claims and evidence links remain incomplete. Crossref returned no correction/retraction update in the checked metadata; that is not a clean-status certification. Treehopper online publication was December 2023 and its issue is January 2024; the production note “corrected and typeset” is not treated as a separate scientific correction.

The intake notes preserve the treehopper null-function alternatives, jay null social modulation, hydrodynamic signal/cue uncertainty, context-dependent electrical source/sender roles, human-directed elephant scope, cuttlefish disturbance boundary, ostracod higher-taxon identity and spider cue interpretation. Provisional mappings are calibration hypotheses, not accepted ARS claims. No semantic, causal, independence, replication or generality promotion follows from these records.

Dryad immutable-version URIs for D0038/D0039 must be recovered from the saved provider receipts and reverified before acquisition. File manifests, exact bytes/checksums, embedded or third-party rights, processing lineage and code/environment remain gated for every case. Large packages were not downloaded solely for registration.

OSF D0026 still returned HTTP 503 maintenance. Q0029 scientific key/dependence holds remain as recorded in PRs #51/#53. No author outreach, blind evaluation or raw archive extraction occurred.

## Authority maintenance

ACEB changed in this pass. A separate one-field Workbench modified-time pin PR must pass exact-head CI, an immediate premerge Drive timestamp recheck, expected-head merge and exact-main CI. The final audit/forecast disposition records that proof. This report does not itself certify that later maintenance.
