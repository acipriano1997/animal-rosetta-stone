"""Aggregate-only D0019 Group-2 eligibility/missingness audit for RDC-004."""
from __future__ import annotations

import argparse
from collections import Counter
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
    "sex_rec":"J","dyad":"K","rel_dom":"L","face":"M","context_dyad":"N",
    "GEST":"O","REACT":"P",
}


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
                raise ValueError("Invalid source shared-string index")
            return strings[idx]
        if kind=="inlineStr":
            inline=cell.find(S+"is")
            return "".join(x.text or "" for x in inline.iter(S+"t")) if inline is not None else ""
        return v.text if v is not None and v.text is not None else ""
    return decode


def group2_eligibility(raw: bytes, expected_headers: list[str], rules: dict) -> dict:
    with ZipFile(BytesIO(raw)) as book:
        if sum(x.file_size for x in book.infolist())>8_000_000:
            raise ValueError("Source decompression bound exceeded")
        decode=_decoder(book)
        root=ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
        dim=root.find(S+"dimension")
        if dim is None or dim.get("ref")!="A1:P253":
            raise ValueError("Rawdata dimension differs from H1 pin")
        data=root.find(S+"sheetData")
        if data is None:
            raise ValueError("Missing Rawdata sheet data")
        rows=data.findall(S+"row")
        header=next((r for r in rows if r.get("r")=="1"),None)
        if header is None or [decode(c) for c in header.findall(S+"c")]!=expected_headers:
            raise ValueError("Source headers differ from H1 pin")

        expected_domains={
            "Dataset":set(rules["rules"]["year"]["allowed"]),
            "sex_init":set(rules["rules"]["initiator_sex"]["allowed"]),
            "sex_rec":set(rules["rules"]["recipient_sex"]["allowed"]),
            "rel_dom":set(rules["rules"]["rank_relationship"]["allowed"]),
            "GEST":set(rules["rules"]["gesture"]["allowed"]),
            "face":set(rules["rules"]["face"]["allowed"]),
            "context_dyad":set(rules["rules"]["context"]["allowed"]),
            "REACT":set(rules["rules"]["response"]["allowed"]),
        }

        exclusion_counts=Counter()
        invalid_counts=Counter()
        blank_counts=Counter()
        retained_unknown_counts=Counter()
        eligible_rows=[]
        eligible_pairs=set()
        group2_rows=0
        group1_other_cells_decoded=False

        for row in rows:
            number=int(row.get("r","0"))
            if number<=1:
                continue
            cells={c.get("r"):c for c in row.findall(S+"c")}
            group=decode(cells.get(f"F{number}")).strip()
            if group!="2":
                # Holdout firewall: after structural partition selection no other Group-1 cell is decoded.
                continue
            group2_rows+=1
            values={name:decode(cells.get(f"{col}{number}")).strip() for name,col in COLS.items()}
            reasons=[]

            for field,allowed in expected_domains.items():
                value=values[field]
                if not value:
                    blank_counts[field]+=1
                elif value not in allowed:
                    invalid_counts[field]+=1

            initiator,recipient=values["initiator"],values["recipient"]
            if not initiator:
                reasons.append("MISSING_INITIATOR")
            if not recipient:
                reasons.append("MISSING_RECIPIENT")
            if initiator and recipient and initiator==recipient:
                reasons.append("SELF_DIRECTED_ID_CONFLICT")
            if values["Dataset"] not in expected_domains["Dataset"]:
                reasons.append("INVALID_YEAR")
            if values["GEST"] not in expected_domains["GEST"]:
                reasons.append("GESTURE_UNAVAILABLE_OR_INVALID")
            if values["face"]=="NA" or values["face"] not in expected_domains["face"]:
                reasons.append("FACE_UNAVAILABLE_OR_INVALID")
            if values["context_dyad"]=="NA" or values["context_dyad"] not in expected_domains["context_dyad"]:
                reasons.append("CONTEXT_UNAVAILABLE_OR_INVALID")
            if values["REACT"]=="NA" or values["REACT"] not in expected_domains["REACT"]:
                reasons.append("OUTCOME_UNAVAILABLE_OR_INVALID")

            if values["rel_dom"]=="NA":
                retained_unknown_counts["rel_dom"]+=1
            if not values["sex_init"]:
                retained_unknown_counts["sex_init"]+=1
            if not values["sex_rec"]:
                retained_unknown_counts["sex_rec"]+=1

            if reasons:
                for reason in set(reasons):
                    exclusion_counts[reason]+=1
            else:
                eligible_rows.append(number)
                eligible_pairs.add(tuple(sorted((initiator,recipient))))

        if group2_rows!=149:
            raise ValueError("Group-2 source row count differs from frozen 149")
        invalid_total=sum(invalid_counts.values())
        digest=hashlib.sha256(
            ("D0019_ELIGIBLE_V0.1|"+rules["source_sha256"]+"|"+
             ",".join(str(x) for x in eligible_rows)).encode()
        ).hexdigest()
        return {
            "source_group2_rows":149,
            "eligible_primary_rows":len(eligible_rows),
            "excluded_primary_rows":149-len(eligible_rows),
            "exclusion_reason_counts":dict(sorted(exclusion_counts.items())),
            "source_blank_counts_for_audited_fields":dict(sorted(blank_counts.items())),
            "retained_explicit_unknown_counts":dict(sorted(retained_unknown_counts.items())),
            "invalid_token_counts":dict(sorted(invalid_counts.items())),
            "all_tokens_within_frozen_domains":invalid_total==0,
            "eligible_unordered_dyad_count":len(eligible_pairs),
            "eligible_source_row_set_sha256":digest,
            "eligibility_rules_version":rules["eligibility_version"],
            "outcome_class_frequencies_computed":False,
            "predictor_class_frequencies_computed":False,
            "row_level_records_emitted":False,
            "identity_values_emitted":False,
            "group1_nonpartition_cells_decoded":group1_other_cells_decoded,
            "group1_holdout_opened":False,
        }


def audit(item: dict,pins: dict,crosswalk: dict,amendment: dict,rules: dict,fetch) -> dict:
    receipt={
        "dataset_id":"D0019","phase":"H4_GROUP2_ELIGIBILITY_AGGREGATE",
        "state":"HELD_SOURCE_OR_RULE_MISMATCH","source_bytes_stored":False,
        "group1_holdout_opened":False,"group1_outcomes_accessed":False,
        "rdc004_empirical_admission":False,"pr0005_executed":False,
        "scientific_effect":"NONE","crg_c_credit":"UNMET",
    }
    if (
        rules.get("source_sha256")!=pins["file"]["sha256"]
        or rules.get("crosswalk_ref")!="contracts/d0019_rdc004_source_crosswalk_v0_2.json"
        or rules.get("grouping_amendment_ref")!="contracts/pr0005_pd_001_grouping_amendment.json"
        or crosswalk.get("version")!="source-crosswalk-v0.2"
        or crosswalk.get("empirical_admission") is not False
        or amendment.get("status")!="FROZEN_PRE_OUTCOME_SOURCE_SCHEMA_AMENDMENT"
        or amendment.get("evidence",{}).get("group1_outcomes_accessed") is not False
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
        summary=group2_eligibility(raw,pins["sheets"][0]["source_header_candidates"],rules)
        receipt["eligibility"]=summary
        if (
            summary["all_tokens_within_frozen_domains"]
            and summary["eligible_primary_rows"]>0
            and summary["eligible_unordered_dyad_count"]>=2
            and summary["group1_holdout_opened"] is False
        ):
            receipt["state"]="H4_ELIGIBILITY_STRUCTURE_PASS_SPLIT_SUPPORT_PENDING"
        else:
            receipt["state"]="HELD_ELIGIBILITY_OR_DOMAIN"
    except (OSError,ValueError,TypeError,KeyError,IndexError,BadZipFile,ET.ParseError) as exc:
        receipt["state"]="HELD_ELIGIBILITY_SOURCE"
        receipt["error_type"]=type(exc).__name__
        receipt["error_summary"]=str(exc)[:180]
    return receipt


def main():
    ap=argparse.ArgumentParser(description="Audit aggregate D0019 Group-2 eligibility only")
    ap.add_argument("--pins",default="contracts/d0019_v1_verified_source_snapshot.json")
    ap.add_argument("--crosswalk",default="contracts/d0019_rdc004_source_crosswalk_v0_2.json")
    ap.add_argument("--amendment",default="contracts/pr0005_pd_001_grouping_amendment.json")
    ap.add_argument("--rules",default="contracts/d0019_group2_eligibility_rules_v0_1.json")
    ap.add_argument("--out",default="build/d0019_group2_eligibility_audit.json")
    args=ap.parse_args()
    try:
        from scripts.probe_d0019_source import public_item,fetch_source
    except ModuleNotFoundError:
        from probe_d0019_source import public_item,fetch_source
    pins=json.loads(Path(args.pins).read_text())
    crosswalk=json.loads(Path(args.crosswalk).read_text())
    amendment=json.loads(Path(args.amendment).read_text())
    rules=json.loads(Path(args.rules).read_text())
    try:
        receipt=audit(public_item(),pins,crosswalk,amendment,rules,fetch_source)
    except (OSError,ValueError,TypeError) as exc:
        receipt={"dataset_id":"D0019","phase":"H4_GROUP2_ELIGIBILITY_AGGREGATE",
                 "state":"HELD_SOURCE_METADATA","error_type":type(exc).__name__,
                 "error_summary":str(exc)[:180],"source_bytes_stored":False,
                 "group1_holdout_opened":False,"group1_outcomes_accessed":False,
                 "rdc004_empirical_admission":False,"pr0005_executed":False}
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"state":receipt["state"],
                      "eligible_rows":receipt.get("eligibility",{}).get("eligible_primary_rows"),
                      "group1_outcomes_accessed":False,"pr0005_executed":False,
                      "output":str(out)}))


if __name__=="__main__":
    main()
