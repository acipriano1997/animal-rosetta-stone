"""Outcome-blind-to-frequency D0019 split-support audit for PR0005."""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

S="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
COLS={
    "Dataset":"A","initiator":"E","group":"F","sex_init":"G","recipient":"I",
    "sex_rec":"J","rel_dom":"L","face":"M","context_dyad":"N","GEST":"O","REACT":"P",
}
REGISTERED_RESPONSES={"affil","avoid"}


def _decoder(book: ZipFile):
    strings=[]
    if "xl/sharedStrings.xml" in book.namelist():
        root=ET.fromstring(book.read("xl/sharedStrings.xml"))
        strings=["".join(t.text or "" for t in si.iter(S+"t")) for si in root.findall(S+"si")]
    def decode(cell):
        if cell is None:
            return ""
        if cell.find(S+"f") is not None:
            raise ValueError("Formula present in audited source field")
        v=cell.find(S+"v")
        kind=cell.get("t")
        if kind=="s":
            if v is None or v.text is None:
                return ""
            idx=int(v.text)
            if idx<0 or idx>=len(strings):
                raise ValueError("Invalid shared-string index")
            return strings[idx]
        if kind=="inlineStr":
            inline=cell.find(S+"is")
            return "".join(x.text or "" for x in inline.iter(S+"t")) if inline is not None else ""
        return v.text if v is not None and v.text is not None else ""
    return decode


def _eligible_group2_rows(raw: bytes, headers: list[str], rules: dict) -> list[dict]:
    with ZipFile(BytesIO(raw)) as book:
        if sum(x.file_size for x in book.infolist())>8_000_000:
            raise ValueError("Source decompression bound exceeded")
        decode=_decoder(book)
        root=ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
        dim=root.find(S+"dimension")
        if dim is None or dim.get("ref")!="A1:P253":
            raise ValueError("Rawdata dimension drift")
        data=root.find(S+"sheetData")
        if data is None:
            raise ValueError("Missing Rawdata sheetData")
        rows=data.findall(S+"row")
        header=next((r for r in rows if r.get("r")=="1"),None)
        if header is None or [decode(c) for c in header.findall(S+"c")]!=headers:
            raise ValueError("Source header differs from H1 pin")

        allowed={
            "Dataset":set(rules["rules"]["year"]["allowed"]),
            "GEST":set(rules["rules"]["gesture"]["allowed"]),
            "face":set(rules["rules"]["face"]["allowed"]),
            "context_dyad":set(rules["rules"]["context"]["allowed"]),
            "REACT":set(rules["rules"]["response"]["allowed"]),
        }
        eligible=[]
        group2_count=0
        for row in rows:
            n=int(row.get("r","0"))
            if n<=1:
                continue
            cells={c.get("r"):c for c in row.findall(S+"c")}
            group=decode(cells.get(f"F{n}")).strip()
            if group!="2":
                # Hard holdout firewall: do not decode any other Group-1 cell.
                continue
            group2_count+=1
            values={name:decode(cells.get(f"{col}{n}")).strip() for name,col in COLS.items()}
            initiator,recipient=values["initiator"],values["recipient"]
            valid=(
                bool(initiator) and bool(recipient) and initiator!=recipient
                and values["Dataset"] in allowed["Dataset"]
                and values["GEST"] in allowed["GEST"]
                and values["face"] in allowed["face"] and values["face"]!="NA"
                and values["context_dyad"] in allowed["context_dyad"] and values["context_dyad"]!="NA"
                and values["REACT"] in allowed["REACT"] and values["REACT"]!="NA"
            )
            if valid:
                eligible.append({
                    "source_row":n,
                    "dyad":tuple(sorted((initiator,recipient))),
                    "initiator":initiator,
                    "response":values["REACT"],
                })
        if group2_count!=149:
            raise ValueError("Group-2 row count differs from frozen source partition")
        return eligible


def _logo_support(rows: list[dict], group_field: str) -> dict:
    groups=sorted({r[group_field] for r in rows},key=lambda x:repr(x))
    all_indices=set(range(len(rows)))
    seen_test=set()
    all_train_two_classes=True
    no_group_leakage=True
    test_sizes=[]
    for group in groups:
        test={i for i,r in enumerate(rows) if r[group_field]==group}
        train=all_indices-test
        if not test or not train:
            raise ValueError("Empty train/test fold under frozen leave-one-group-out policy")
        test_sizes.append(len(test))
        seen_test.update(test)
        train_classes={rows[i]["response"] for i in train}
        if train_classes!=REGISTERED_RESPONSES:
            all_train_two_classes=False
        train_groups={rows[i][group_field] for i in train}
        test_groups={rows[i][group_field] for i in test}
        if train_groups & test_groups:
            no_group_leakage=False
    return {
        "fold_count":len(groups),
        "all_eligible_events_tested_exactly_once":seen_test==all_indices,
        "all_training_folds_have_both_registered_response_classes":all_train_two_classes,
        "zero_train_test_group_overlap":no_group_leakage,
        "test_fold_size_min":min(test_sizes),
        "test_fold_size_max":max(test_sizes),
        "test_fold_size_sum":sum(test_sizes),
    }


def split_support(raw: bytes, headers: list[str], rules: dict, split_policy: dict) -> dict:
    rows=_eligible_group2_rows(raw,headers,rules)
    row_digest=hashlib.sha256(
        ("D0019_ELIGIBLE_V0.1|"+rules["source_sha256"]+"|"+
         ",".join(str(r["source_row"]) for r in rows)).encode()
    ).hexdigest()
    if len(rows)!=split_policy["support_gate"]["expected_eligible_rows"]:
        raise ValueError("Eligible row count differs from frozen split-policy expectation")
    if row_digest!=split_policy["support_gate"]["eligible_source_rows_digest"]:
        raise ValueError("Eligible source-row set differs from frozen H4 digest")
    if {r["response"] for r in rows}!=REGISTERED_RESPONSES:
        raise ValueError("Eligible response domain differs from the two registered classes")

    primary=_logo_support(rows,"dyad")
    robustness=_logo_support(rows,"initiator")
    if primary["fold_count"]!=split_policy["support_gate"]["expected_unordered_dyads"]:
        raise ValueError("Primary unordered-dyad count differs from frozen H4 expectation")

    pass_gate=(
        primary["all_eligible_events_tested_exactly_once"]
        and primary["all_training_folds_have_both_registered_response_classes"]
        and primary["zero_train_test_group_overlap"]
        and primary["test_fold_size_sum"]==len(rows)
        and robustness["all_eligible_events_tested_exactly_once"]
        and robustness["all_training_folds_have_both_registered_response_classes"]
        and robustness["zero_train_test_group_overlap"]
        and robustness["test_fold_size_sum"]==len(rows)
    )
    return {
        "eligible_rows":len(rows),
        "eligible_source_row_set_sha256":row_digest,
        "registered_response_domain_present":True,
        "primary_leave_unordered_dyad_out":primary,
        "robustness_leave_initiator_out":robustness,
        "support_gate_passed":pass_gate,
        "outcome_class_counts_or_frequencies_emitted":False,
        "row_level_assignments_emitted":False,
        "identity_or_group_values_emitted":False,
        "group1_nonpartition_cells_decoded":False,
        "group1_holdout_opened":False,
    }


def audit(item: dict,pins: dict,crosswalk: dict,amendment1: dict,eligibility: dict,split_policy: dict,fetch) -> dict:
    receipt={
        "dataset_id":"D0019","phase":"H5_GROUPED_SPLIT_SUPPORT",
        "state":"HELD_SOURCE_OR_POLICY_MISMATCH",
        "source_bytes_stored":False,"group1_holdout_opened":False,
        "group1_outcomes_accessed":False,"rdc004_empirical_admission":False,
        "pr0005_executed":False,"scientific_effect":"NONE","crg_c_credit":"UNMET",
    }
    if (
        crosswalk.get("version")!="source-crosswalk-v0.2"
        or crosswalk.get("empirical_admission") is not False
        or amendment1.get("status")!="FROZEN_PRE_OUTCOME_SOURCE_SCHEMA_AMENDMENT"
        or eligibility.get("status")!="FROZEN_PRE_MODEL_GROUP2_ELIGIBILITY"
        or split_policy.get("deviation_id")!="PD-PR0005-002"
        or split_policy.get("status")!="FROZEN_PRE_OUTCOME_PERFORMANCE"
        or eligibility.get("source_sha256")!=pins["file"]["sha256"]
    ):
        return receipt
    if item.get("id")!=pins["source_item_id"] or item.get("version")!=1 or item.get("doi")!=pins["doi"]:
        receipt["state"]="HELD_SOURCE_IDENTITY"; return receipt
    lic=item.get("license") or {}
    if not isinstance(lic,dict) or {k:lic.get(k) for k in ("name","url")}!=pins["license_as_reported"]:
        receipt["state"]="HELD_LICENSE"; return receipt
    files=item.get("files")
    if not isinstance(files,list) or len(files)!=1:
        receipt["state"]="HELD_FILE_INVENTORY"; return receipt
    f=files[0]; expected=pins["file"]
    if (
        f.get("id")!=expected["id"] or f.get("name")!=expected["name"]
        or f.get("size")!=expected["bytes"]
        or (f.get("computed_md5") or f.get("supplied_md5"))!=expected["md5"]
    ):
        receipt["state"]="QUARANTINED_SOURCE_DRIFT"; return receipt
    parsed=urlparse(str(f.get("download_url")))
    if parsed.scheme!="https" or parsed.hostname!="ndownloader.figshare.com" or parsed.path!=f"/files/{expected['id']}":
        receipt["state"]="QUARANTINED_SOURCE_LOCATION"; return receipt
    try:
        raw=fetch(f.get("download_url"),expected["bytes"])
        if len(raw)!=expected["bytes"] or hashlib.sha256(raw).hexdigest()!=expected["sha256"]:
            raise ValueError("Source bytes differ from exact H1 SHA-256")
        support=split_support(raw,pins["sheets"][0]["source_header_candidates"],eligibility,split_policy)
        receipt["split_support"]=support
        receipt["state"]="H5_GROUPED_SPLIT_SUPPORT_PASS_FINAL_ADMISSION_PENDING" if support["support_gate_passed"] else "HELD_SPLIT"
    except (OSError,ValueError,TypeError,KeyError,IndexError,BadZipFile,ET.ParseError) as exc:
        receipt["state"]="HELD_SPLIT_SUPPORT_SOURCE"
        receipt["error_type"]=type(exc).__name__
        receipt["error_summary"]=str(exc)[:180]
    return receipt


def main():
    ap=argparse.ArgumentParser(description="Audit D0019 grouped split support without reporting class balance")
    ap.add_argument("--pins",default="contracts/d0019_v1_verified_source_snapshot.json")
    ap.add_argument("--crosswalk",default="contracts/d0019_rdc004_source_crosswalk_v0_2.json")
    ap.add_argument("--amendment1",default="contracts/pr0005_pd_001_grouping_amendment.json")
    ap.add_argument("--eligibility",default="contracts/d0019_group2_eligibility_rules_v0_1.json")
    ap.add_argument("--split-policy",default="contracts/pr0005_pd_002_split_policy.json")
    ap.add_argument("--out",default="build/d0019_group2_split_support.json")
    args=ap.parse_args()
    try:
        from scripts.probe_d0019_source import public_item,fetch_source
    except ModuleNotFoundError:
        from probe_d0019_source import public_item,fetch_source
    objs=[json.loads(Path(p).read_text()) for p in (
        args.pins,args.crosswalk,args.amendment1,args.eligibility,args.split_policy
    )]
    try:
        receipt=audit(public_item(),*objs,fetch_source)
    except (OSError,ValueError,TypeError) as exc:
        receipt={"dataset_id":"D0019","phase":"H5_GROUPED_SPLIT_SUPPORT",
                 "state":"HELD_SOURCE_METADATA","error_type":type(exc).__name__,
                 "error_summary":str(exc)[:180],"source_bytes_stored":False,
                 "group1_holdout_opened":False,"group1_outcomes_accessed":False,
                 "rdc004_empirical_admission":False,"pr0005_executed":False}
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({
        "state":receipt["state"],
        "eligible_rows":receipt.get("split_support",{}).get("eligible_rows"),
        "primary_folds":receipt.get("split_support",{}).get("primary_leave_unordered_dyad_out",{}).get("fold_count"),
        "robustness_folds":receipt.get("split_support",{}).get("robustness_leave_initiator_out",{}).get("fold_count"),
        "group1_outcomes_accessed":False,"pr0005_executed":False,"output":str(out)
    }))


if __name__=="__main__":
    main()
