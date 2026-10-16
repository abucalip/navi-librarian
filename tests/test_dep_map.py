import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('dep_map', ROOT / 'scripts' / 'dep_map.py')
assert SPEC and SPEC.loader
dep_map = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dep_map)

class DependencyMapTests(unittest.TestCase):
    def test_imports_of_records_absolute_and_relative_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'sample.py'
            source.write_text('import json\\nfrom app.api import settings\\nfrom . import sibling\\n', encoding='utf-8')
            imports = dep_map.imports_of(source)
        self.assertEqual([item['module'] for item in imports], ['json', 'app.api', ''])
        self.assertEqual([item['kind'] for item in imports], ['import', 'from', 'from'])
        self.assertEqual(imports[2]['level'], 1)

    def test_resolves_repository_local_imports_and_from_children(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'app' / 'api').mkdir(parents=True)
            source = root / 'app' / 'main.py'
            source.write_text('from app.api import settings\\n', encoding='utf-8')
            modules = {
                'app.main': source,
                'app.api': root / 'app' / 'api' / '__init__.py',
                'app.api.settings': root / 'app' / 'api' / 'settings.py',
            }
            dep_map.ROOT = root
            imports = dep_map.imports_of(source)
            resolved = dep_map.resolve_local_imports(source, imports, modules)
        self.assertEqual(resolved, ['app.api', 'app.api.settings'])

if __name__ == '__main__':
    unittest.main()
