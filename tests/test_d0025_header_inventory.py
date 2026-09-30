import hashlib
import io
import json
from zipfile import ZipFile

from scripts.inspect_d0025_headers import inspect_xlsx_headers, inspect_item_headers


def _mini_xlsx():
    archive = io.BytesIO()
    workbook = '''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheets><sheet name="Observations" sheetId="1" r:id="rId1"/></sheets></workbook>'''
    rels = '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Target="worksheets/sheet1.xml"
      Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>'''
    strings = '''<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
      <si><t>Subject</t></si><si><t>Receiver_Outcome</t></si></sst>'''
    sheet = '''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
      <dimension ref="A1:B2"/><sheetData>
      <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
      <row r="2"><c r="A2" t="inlineStr"><is><t>private-row-data</t></is></c>
                 <c r="B2" t="inlineStr"><is><t>private-response-value</t></is></c></row>
      </sheetData></worksheet>'''
    with ZipFile(archive, "w") as z:
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/sharedStrings.xml", strings)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return archive.getvalue()


def _candidate_pair(raw):
    files = []
    for fid in (35234047, 35234059):
        files.append({
            "id": fid, "name": "synthetic-" + str(fid) + ".xlsx",
            "size": len(raw), "computed_md5": hashlib.md5(raw).hexdigest(),
            "download_url": "https://ndownloader.figshare.com/files/" + str(fid),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    pins = {
        "item_id": 19683768, "version": 1,
        "doi": "10.6084/m9.figshare.19683768.v1",
        "license_as_reported": {"name": "CC BY 4.0"},
        "files": [{"id": f["id"], "name": f["name"], "size": f["size"],
                   "md5": f["computed_md5"], "sha256": f["sha256"]} for f in files],
    }
    item = {"id": pins["item_id"], "version": 1, "doi": pins["doi"],
            "license": {"name": "CC BY 4.0"}, "files": files}
    return item, pins


def test_extracts_only_first_row_candidates():
    sheets = inspect_xlsx_headers(_mini_xlsx())
    assert len(sheets) == 1
    assert sheets[0]["sheet_name"] == "Observations"
    assert sheets[0]["dimension_as_declared"] == "A1:B2"
    assert [c["header_candidate"] for c in sheets[0]["header_candidate_cells"]] == ["Subject", "Receiver_Outcome"]
    assert "private-row-data" not in json.dumps(sheets)
    assert "private-response-value" not in json.dumps(sheets)


def test_h2_stays_partial_even_after_two_header_checks():
    raw = _mini_xlsx()
    item, pins = _candidate_pair(raw)
    result = inspect_item_headers(item, pins, lambda url, size: raw)
    assert result["state"] == "H2_PARTIAL_HEADERS_ONLY_CODEBOOK_HELD"
    assert len(result["workbooks"]) == 2
    assert result["data_rows_or_outcome_distributions_examined"] is False
    assert result["codebook_documents_reviewed"] is False
    assert result["pr0006_executed"] is False


def test_wrong_pinned_hash_fails_closed():
    raw = _mini_xlsx()
    item, pins = _candidate_pair(raw)
    pins["files"][0]["sha256"] = "0" * 64
    result = inspect_item_headers(item, pins, lambda url, size: raw)
    assert result["state"] == "HELD_SCHEMA_SOURCE"
    assert any(w["state"] == "HELD_SCHEMA_SOURCE" for w in result["workbooks"])


def test_invalid_zip_is_not_accepted_as_a_workbook():
    raw = b"invalid-xlsx-file"
    item, pins = _candidate_pair(raw)
    result = inspect_item_headers(item, pins, lambda url, size: raw)
    assert result["state"] == "HELD_SCHEMA_SOURCE"
    assert all(w["state"] == "HELD_SCHEMA_SOURCE" for w in result["workbooks"])
