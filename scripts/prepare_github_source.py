"""Copy an allowlist into a fresh publishing folder without local Git history."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / '.github-publish' / 'GovPolicyWeekly'
FILES = [
    '.gitignore', 'README.md', 'WINDOWS_BUILD.md', 'CHANGELOG.md', 'RELEASE_NOTES.md',
    'app.py', 'qt_app.py', 'main.py', 'GovPolicyWeekly.spec', 'GovPolicyWeekly.iss',
    'build_windows.bat', 'build_windows.ps1', 'requirements.txt', 'requirements-windows-build.txt',
]
FOLDERS = ['.github', 'config', 'gov_report', 'input', 'scripts']


def main() -> None:
    paths = [ROOT / name for name in FILES]
    for folder in FOLDERS:
        paths.extend(path for path in (ROOT / folder).rglob('*') if path.is_file()
                     and '__pycache__' not in path.parts and path.suffix in {'.py', '.ps1', '.yml', '.yaml', '.txt', '.md'})
    for path in paths:
        content = path.read_text(encoding='utf-8')
        if re.search(r'sk-[A-Za-z0-9_-]{20,}', content):
            raise RuntimeError(f'Credential found in {path.relative_to(ROOT)}; publishing stopped')
    DEST.mkdir(parents=True, exist_ok=True)
    for path in paths:
        target = DEST / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    with ZipFile(ROOT / 'GovPolicyWeekly_windows_source.zip', 'w', ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT))
    print(f'Prepared {len(paths)} files in {DEST}')
    print('Updated GovPolicyWeekly_windows_source.zip')


if __name__ == '__main__':
    main()
