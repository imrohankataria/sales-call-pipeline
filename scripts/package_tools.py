"""Create a clean Lambda ZIP from package sources; no environment or local data."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
source = root / 'src'
output = root / 'build' / 'tools.zip'
output.parent.mkdir(exist_ok=True)
package = source / 'gtm_starter'
paths = list(package.rglob('*.py')) + [package / 'catalog.json'] + list(package.glob('skills/*/*/SKILL.md'))
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for path in sorted(paths):
        if path.is_file() and '__pycache__' not in path.parts:
            archive.write(path, path.relative_to(source))
print(output)
