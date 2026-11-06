#!/usr/bin/env python3
"""Verify the archive's project menu and its unchanged edition hash contract."""
from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/"


class Menu(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.rail = False
        self.assets = []
        self.project = None
        self.bundle = None
        self.owned_assets = []

    def handle_starttag(self, tag, attrs):
        row = dict(attrs)
        if tag == 'script' and row.get('data-news-design-bundle'):
            self.bundle = row['data-news-design-bundle']
        asset = row.get('src', row.get('href', ''))
        if tag in {'script', 'link'} and asset.startswith('/news/assets/news/'):
            self.owned_assets.append(asset)
        if tag == "div" and "quant-shared-nav__links" in row.get("class", "").split():
            self.rail = True
        if self.rail and tag == "a":
            self.links.append(row.get("href"))
        if tag == "link" and row.get("href", "").startswith(BASE):
            self.assets.append(row["href"])
        if tag == "script" and row.get("src", "").startswith(BASE):
            self.assets.append(row["src"])
            self.project = row.get("data-quant-project")

    def handle_endtag(self, tag):
        if tag == "div" and self.rail:
            self.rail = False


def verify(root):
    pages = 0
    for path in root.rglob("*.html"):
        text = path.read_text()
        if "quant-shared-nav__links" not in text:
            continue  # Date aliases and the archive landing are redirects.
        menu = Menu()
        menu.feed(text)
        if menu.bundle:
            assert menu.bundle in {'news-2026-11-04.1', 'news-2026-11-04.2', 'news-2026-11-06.1'}, path
            assert not menu.assets, path  # One navigation owner; no competing mutable loader.
            names = {url.split('?')[0].rsplit('/', 1)[-1] for url in menu.owned_assets}
            assert {'boot.js', 'shell.js', 'v04.js', 'reader.js', 'palette.css', 'source-links.js'} <= names, path
            if menu.bundle == 'news-2026-11-04.2':
                assert {'common.css', 'editorial.css', 'polish.js', 'editorial.js', 'unified.js'} <= names, path
            for url in menu.owned_assets:
                relative, _, version = url.removeprefix('/news/').partition('?v=')
                candidate = root / relative
                assert '..' not in Path(relative).parts and candidate.is_file(), path
                assert hashlib.sha256(candidate.read_bytes()).hexdigest()[:12] == version, str(candidate)
        else:
            assert sorted(menu.assets) == [BASE + "nav.css", BASE + "nav.js"], path
            assert menu.project == "news", path
        assert len(menu.links) == len(set(menu.links)) == 8, path
        assert "https://sonchanggi.github.io/factor/" in menu.links, path
        assert not any("best-factor" in href or "momentum-factor-lab" in href or "/SPO/" in href for href in menu.links), path
        pages += 1
    assert pages, "Archive has no project navigation"
    hashes = 0

    def visit(row):
        nonlocal hashes
        if isinstance(row, dict):
            url = row.get("report_url", row.get("url", ""))
            if isinstance(row.get("sha256"), dict) and "html" in row["sha256"]:
                assert url.startswith("/news/") and url.endswith("/index.html"), url
                relative = Path(url.removeprefix("/news/"))
                assert ".." not in relative.parts and not relative.is_absolute(), url
                path = root / relative
                assert set(row["sha256"]) == {"html", "json", "markdown"}, url
                for kind, filename in {"html": "index.html", "json": "briefing.json", "markdown": "briefing.md"}.items():
                    candidate = path.parent / filename
                    assert hashlib.sha256(candidate.read_bytes()).hexdigest() == row["sha256"][kind], str(candidate)
                hashes += 1
            for value in row.values():
                visit(value)
        elif isinstance(row, list):
            for value in row:
                visit(value)

    visit(json.loads((root / "archive.json").read_text()))
    if (root / "previews.json").exists():
        visit(json.loads((root / "previews.json").read_text()))
    assert hashes, "No edition hashes verified"
    print(f"Shared navigation verified: {pages} archive pages, {hashes} edition and preview file groups")


if __name__ == "__main__":
    verify(Path(__file__).resolve().parents[2] / "site")
