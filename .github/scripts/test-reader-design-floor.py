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
        self.menu.owned_styles = self.menu.owned_assets[:2]
        self.menu.owned_scripts = [dict(src=url, **{'defer': None})
                                   for url, name in zip(self.menu.owned_assets[2:], names[2:] + ['shell.js'])]

    def save(self):
        (self.assets / 'manifest.json').write_text(json.dumps(self.manifest))

    def test_engine_adapter_requires_bound_stylesheet(self):
        self.manifest['adapter_version'] = module.ENGINE_ADAPTER
        self.save()
        with self.assertRaisesRegex(AssertionError, 'Engine adapter stylesheet'):
            module.verify_design_manifest(self.root)
        target = self.assets / 'engine-040.css'
        target.write_text('verified engine tokens')
        self.manifest['files']['engine-040.css'] = hashlib.sha256(target.read_bytes()).hexdigest()
        self.save()
        module.verify_design_manifest(self.root)
        self.menu.bundle = module.ENGINE_ADAPTER
        with self.assertRaisesRegex(AssertionError, 'stylesheet link missing'):
            module.verify_design_page(self.menu, self.manifest, 'new-edition.html')
        url = '/news/assets/news/engine-040.css?v=fixture'
        self.menu.owned_assets.insert(0, url)
        self.menu.owned_styles.insert(0, url)
        module.verify_design_page(self.menu, self.manifest, 'new-edition.html')

    def preferences_fixture(self):
        pref = '/news/assets/news/preferences.js?v=fixture'
        boot = '/news/assets/news/boot.js?v=fixture'
        self.manifest['files']['preferences.js'] = hashlib.sha256(b'preferences').hexdigest()
        self.menu.owned_assets[:0] = [pref, boot]
        self.menu.owned_scripts[:0] = [{'src': pref, '_in_head': True}, {'src': boot, '_in_head': True}]

    def test_preferences_are_blocking_and_first_in_head(self):
        self.preferences_fixture()
        module.verify_design_page(self.menu, self.manifest, 'current.html')
        parser = module.Menu()
        parser.feed('<html><head><script src="/news/assets/news/preferences.js"></script></head><body><script src="/news/assets/news/boot.js"></script></body></html>')
        self.assertTrue(parser.owned_scripts[0]['_in_head'])
        self.assertFalse(parser.owned_scripts[1]['_in_head'])

    def test_preferences_missing_duplicate_late_or_async_are_blocked(self):
        import copy

        self.preferences_fixture()
        valid = copy.deepcopy(self.menu)
        mutations = [
            lambda m: m.owned_assets.pop(0),
            lambda m: m.owned_assets.append(m.owned_assets[0]),
            lambda m: m.owned_assets.insert(1, m.owned_assets.pop(0)),
            lambda m: m.owned_scripts[0].update(async_=None),
            lambda m: m.owned_scripts[0].update(defer=None),
            lambda m: m.owned_scripts[0].update(type='module'),
            lambda m: m.owned_scripts[0].update(_in_head=False),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                menu = copy.deepcopy(valid)
                mutate(menu)
                if 'async_' in menu.owned_scripts[0]:
                    menu.owned_scripts[0]['async'] = menu.owned_scripts[0].pop('async_')
                with self.assertRaises(AssertionError):
                    module.verify_design_page(menu, self.manifest, 'current.html')

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

    def test_late_stylesheet_is_blocked(self):
        self.menu.owned_assets.append(self.menu.owned_assets.pop(0))
        with self.assertRaisesRegex(AssertionError, 'stylesheet loaded after'):
            module.verify_design_page(self.menu, self.manifest, 'new-edition.html')

    def test_async_engine_is_blocked(self):
        self.menu.owned_scripts[1]['async'] = None
        with self.assertRaisesRegex(AssertionError, 'handler loaded before engine'):
            module.verify_design_page(self.menu, self.manifest, 'new-edition.html')

    def test_unused_legacy_output_is_blocked_even_with_a_valid_hash(self):
        page = self.root / 'index.html'
        page.write_text(''.join('<script src="/news/assets/news/' + name + '"></script>'
                                for name in self.manifest['files']))
        module.verify_asset_inventory(self.root, self.manifest)
        legacy = 'extensions/0.6.0/unused.js'
        self.manifest['files'][legacy] = hashlib.sha256(b'old').hexdigest()
        with self.assertRaisesRegex(AssertionError, 'Unused reader assets'):
            module.verify_asset_inventory(self.root, self.manifest)
        preview = self.root / 'previews/approved/index.html'
        preview.parent.mkdir(parents=True)
        preview.write_text('<script src="/news/assets/news/' + legacy + '"></script>')
        module.verify_asset_inventory(self.root, self.manifest)


if __name__ == '__main__':
    unittest.main()
