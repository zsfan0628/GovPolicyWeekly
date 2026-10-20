"""Copy an allowlist into a fresh publishing folder without local Git history."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / '.github-publish' / 'GovPolicyWeekly'
FILES = [
    '.gitignore', 'README.md', 'README.zh-CN.md', 'WINDOWS_BUILD.md', 'CHANGELOG.md', 'RELEASE_NOTES.md',
    'app.py', 'qt_app.py', 'desktop_app.py', 'ui_preview.py', 'main.py', 'GovPolicyWeekly.spec', 'GovPolicyWeekly.iss',
    'build_windows.bat', 'build_windows.ps1', 'requirements.txt', 'requirements-windows-build.txt',
]
FOLDERS = ['.github', 'config', 'gov_report', 'input', 'scripts', 'tests', 'docs']
PRIVATE_PATTERNS = {
    'API token': re.compile(r'(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})'),
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'home path': re.compile(r'(?:/[U]sers/[^/\s"\x27<>]+/|/[h]ome/[^/\s"\x27<>]+/|[A-Za-z]:[\\/][U]sers[\\/][^\\/\s"\x27<>]+[\\/])', re.I),
    'authenticated URL': re.compile(r'https?://[^\s/@]+:[^\s/@]+@', re.I),
}


def protected_local_values(root: Path) -> set[str]:
    values = {str(root.resolve()), str(Path.home()) + '/'}
    settings = [root / 'user_settings.json']
    if os.name == 'nt':
        settings.append(Path(os.getenv('APPDATA', str(Path.home()))) / 'GovPolicyWeekly' / 'user_settings.json')
    elif sys.platform == 'darwin':
        settings.append(Path.home() / 'Library' / 'Application Support' / 'GovPolicyWeekly' / 'user_settings.json')
    else:
        settings.append(Path(os.getenv('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'GovPolicyWeekly' / 'user_settings.json')
    for path in settings:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            for key, value in data.items():
                if not isinstance(value, str) or len(value) < 8:
                    continue
                if re.search(r'api.?key|secret|token|password', key, re.I):
                    values.add(value)
                elif key == 'openai_base_url' and value.rstrip('/') != 'https://api.openai.com/v1':
                    values.add(value)
    return values


def check_payload(relative: Path, payload: bytes, protected: set[str]) -> None:
    forbidden = {'.git', '__pycache__', '.DS_Store', '.venv', 'release-check', 'audit-results'}
    if any(part in forbidden or part.startswith(('user_settings', '.env')) for part in relative.parts):
        raise RuntimeError(f'Private file excluded: {relative}')
    content = payload.decode('utf-8', errors='ignore')
    variants = (content, content.replace('\\\\', '\\'))
    if any(value and any(value in text for text in variants) for value in protected):
        raise RuntimeError(f'Known local credential or path found in {relative}; publishing stopped')
    for label, pattern in PRIVATE_PATTERNS.items():
        if any(pattern.search(text) for text in variants):
            raise RuntimeError(f'{label} found in {relative}; publishing stopped')


def collect_paths(root: Path) -> list[Path]:
    paths = [root / name for name in FILES]
    for folder in FOLDERS:
        paths.extend(path for path in (root / folder).rglob('*') if path.is_file()
                     and '__pycache__' not in path.parts and path.suffix in {'.py', '.ps1', '.yml', '.yaml', '.txt', '.md'})
    paths.extend(path for path in (root / 'ui' / 'preview').rglob('*') if path.is_file()
                 and (path.suffix in {'.qml', '.qsb', '.frag', '.svg', '.jpg', '.md'} or path.name == 'LICENSE'))
    return sorted(set(paths))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upload-dir', type=Path, help='Also create a new browser-upload folder containing only checked files')
    args = parser.parse_args()
    if args.upload_dir and args.upload_dir.exists():
        parser.error('Upload destination must not exist; no existing files were changed')
    paths = collect_paths(ROOT)
    protected = protected_local_values(ROOT)
    for path in paths:
        check_payload(path.relative_to(ROOT), path.read_bytes(), protected)
    DEST.mkdir(parents=True, exist_ok=True)
    if args.upload_dir:
        args.upload_dir.mkdir(parents=True)
    for path in paths:
        destinations = [DEST] + ([args.upload_dir] if args.upload_dir else [])
        for destination in destinations:
            target = destination / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    with ZipFile(ROOT / 'GovPolicyWeekly_windows_source.zip', 'w', ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT))
    print(f'Prepared {len(paths)} files in {DEST}')
    print('Privacy checks passed: no known local credentials, personal home paths or common token formats found')
    if args.upload_dir:
        print(f'Checked browser-upload snapshot: {args.upload_dir}')
    print('Updated GovPolicyWeekly_windows_source.zip')


if __name__ == '__main__':
    main()
