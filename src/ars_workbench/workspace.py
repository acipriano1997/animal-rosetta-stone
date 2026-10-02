from __future__ import annotations

import json
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
