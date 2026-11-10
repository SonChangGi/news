#!/usr/bin/env python3
"""Verify the archive's project menu and its unchanged edition hash contract."""
from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ENGINE_ADAPTER = 'news-engine-0.4.0-production'

BASE = "https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/"
MINIMUM_DESIGN = (0, 7, 0)
REQUIRED_EXTENSION_ASSETS = {'number.js', 'spacing.css', 'table-edges.js',
                             'news-numbers.js', 'quant-range.js', 'quant-range.css'}


def verify_design_manifest(root):
    """Keep the published design floor outside the replaceable runtime/export."""
    target = root / 'assets/news'
    manifest = json.loads((target / 'manifest.json').read_text())
    version = manifest.get('extension_version', '')
    assert re.fullmatch(r'\d+\.\d+\.\d+', version), 'Invalid reader design version'
    assert tuple(map(int, version.split('.'))) >= MINIMUM_DESIGN, 'Reader design downgrade blocked'
    assert manifest.get('adapter_version'), 'Missing reader adapter version'
    prefix = f'extensions/{version}/'
    required = {prefix + name for name in REQUIRED_EXTENSION_ASSETS}
    files = manifest.get('files', {})
    extension_files = manifest.get('extension_files', {})
    assert required <= extension_files.keys(), 'Required reader design assets missing'
    for name, digest in extension_files.items():
        assert name.startswith(prefix) and '..' not in Path(name).parts, 'Invalid extension path'
        candidate = target / name
        assert files.get(name) == digest and candidate.is_file(), 'Unbound reader design asset'
        assert hashlib.sha256(candidate.read_bytes()).hexdigest() == digest, 'Reader design asset hash mismatch'
    if manifest['adapter_version'] == ENGINE_ADAPTER:
        candidate = target / 'engine-040.css'
        assert candidate.is_file() and files.get('engine-040.css') == hashlib.sha256(candidate.read_bytes()).hexdigest(), 'Engine adapter stylesheet missing or changed'
    return manifest


def verify_design_page(menu, manifest, path):
    assert menu.bundle == manifest['adapter_version'], f'Reader adapter downgrade or mismatch: {path}'
    assets = [url.split('?')[0].removeprefix('/news/assets/news/') for url in menu.owned_assets]
    if menu.bundle == ENGINE_ADAPTER:
        assert 'engine-040.css' in assets, f'Engine adapter stylesheet link missing: {path}'
    prefix = f"extensions/{manifest['extension_version']}/"
    assert {prefix + name for name in REQUIRED_EXTENSION_ASSETS} <= set(assets), f'Reader design links missing: {path}'
    assert assets.index(prefix + 'number.js') < assets.index(prefix + 'quant-range.js') < assets.index('shell.js'), f'Reader startup order changed: {path}'
    number_index = assets.index(prefix + 'number.js')
    for url in menu.owned_styles:
        name = url.split('?')[0].removeprefix('/news/assets/news/')
        assert assets.index(name) < number_index, f'Reader stylesheet loaded after startup: {path}'
    for row in menu.owned_scripts:
        name = row['src'].split('?')[0].removeprefix('/news/assets/news/')
        if name in {'boot.js', prefix + 'number.js', prefix + 'quant-range.js'}:
            assert not {'async', 'defer'} & row.keys() and row.get('type', '') != 'module', f'Reader startup must block: {path}'
        else:
            assert 'defer' in row and 'async' not in row and assets.index(name) > assets.index(prefix + 'quant-range.js'), f'Reader handler loaded before engine: {path}'


class Menu(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.rail = False
        self.assets = []
        self.project = None
        self.bundle = None
        self.owned_assets = []
        self.owned_styles = []
        self.owned_scripts = []

    def handle_starttag(self, tag, attrs):
        row = dict(attrs)
        if tag == 'script' and row.get('data-news-design-bundle'):
            self.bundle = row['data-news-design-bundle']
        asset = row.get('src', row.get('href', ''))
        if tag in {'script', 'link'} and asset.startswith('/news/assets/news/'):
            self.owned_assets.append(asset)
            if tag == 'script':
                self.owned_scripts.append(row)
            elif row.get('rel') == 'stylesheet':
                self.owned_styles.append(asset)
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


def verify_asset_inventory(root, manifest):
    referenced, preview_versions = set(), set()
    for page in root.rglob('*.html'):
        menu = Menu()
        menu.feed(page.read_text())
        names = {url.split('?')[0].removeprefix('/news/assets/news/') for url in menu.owned_assets}
        referenced.update(names)
        if page.relative_to(root).parts[0] == 'previews':
            preview_versions.update('/'.join(name.split('/')[:2]) + '/' for name in names
                                    if name.startswith('extensions/'))
    files = set(manifest['files'])
    retained = {name for name in files if any(name.startswith(prefix) for prefix in preview_versions)}
    unused = files - referenced - retained - {'PretendardVariable.woff2'}
    assert not unused, f'Unused reader assets must not be republished: {sorted(unused)}'


def verify(root):
    manifest = verify_design_manifest(root)
    verify_asset_inventory(root, manifest)
    pages = 0
    for path in root.rglob("*.html"):
        text = path.read_text()
        if "quant-shared-nav__links" not in text:
            continue  # Date aliases and the archive landing are redirects.
        menu = Menu()
        menu.feed(text)
        # Approved previews are immutable historical artifacts, not the next edition.
        preview = path.relative_to(root).parts[0] == 'previews'
        if menu.bundle:
            if not preview:
                verify_design_page(menu, manifest, path)
            assert menu.bundle in {'news-2026-11-04.1', 'news-2026-11-04.2', 'news-2026-11-06.1', ENGINE_ADAPTER}, path
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
            assert preview or 'data-reader-layout' not in text, f'Reader bootstrap missing: {path}'
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
