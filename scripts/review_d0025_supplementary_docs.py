"""Inspect D0025 supplementary document structure and bounded codebook cues only."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import ZipFile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KEYWORDS = re.compile(
    r"\b(dataset|codebook|variable|signaller|recipient|response|approach|avoidance|"
    r"event|identity|dyad|social bond|intention|bimodal|gesture|vocal)\b",
    re.IGNORECASE,
)


def document_cues(raw: bytes) -> dict:
    with ZipFile(BytesIO(raw)) as doc:
        if sum(part.file_size for part in doc.infolist()) > 8_000_000:
            raise ValueError("Document uncompressed content exceeds safe bound")
        body = ET.fromstring(doc.read("word/document.xml")).find(W + "body")
        if body is None:
            raise ValueError("DOCX has no Word body")
        paragraphs = body.findall(W + "p")  # exclude table data and nested paragraphs
        headings = []
        matching = []
        for index, paragraph in enumerate(paragraphs, 1):
            value = "".join(t.text or "" for t in paragraph.iter(W + "t")).strip()
            if not value:
                continue
            props = paragraph.find(W + "pPr")
            style = props.find(W + "pStyle") if props is not None else None
            named_style = style.get(W + "val") if style is not None else ""
            if named_style.lower().startswith(("heading", "title", "subtitle")) and len(headings) < 20:
                headings.append({"paragraph_index": index, "title_excerpt": value[:120]})
            if KEYWORDS.search(value) and len(matching) < 18:
                matching.append({
                    "paragraph_index": index,
                    "topic_cue_excerpt": value[:160],
                    "truncated": len(value) > 160,
                })
        return {
            "body_paragraph_count": len(paragraphs),
            "body_table_count": len(body.findall(W + "tbl")),
            "heading_excerpts": headings,
            "bounded_topic_cues": matching,
            "full_document_not_redistributed": True,
            "body_table_data_not_read": True,
        }


def review(item: dict, pins: dict, fetch_bytes) -> dict:
    output = {
        "dataset_id": "D0025",
        "scope": "H2_SUPPLEMENTARY_DOCUMENT_CUES_ONLY",
        "state": "HELD_DOCUMENT_PROVENANCE",
        "files_stored": False, "event_rows_examined": False,
        "document_codebook_approved": False,
        "source_join_keys_verified": False,
        "timing_mapping_adjudicated": False,
        "pr0006_executed": False, "crg_c_credit": "UNMET",
        "documents": [],
    }
    if (item.get("id") != pins.get("item_id")
        or item.get("version") != pins.get("version")
        or item.get("doi") != pins.get("doi")):
        return output
    lic = item.get("license") or {}
    if not isinstance(lic, dict) or lic.get("name") != "CC BY 4.0":
        output["state"] = "HELD_RIGHTS"
        return output
    files = {x.get("id"): x for x in item.get("files", []) if isinstance(x, dict)}
    complete = True
    for pinned in pins["files"]:
        if not pinned["name"].lower().endswith(".docx"):
            continue
        fid = pinned["id"]
        current = files.get(fid, {})
        info = {"file_id": fid, "filename": pinned["name"], "sha256": pinned["sha256"]}
        output["documents"].append(info)
        try:
            if (current.get("name") != pinned["name"]
                or current.get("size") != pinned["size"]
                or current.get("computed_md5") != pinned["md5"]):
                raise ValueError("Source metadata differs from H1 pin")
            url = current.get("download_url")
            parsed = urlparse(str(url))
            if (parsed.scheme != "https" or parsed.hostname != "ndownloader.figshare.com"
                or parsed.path != f"/files/{fid}"):
                raise ValueError("Unexpected source download address")
            raw = fetch_bytes(url, pinned["size"])
            if len(raw) != pinned["size"] or hashlib.sha256(raw).hexdigest() != pinned["sha256"]:
                raise ValueError("DOCX bytes differ from H1 pin")
            info["structure"] = document_cues(raw)
            info["state"] = "DOCUMENT_CUES_RECORDED"
        except (OSError, ValueError, TypeError, KeyError, ET.ParseError) as error:
            complete = False
            info["state"] = "HELD_DOCUMENT_SOURCE"
            info["error_type"] = type(error).__name__
            info["error_summary"] = str(error)[:150]
    output["state"] = ("H2_DOCUMENT_CUES_RECORDED_CODEBOOK_NOT_APPROVED"
                       if complete and len(output["documents"]) == 2 else "HELD_DOCUMENT_SOURCE")
    return output


def main():
    parser = argparse.ArgumentParser(description="Inspect pinned D0025 DOCX codebook cues")
    parser.add_argument("--pins", default="contracts/d0025_v1_verified_source_snapshot.json")
    parser.add_argument("--out", default="build/d0025_supplementary_doc_cues.json")
    args = parser.parse_args()
    from probe_d0025_metadata import public_json
    from freeze_d0025_source_integrity import download_bounded
    pins = json.loads(Path(args.pins).read_text())
    try:
        result = review(public_json("/articles/19683768"), pins, download_bounded)
    except (OSError, ValueError, TypeError) as error:
        result = {
            "dataset_id": "D0025", "scope": "H2_SUPPLEMENTARY_DOCUMENT_CUES_ONLY",
            "state": "HELD_DOCUMENT_SOURCE",
            "error_type": type(error).__name__, "error_summary": str(error)[:150],
            "files_stored": False, "event_rows_examined": False,
            "document_codebook_approved": False, "pr0006_executed": False,
            "crg_c_credit": "UNMET",
        }
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"state": result["state"], "documents": len(result.get("documents", [])),
                      "codebook_approved": False, "output": str(target)}))


if __name__ == "__main__":
    main()
