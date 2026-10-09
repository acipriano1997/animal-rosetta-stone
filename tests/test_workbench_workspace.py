from urllib.parse import parse_qs, urlparse

import pytest

from ars_workbench.workspace import GoogleWorkspaceReadError, GoogleWorkspaceRESTReader


def _reader(pages):
    reader = GoogleWorkspaceRESTReader("synthetic-runtime-token-not-a-credential")
    urls = []
    def get_json(url):
        urls.append(url)
        return pages[len(urls) - 1]
    reader._get_json = get_json
    return reader, urls


def test_drive_head_reads_all_pages_and_uses_time_not_id_or_order():
    reader, urls = _reader([
        {"revisions": [{"id": "999", "modifiedTime": "2026-01-01T00:00:00Z"}], "nextPageToken": "next/page"},
        {"revisions": [
            {"id": "opaque-head", "modifiedTime": "2026-02-01T00:00:00Z"},
            {"id": "1000", "modifiedTime": "2025-01-01T00:00:00Z"},
        ]},
    ])
    assert reader.drive_head_revision("file/id") == "opaque-head"
    assert len(urls) == 2
    assert "/files/file%2Fid/revisions" in urls[0]
    assert parse_qs(urlparse(urls[1]).query)["pageToken"] == ["next/page"]
    assert all("synthetic-runtime-token" not in url for url in urls)


@pytest.mark.parametrize("payload", [
    {}, {"revisions": {}}, {"revisions": []},
    {"revisions": [{"id": "", "modifiedTime": "2026-01-01T00:00:00Z"}]},
    {"revisions": [{"id": "1", "modifiedTime": "invalid"}]},
    {"revisions": [{"id": "1", "modifiedTime": "2026-01-01T00:00:00"}]},
    {"revisions": [
        {"id": "1", "modifiedTime": "2026-01-01T00:00:00Z"},
        {"id": "2", "modifiedTime": "2026-01-01T00:00:00Z"},
    ]},
])
def test_invalid_or_ambiguous_revision_history_fails_closed(payload):
    reader, _ = _reader([payload])
    with pytest.raises(GoogleWorkspaceReadError):
        reader.drive_head_revision("doc")


def test_revision_history_changes_during_pagination_fail_closed():
    reader, _ = _reader([
        {"revisions": [{"id": "1", "modifiedTime": "2026-01-01T00:00:00Z"}], "nextPageToken": "next"},
        {"revisions": [{"id": "1", "modifiedTime": "2026-02-01T00:00:00Z"}]},
    ])
    with pytest.raises(GoogleWorkspaceReadError, match="changed during pagination"):
        reader.drive_head_revision("doc")


def test_revision_pagination_cycle_fails_closed():
    page = {"revisions": [], "nextPageToken": "repeat"}
    reader, _ = _reader([page, page])
    with pytest.raises(GoogleWorkspaceReadError, match="pagination"):
        reader.drive_head_revision("doc")
