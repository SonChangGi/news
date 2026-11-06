"""Regression checks for a runtime exporting an older or incomplete UI bundle."""
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('navigation', Path(__file__).with_name('verify-shared-navigation.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReaderDesignFloorTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.assets = self.root / 'assets/news'
        self.prefix = 'extensions/0.7.0/'
        files = {}
        for name in module.REQUIRED_EXTENSION_ASSETS:
            target = self.assets / self.prefix / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('verified ' + name)
            files[self.prefix + name] = hashlib.sha256(target.read_bytes()).hexdigest()
        self.manifest = {'extension_version': '0.7.0', 'adapter_version': 'news-2026-11-06.1',
                         'extension_files': files, 'files': dict(files)}
        self.save()
        names = ['spacing.css', 'quant-range.css', 'number.js', 'quant-range.js', 'table-edges.js', 'news-numbers.js']
        self.menu = SimpleNamespace(bundle=self.manifest['adapter_version'], owned_assets=[
            '/news/assets/news/' + self.prefix + name + '?v=fixture' for name in names
        ] + ['/news/assets/news/shell.js?v=fixture'])

    def save(self):
        (self.assets / 'manifest.json').write_text(json.dumps(self.manifest))

    def test_current_bundle_and_startup_pass(self):
        manifest = module.verify_design_manifest(self.root)
        module.verify_design_page(self.menu, manifest, 'new-edition.html')

    def test_old_runtime_export_is_blocked(self):
        self.manifest['extension_version'] = '0.6.0'
        self.save()
        with self.assertRaisesRegex(AssertionError, 'downgrade'):
            module.verify_design_manifest(self.root)

    def test_old_bootstrap_cannot_hide_behind_new_manifest(self):
        self.menu.bundle = 'news-2026-11-04.2'
        with self.assertRaisesRegex(AssertionError, 'adapter downgrade'):
            module.verify_design_page(self.menu, self.manifest, 'old-edition.html')

    def test_missing_number_loader_is_blocked(self):
        self.menu.owned_assets = [p for p in self.menu.owned_assets if '/number.js?' not in p]
        with self.assertRaisesRegex(AssertionError, 'links missing'):
            module.verify_design_page(self.menu, self.manifest, 'new-edition.html')

    def test_mutated_asset_is_blocked(self):
        (self.assets / self.prefix / 'number.js').write_text('stale formatter')
        with self.assertRaisesRegex(AssertionError, 'hash mismatch'):
            module.verify_design_manifest(self.root)

    def test_missing_spacing_manifest_entry_is_blocked(self):
        del self.manifest['extension_files'][self.prefix + 'spacing.css']
        self.save()
        with self.assertRaisesRegex(AssertionError, 'assets missing'):
            module.verify_design_manifest(self.root)

    def test_number_loader_after_native_shell_is_blocked(self):
        self.menu.owned_assets.insert(0, self.menu.owned_assets.pop())
        with self.assertRaisesRegex(AssertionError, 'startup order'):
            module.verify_design_page(self.menu, self.manifest, 'new-edition.html')


if __name__ == '__main__':
    unittest.main()
