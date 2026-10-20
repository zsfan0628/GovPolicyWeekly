from pathlib import Path
import unittest

from scripts.prepare_github_source import check_payload, collect_paths, ROOT


class PublishSafetyTests(unittest.TestCase):
    def test_known_credentials_are_blocked_without_echoing_them(self):
        secret = 'private-fixture-' + 'x' * 24
        with self.assertRaises(RuntimeError) as failure:
            check_payload(Path('settings.txt'), secret.encode(), {secret})
        self.assertNotIn(secret, str(failure.exception))

    def test_home_paths_and_tokens_are_blocked_in_text_and_binary(self):
        values = ['/' + 'Users' + '/example/project/file.py',
                  'C:' + '\\' + 'Users' + '\\' + 'example' + '\\' + 'project',
                  'sk-' + 'x' * 32, 'github_pat_' + 'x' * 32]
        for value in values:
            with self.subTest(kind=value[:3]):
                with self.assertRaises(RuntimeError):
                    check_payload(Path('asset.bin'), b'\xff\x00' + value.encode(), set())
        with self.assertRaises(RuntimeError):
            check_payload(Path('file.txt'), values[1].replace('\\', '\\\\').encode(), set())

    def test_private_file_names_are_blocked(self):
        for path in ('user_settings.json', 'user_settings.backup.json', '.env', '.git/config', '__pycache__/file.pyc'):
            with self.assertRaises(RuntimeError):
                check_payload(Path(path), b'{}', set())

    def test_allowlist_contains_both_readmes_and_no_private_artifacts(self):
        paths = collect_paths(ROOT)
        names = {path.relative_to(ROOT).as_posix() for path in paths}
        self.assertTrue({'README.md', 'README.zh-CN.md', 'desktop_app.py', 'ui/preview/Main.qml'} <= names)
        self.assertNotIn('user_settings.json', names)
        self.assertTrue(all('.git/' not in name and '__pycache__' not in name for name in names))
        self.assertEqual(len(paths), len(names))


if __name__ == '__main__':
    unittest.main()
