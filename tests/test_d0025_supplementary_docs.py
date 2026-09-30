from io import BytesIO
import hashlib
from zipfile import ZipFile

from scripts.review_d0025_supplementary_docs import document_cues, review


def _fixture_docx():
    xml = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
       <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Codebook notes</w:t></w:r></w:p>
       <w:p><w:r><w:t>Recipient response was source coded for the behavioral endpoint.</w:t></w:r></w:p>
       <w:tbl><w:tr><w:tc><w:p><w:r><w:t>private table datum</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
    </w:body></w:document>"""
    data = BytesIO()
    with ZipFile(data, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return data.getvalue()


def _source(raw):
    docs = []
    for fid in (35888735, 35888738):
        docs.append({
            "id": fid, "name": f"Supplementary {fid}.docx",
            "size": len(raw), "computed_md5": hashlib.md5(raw).hexdigest(),
            "download_url": f"https://ndownloader.figshare.com/files/{fid}",
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    pins = {
        "item_id": 19683768, "version": 1, "doi": "10.6084/m9.figshare.19683768.v1",
        "files": [{"id": d["id"], "name": d["name"], "size": d["size"],
                   "md5": d["computed_md5"], "sha256": d["sha256"]} for d in docs],
    }
    item = {"id": 19683768, "version": 1, "doi": pins["doi"],
            "license": {"name": "CC BY 4.0"}, "files": docs}
    return item, pins


def test_codebook_cues_are_bounded_without_table_data():
    result = document_cues(_fixture_docx())
    assert result["body_paragraph_count"] == 2
    assert result["body_table_count"] == 1
    assert result["heading_excerpts"][0]["title_excerpt"] == "Codebook notes"
    assert any("Recipient response" in cue["topic_cue_excerpt"] for cue in result["bounded_topic_cues"])
    assert "private table datum" not in str(result)
    assert result["full_document_not_redistributed"]


def test_pinned_documents_stay_unapproved():
    raw = _fixture_docx()
    item, pins = _source(raw)
    result = review(item, pins, lambda url, length: raw)
    assert result["state"] == "H2_DOCUMENT_CUES_RECORDED_CODEBOOK_NOT_APPROVED"
    assert result["document_codebook_approved"] is False
    assert result["source_join_keys_verified"] is False
    assert result["pr0006_executed"] is False
    assert result["crg_c_credit"] == "UNMET"


def test_source_hash_failure_holds_document():
    raw = _fixture_docx()
    item, pins = _source(raw)
    pins["files"][0]["sha256"] = "0" * 64
    result = review(item, pins, lambda url, length: raw)
    assert result["state"] == "HELD_DOCUMENT_SOURCE"


def test_unverified_license_blocks_document_fetch():
    raw = _fixture_docx()
    item, pins = _source(raw)
    item["license"]["name"] = "Unverified"
    result = review(item, pins, lambda url, length: (_ for _ in ()).throw(AssertionError("Forbidden fetch")))
    assert result["state"] == "HELD_RIGHTS"
