import hashlib

from scripts.freeze_d0025_source_integrity import freeze_manifest


def _item():
    raw = {}
    files = []
    for i, fid in enumerate((35234047, 35234059, 35888735, 35888738)):
        data = ("fixture-bytes-" + str(i)).encode()
        raw[fid] = data
        digest = hashlib.md5(data).hexdigest()
        files.append({
            "id": fid, "name": f"test-{i}.xlsx", "size": len(data),
            "download_url": f"https://ndownloader.figshare.com/files/{fid}",
            "computed_md5": digest, "supplied_md5": digest,
        })
    article = {
        "id": 19683768, "version": 1, "doi": "10.6084/m9.figshare.19683768.v1",
        "license": {"name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"},
        "authors": [{"full_name": "Synthetic Test Author"}], "files": files,
    }
    return article, raw


def test_source_integrity_is_checked_without_raw_redistribution():
    article, raw = _item()
    receipt = freeze_manifest(article, lambda url, size: raw[int(url.rsplit("/", 1)[1])])
    assert receipt["state"] == "H1_TRANSIENT_BYTES_VERIFIED"
    assert len(receipt["files"]) == 4
    assert all(len(f["sha256"]) == 64 for f in receipt["files"])
    assert receipt["raw_files_persisted"] is False
    assert receipt["source_rows_inspected"] is False
    assert receipt["rdc005_mapping"] == "NOT_ATTEMPTED"
    assert receipt["research_rights_state"].startswith("HELD_PENDING")
    assert receipt["crg_c_credit"] == "UNMET"


def test_wrong_license_prevents_even_transient_acquisition():
    article, raw = _item()
    article["license"]["name"] = "Unverified"
    def forbidden(url, size):
        raise AssertionError("Must not fetch unverified-licensed bytes")
    receipt = freeze_manifest(article, forbidden)
    assert receipt["state"] == "HELD_RIGHTS"
    assert receipt["source_bytes_sha256_verified"] is False


def test_hash_mismatch_preserves_a_failure_receipt():
    article, raw = _item()
    receipt = freeze_manifest(article, lambda url, size: b"x" * size)
    assert receipt["state"] == "HELD_PARTIAL_SOURCE_INTEGRITY"
    assert not receipt["source_bytes_sha256_verified"]
    assert all(f["state"] == "HELD_SOURCE_DOWNLOAD_OR_CHECKSUM" for f in receipt["files"])


def test_missing_file_in_source_inventory_is_held():
    article, raw = _item()
    article["files"] = article["files"][:3]
    receipt = freeze_manifest(article, lambda url, size: b"")
    assert receipt["state"] == "HELD_FILE_INVENTORY"
