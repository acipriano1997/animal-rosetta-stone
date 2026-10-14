# D0026 OSF source admission — metadata-only result

On 2026-10-14, the publication-linked OSF `wes3f` view-only route was readable
from the execution runtime. The prior environment-access hold is superseded by
the exact metadata evidence in `contracts/d0026_osf_metadata_snapshot.json`.
This is an acquisition/admission record, not a new dataset schema or biological
result. The existing ACEB D0026 record and Bonobo species authority control scope.

The [published article](https://doi.org/10.1371/journal.pone.0330250) supplies the
view-only route. The API node identifies the same title and reports `public=false`
with anonymous read permission through that published link. It has no children,
one `osfstorage` provider, two root folders and five files. All listing and version
pages terminated without an unread next page; each file currently has one version.

| Path | OSF file ID | Version | Bytes |
| --- | --- | --- | ---: |
| /data/1_Bonobo_vocrep_randomForest.xlsx | 67ceaf96fadc61f442bb3407 | 1 | 629380 |
| /data/2_Bonobo_vocrep_tSNE.xlsx | 67ceafa1f741140c690411f7 | 1 | 629008 |
| /analysis/0_acoustic_parameter extraction.R | 6745e1e1b9010d48c7fb4f77 | 1 | 2418 |
| /analysis/1_Bonobo_vocrep_randomForest.R | 67ceaf58293a3ed5fbfd737d | 1 | 2594 |
| /analysis/2_vocrep_t-SNE.R | 67ceaf643bf5ff813a040f77 | 1 | 2694 |

The snapshot preserves provider-reported MD5/SHA-256, exact file identities,
version metadata URLs, dates and sizes. These hashes are **not locally byte-verified**.
No XLSX/R source bytes were downloaded, transformed, republished or executed.

The node's explicit licence relationship resolves to OSF licence
`563c1cf88c5e4a3877f9e965`, named **No license**, with a copyright template and no
licence URL. No separate file permission instrument was exposed in the metadata.
Neither the view-only access route nor the article's open-access licence grants
an asserted data/code reuse licence. Publication-version equivalence remains
unconfirmed: one deposited version does not prove which inputs produced the final
paper. Source schema, missingness, dependencies and empirical runtime remain held.

Next gate: resolve data/code reuse permission and final-publication version
identity through a source-authoritative instrument or clarification. The existing
DRO-004 draft remains unsent; this execution pass neither sends nor impersonates
the founder. Once the rights/version gate is resolved, acquire the exact approved
versions, independently check all bytes against the reported hashes, audit schemas
and timing/identity/population/dependence boundaries, and inspect the deposited
runtime before any analysis. D0026 remains an acoustic/production taxonomy lane;
it earns no receiver-use, meaning or compositionality promotion.
