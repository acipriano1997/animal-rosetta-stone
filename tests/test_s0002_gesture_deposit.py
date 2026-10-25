"""Synthetic structural checks only; no original source rows or identities."""
from io import BytesIO
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_s0002_gesture_deposit as audit


def workbook(cell_xml):
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("xl/workbook.xml", f'<workbook xmlns="{audit.S[1:-1]}" xmlns:r="{audit.R[1:-1]}"><sheets><sheet name="Synthetic" r:id="rId1"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels", f'<Relationships xmlns="{audit.P[1:-1]}"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{audit.S[1:-1]}"><sheetData><row r="1">{cell_xml}</row></sheetData></worksheet>')
    return output.getvalue()


def test_ooxml_preserves_sparse_columns_and_literal_whitespace():
    data = workbook('<c r="A1" t="inlineStr"><is><t>  gesture </t></is></c><c r="C1"><v>1</v></c>')
    assert audit.read_workbook(data) == {"Synthetic": [["  gesture ", "", "1"]]}
    with pytest.raises(ValueError, match="FORMULA"):
        audit.read_workbook(workbook('<c r="A1"><f>1+1</f><v>2</v></c>'))


def test_raw_reduced_triples_are_observations_not_duplicate_events():
    headers = ["Goal", "Gesture", "Recipient"]
    result = audit.raw_summary([headers, ["Unknown", " g ", "synthetic-a"],
                               ["Unknown", " g ", "synthetic-a"]], headers)
    assert result["rows"] == 2
    assert result["unknown_outcome_rows"] == 2
    assert result["repeated_reduced_triples_beyond_first"] == 1
    assert result["identity_column_role"] == "Recipient"
    assert result["deduplication_performed"] is False
    with pytest.raises(ValueError, match="MISSING"):
        audit.raw_summary([headers, ["goal", "gesture", ""]], headers)


def test_matrix_zero_policy_never_accepts_unknown_observations():
    headers = [""] + [f"outcome-{i}" for i in range(11)]
    _, values = audit.matrix([headers, ["synthetic-gesture", "1"]])
    assert values == {"synthetic-gesture": [1] + [0] * 10}
    with pytest.raises(ValueError, match="NON_BINARY"):
        audit.matrix([headers, ["synthetic-gesture", "Unknown"]])
    with pytest.raises(ValueError, match="GESTURE_LABELS"):
        audit.matrix([headers, ["same", "1"], ["same", "0"]])


def test_fixed_positive_totals_make_matches_affine_in_shared_positives():
    # Exhaust every pair of four-cell binary matrices, including zero overlap.
    for a in range(16):
        for b in range(16):
            aa = [(a >> i) & 1 for i in range(4)]
            bb = [(b >> i) & 1 for i in range(4)]
            result = audit.overlap({"g": aa}, {"g": bb})
            assert result["total_matches"] == 4 - sum(aa) - sum(bb) + 2 * result["shared_ones"]
            assert result["permutation_test_executed"] is False
    with pytest.raises(ValueError, match="UNALIGNED"):
        audit.overlap({"a": [1]}, {"b": [1]})


def test_published_table_uses_explicit_counts_and_continuation_rows():
    output = BytesIO()
    rows = [["Gesture type", "Goal (ASO)", "# Instances", "Proportion"],
            ["synthetic-g", "outcome-a", "3", "0.75"], ["", "outcome-b", "1", "0.25"]]
    body = "".join("<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{v}</w:t></w:r></w:p></w:tc>" for v in row) + "</w:tr>" for row in rows)
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", f'<w:document xmlns:w="{audit.W[1:-1]}"><w:body><w:tbl>{body}</w:tbl></w:body></w:document>')
    assert audit.table_summary(output.getvalue()) == {
        "gesture_outcome_entries": 2, "gesture_types": 1, "outcome_types": 2,
        "sum_instances": 4, "row_level_exclusion_ledger_present": False}


def test_cli_rejects_unverified_bytes_before_parsing_or_writing(tmp_path):
    source = tmp_path / "unverified.xlsx"
    source.write_bytes(b"unverified source")
    out = tmp_path / "receipt.json"
    assert audit.main(["--workbook", str(source), "--code", str(source),
                       "--table", str(source), "--out", str(out)]) == 2
    assert not out.exists()
    assert source.read_bytes() == b"unverified source"
