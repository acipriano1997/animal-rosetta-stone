"""English shell messages only; never imported by scientific stores/adapters."""
from __future__ import annotations

from html import escape
from importlib.resources import files
import json
import re


def english_messages() -> dict[str, str]:
    return json.loads(files("ars_workbench").joinpath("static/locales/en.json").read_text(encoding="utf-8"))


def render_shell(template: str) -> str:
    messages = english_messages()
    # Embed English for immediate, network-independent fallback in the browser.
    seed = json.dumps(messages, ensure_ascii=True).replace("<", "\\u003c")
    return re.sub(
        r"\{\{([\w.]+)\}\}",
        lambda match: seed if match[1] == "messages" else escape(messages[match[1]], quote=True),
        template,
    )


def error_page(status: int) -> str:
    messages = english_messages()
    return (
        '<!doctype html><html lang="en" dir="ltr"><meta charset="utf-8">'
        f'<title>{escape(messages["http.title"])}</title><h1>{escape(messages["http.title"])}</h1>'
        f'<p>{escape(messages["http.error"].format(status=status))}</p>'
        f'<a href="/">{escape(messages["http.return"])}</a></html>'
    )
