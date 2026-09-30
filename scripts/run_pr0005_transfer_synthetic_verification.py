"""ZERO_SYNTHETIC end-to-end verification of locked PR0005 RUN-006."""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from ars_receiver_harness.pr0005_artifacts import freeze_run005_package
from ars_receiver_harness.pr0005_transfer import run_d0019_group1_transfer
try:
    from scripts.run_pr0005_synthetic_verification import synthetic_group2
except ModuleNotFoundError:
    from run_pr0005_synthetic_verification import synthetic_group2

HEADERS=[
    "Dataset","event","clip_old","time","initiator","group","sex_init","ini_approaching",
    "recipient","sex_rec","dyad","rel_dom","face","context_dyad","GEST","REACT"
]


def _namespace_fingerprint(secret: bytes) -> str:
    return hashlib.sha256(
        b"D0019_NAMESPACE_PUBLIC_FINGERPRINT|" + hashlib.sha256(secret).digest()
    ).hexdigest()


def synthetic_source_workbook() -> bytes:
    header="".join(
        f'<c r="{chr(65+i)}1" t="inlineStr"><is><t>{name}</t></is></c>'
        for i,name in enumerate(HEADERS)
    )
    rows=[f'<row r="1">{header}</row>']
    for idx in range(252):
        n=idx+2
        if idx<103:
            local=idx
            initiator=f"G1I{local%17:02d}"
            recipient=f"G1R{(local*3+1)%19:02d}"
            gesture="SG" if local%2==0 else "BG"
            face=("neutral","bared","hoot")[local%3]
            context="pos" if (local//2)%2==0 else "neg"
            response="affil" if local%2==0 else "avoid"
            rank="todom" if local%3 else "nottodom"
            cells=[
                f'<c r="A{n}"><v>{2015 if local%2==0 else 2016}</v></c>',
                f'<c r="B{n}"><v>{local+1}</v></c>',
                f'<c r="E{n}" t="inlineStr"><is><t>{initiator}</t></is></c>',
                f'<c r="F{n}"><v>1</v></c>',
                f'<c r="G{n}" t="inlineStr"><is><t>{"female" if local%2==0 else "male"}</t></is></c>',
                f'<c r="I{n}" t="inlineStr"><is><t>{recipient}</t></is></c>',
                f'<c r="J{n}" t="inlineStr"><is><t>{"male" if local%2==0 else "female"}</t></is></c>',
                f'<c r="K{n}" t="inlineStr"><is><t>G1D{local%29:02d}</t></is></c>',
                f'<c r="L{n}" t="inlineStr"><is><t>{rank}</t></is></c>',
                f'<c r="M{n}" t="inlineStr"><is><t>{face}</t></is></c>',
                f'<c r="N{n}" t="inlineStr"><is><t>{context}</t></is></c>',
                f'<c r="O{n}" t="inlineStr"><is><t>{gesture}</t></is></c>',
                f'<c r="P{n}" t="inlineStr"><is><t>{response}</t></is></c>',
            ]
        else:
            # Group 2 is structurally present but not decoded by RUN-006.
            cells=[f'<c r="F{n}"><v>2</v></c>']
        rows.append(f'<row r="{n}">{"".join(cells)}</row>')
    xml=(
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<dimension ref="A1:P253"/><sheetData>'+"".join(rows)+'</sheetData></worksheet>'
    )
    buf=BytesIO()
    with ZipFile(buf,"w") as z:
        z.writestr("xl/worksheets/sheet1.xml",xml)
    return buf.getvalue()


def build_synthetic_case(base: Path) -> dict:
    base.mkdir(parents=True,exist_ok=True)
    secret=b"synthetic-persistent-hmac-key-32-bytes!!"
    namespace=_namespace_fingerprint(secret)

    group2=synthetic_group2()
    group2_csv=base/"synthetic_group2.csv"
    group2.to_csv(group2_csv,index=False)
    group2_sha=hashlib.sha256(group2_csv.read_bytes()).hexdigest()
    materialization={
        "dataset_id":"ZERO_SYNTHETIC","evidence_weight":"ZERO_SYNTHETIC",
        "normalized_rows":104,"normalized_csv_sha256":group2_sha,
        "raw_source_identities_in_normalized_csv":False,
        "group1_rows_materialized":False,"pr0005_executed":False,
        "source_sha256":"ZERO_SYNTHETIC","eligible_source_row_set_sha256":"ZERO_SYNTHETIC",
        "identity_namespace_fingerprint":namespace,
    }
    materialization_path=base/"synthetic_group2_materialization.json"
    materialization_path.write_text(json.dumps(materialization,indent=2)+"\n")
    freeze_dir=base/"run005_freeze"
    freeze_manifest=freeze_run005_package(
        group2_csv,materialization_path,freeze_dir,evidence_weight="ZERO_SYNTHETIC"
    )

    raw=synthetic_source_workbook()
    source_sha=hashlib.sha256(raw).hexdigest()
    source_md5=hashlib.md5(raw).hexdigest()
    pins={
        "source_item_id":9192509,"version":1,"doi":"10.6084/m9.figshare.9192509.v1",
        "license_as_reported":{"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"},
        "file":{"id":16741928,"name":"Rawdata_Compositionality.xlsx","bytes":len(raw),
                "md5":source_md5,"sha256":source_sha},
        "sheets":[{"source_header_candidates":HEADERS}],
    }
    crosswalk={
        "version":"source-crosswalk-v0.2",
        "fields":[
            {"field":"Gesture_Class","native_mapping":{"SG":"stretched_arm","BG":"bent_arm"}},
            {"field":"Facial_Expression_Class","native_mapping":{
                "neutral":"neutral","bared":"bared_teeth","hoot":"funneled_lip_hoot",
                "NA":"SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE"}},
            {"field":"Social_Context","native_mapping":{
                "pos":"positive_affiliative_context","neg":"negative_agonistic_context",
                "NA":"SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE"}},
            {"field":"Recipient_Response","native_mapping":{
                "affil":"affiliative","avoid":"non_affiliative",
                "NA":"SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE"}},
            {"field":"Group_ID","native_mapping":{"1":"Group 1","2":"Group 2"}},
            {"field":"Rank_Relationship","normalization":{
                "NA":"SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE"}},
        ],
    }
    eligibility={"rules":{
        "year":{"allowed":["2015","2016"]},
        "gesture":{"allowed":["SG","BG"]},
        "face":{"allowed":["neutral","bared","hoot","NA"]},
        "context":{"allowed":["pos","neg","NA"]},
        "response":{"allowed":["affil","avoid","NA"]},
    }}
    group1_procedure={
        "status":"FROZEN_BEFORE_GROUP1_NONPARTITION_ACCESS",
        "source_sha256":source_sha,
    }
    item={
        "id":9192509,"version":1,"doi":pins["doi"],"license":dict(pins["license_as_reported"]),
        "files":[{"id":16741928,"name":pins["file"]["name"],"size":len(raw),
                  "computed_md5":source_md5,
                  "download_url":"https://ndownloader.figshare.com/files/16741928"}],
    }
    output_dir=base/"run006"
    transfer=run_d0019_group1_transfer(
        item=item,pins=pins,crosswalk=crosswalk,eligibility=eligibility,
        group1_procedure=group1_procedure,run005_freeze_manifest=freeze_manifest,
        run005_freeze_dir=freeze_dir,secret=secret,
        fetch=lambda url,size:raw,output_dir=output_dir,evidence_weight="ZERO_SYNTHETIC"
    )
    return {
        "secret":secret,"raw":raw,"item":item,"pins":pins,"crosswalk":crosswalk,
        "eligibility":eligibility,"group1_procedure":group1_procedure,
        "freeze_manifest":freeze_manifest,"freeze_dir":freeze_dir,
        "output_dir":output_dir,"transfer_manifest":transfer,
    }


def main() -> None:
    ap=argparse.ArgumentParser(description="Verify locked RUN-006 mechanics on synthetic data only")
    ap.add_argument("--out-dir",default="build/pr0005_run006_synthetic")
    args=ap.parse_args()
    case=build_synthetic_case(Path(args.out_dir))
    manifest=case["transfer_manifest"]
    print(json.dumps({
        "status":"PASS_ZERO_SYNTHETIC_RUN006",
        "group1_eligible_rows":manifest["group1_eligible_rows"],
        "models_refit_on_group1":manifest["models_refit_on_group1"],
        "final_disposition":manifest["final_pr0005_disposition"],
        "crg_c_credit":manifest["crg_c_credit"],
        "output":str(case["output_dir"]/"run006_transfer_manifest.json"),
    }))


if __name__=="__main__":
    main()
