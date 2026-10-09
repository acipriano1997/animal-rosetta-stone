from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class GoogleWorkspaceReadError(RuntimeError):
    """Raised when a read-only Google Workspace request cannot be trusted."""


class GoogleWorkspaceRESTReader:
    """Minimal read-only Google Workspace REST client.

    The bearer token is accepted only in memory and is never included in
    returned payloads, exception strings, output bundles, or command arguments.
    """

    def __init__(
        self,
        access_token: str,
        *,
        drive_base: str = "https://www.googleapis.com/drive/v3",
        docs_base: str = "https://docs.googleapis.com/v1",
        sheets_base: str = "https://sheets.googleapis.com/v4",
        timeout: int = 15,
    ) -> None:
        token = access_token.strip()
        if not token:
            raise GoogleWorkspaceReadError("Google Workspace access token is empty")
        self._access_token = token
        self._drive_base = drive_base.rstrip("/")
        self._docs_base = docs_base.rstrip("/")
        self._sheets_base = sheets_base.rstrip("/")
        self._timeout = timeout

    def _get_json(self, url: str) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._access_token}",
                "User-Agent": "animal-rosetta-stone-workbench",
            },
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            raise GoogleWorkspaceReadError(
                f"Google Workspace read failed with HTTP {exc.code}"
            ) from exc
        except URLError as exc:
            raise GoogleWorkspaceReadError(
                f"Google Workspace read failed: {exc.reason}"
            ) from exc
        except Exception as exc:
            raise GoogleWorkspaceReadError(
                f"Google Workspace read failed: {type(exc).__name__}"
            ) from exc

        try:
            obj = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise GoogleWorkspaceReadError(
                "Google Workspace response was not valid JSON"
            ) from exc
        if not isinstance(obj, dict):
            raise GoogleWorkspaceReadError(
                "Google Workspace response must be a JSON object"
            )
        return obj

    def drive_metadata(self, file_id: str) -> dict[str, Any]:
        params = urlencode({"fields": "id,name,mimeType,modifiedTime"})
        return self._get_json(
            f"{self._drive_base}/files/{quote(file_id, safe='')}?{params}"
        )

    def document(self, document_id: str) -> dict[str, Any]:
        params = urlencode({"includeTabsContent": "true"})
        return self._get_json(
            f"{self._docs_base}/documents/{quote(document_id, safe='')}?{params}"
        )

    def drive_head_revision(self, file_id: str) -> str:
        """Find the unique newest Drive revision across all history pages.

        Revision IDs are opaque: neither numeric order nor response order is
        authority. Ambiguous or incomplete history fails closed.
        """
        revisions: dict[str, datetime] = {}
        page_token = ""
        seen_tokens: set[str] = set()
        for _ in range(100):
            params = {"fields": "nextPageToken,revisions(id,modifiedTime)", "pageSize": "1000"}
            if page_token:
                params["pageToken"] = page_token
            obj = self._get_json(
                f"{self._drive_base}/files/{quote(file_id, safe='')}/revisions?{urlencode(params)}"
            )
            rows = obj.get("revisions")
            if not isinstance(rows, list):
                raise GoogleWorkspaceReadError("Drive revision history is malformed")
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
                    raise GoogleWorkspaceReadError("Drive revision identity is invalid")
                try:
                    stamp = datetime.fromisoformat(row["modifiedTime"].replace("Z", "+00:00"))
                    if stamp.tzinfo is None:
                        raise ValueError("timezone missing")
                except (KeyError, AttributeError, TypeError, ValueError) as exc:
                    raise GoogleWorkspaceReadError("Drive revision time is invalid") from exc
                if row["id"] in revisions and revisions[row["id"]] != stamp:
                    raise GoogleWorkspaceReadError("Drive revision history changed during pagination")
                revisions[row["id"]] = stamp
            page_token = obj.get("nextPageToken", "")
            if not isinstance(page_token, str) or page_token in seen_tokens:
                raise GoogleWorkspaceReadError("Drive revision pagination is invalid")
            if not page_token:
                break
            seen_tokens.add(page_token)
        else:
            raise GoogleWorkspaceReadError("Drive revision history exceeds bounded read limit")
        if not revisions:
            raise GoogleWorkspaceReadError("Drive revision history is empty")
        newest = max(revisions.values())
        heads = [rid for rid, stamp in revisions.items() if stamp == newest]
        if len(heads) != 1:
            raise GoogleWorkspaceReadError("Drive head revision is ambiguous")
        return heads[0]

    def spreadsheet_values(self, spreadsheet_id: str, range_name: str) -> list[list[Any]]:
        encoded_range = quote(range_name, safe="")
        params = urlencode({"majorDimension": "ROWS", "valueRenderOption": "FORMATTED_VALUE"})
        obj = self._get_json(
            f"{self._sheets_base}/spreadsheets/{quote(spreadsheet_id, safe='')}/values/{encoded_range}?{params}"
        )
        values = obj.get("values", [])
        if not isinstance(values, list):
            raise GoogleWorkspaceReadError("Google Sheets values payload is malformed")
        return values
