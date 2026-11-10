import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


class PackagingTests(unittest.TestCase):
    def test_lambda_package_excludes_incidental_local_json_and_notes(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / 'scripts/package_tools.py').exists():
            self.skipTest('requires the source distribution')
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp)
            (release / 'scripts').mkdir()
            shutil.copy(root / 'scripts/package_tools.py', release / 'scripts/package_tools.py')
            shutil.copytree(root / 'src/gtm_starter', release / 'src/gtm_starter', ignore=shutil.ignore_patterns('__pycache__'))
            package = release / 'src/gtm_starter'
            (package / 'config.local.json').write_text('{"example":"local only"}')
            (package / 'opportunity.json').write_text('{"example":"local only"}')
            (package / 'notes.md').write_text('local notes')
            subprocess.run([sys.executable, str(release / 'scripts/package_tools.py')], check=True, capture_output=True)
            with ZipFile(release / 'build/tools.zip') as archive:
                names = set(archive.namelist())
                self.assertIn('gtm_starter/cloud.py', names)
                self.assertIn('gtm_starter/catalog.json', names)
                self.assertIn('gtm_starter/skills/call-review/1.0.0/SKILL.md', names)
                for name in ['config.local.json', 'opportunity.json', 'notes.md']:
                    self.assertNotIn('gtm_starter/' + name, names)
