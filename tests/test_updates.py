import copy
import hashlib
import io
import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from gov_report.desktop import DesktopController, SettingsStore
from gov_report.update_ui import UpdateUI
from gov_report.updates import (LATEST, RAW, REPO, app_offer, catalogue, config_offer,
                                fetch_verified, trusted, unpack_portable)
from scripts.prepare_site_update import generate
from ui_preview import Sources


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = json.loads((ROOT/'updates/catalogue.json').read_bytes())


def info(data):
    return {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class Feed(dict):
    """No network or local user config. Only known, public requests succeed."""
    def __call__(self, url, limit, *, output=None, cancelled=lambda: False, progress=lambda n: None):
        data = self[url]
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        if len(data) > limit or cancelled():
            raise ValueError('size or cancellation')
        if output is None:
            return data
        output.write(data)
        progress(len(data))
        return len(data), info(data)['sha256']


def site_feed():
    pack = copy.deepcopy(PACKAGE)
    pack['revision'] += 1
    for region in ('浙江', '新地区'):
        pack['sources'].append(dict(pack['sources'][0], name=region+'示例站', region=region))
    pack['regions'].append(dict(region='浙江', city='杭州', title='浙江省', lon=120, lat=30, lx=.5, ly=.7))
    payload = json.dumps(pack).encode()
    return Feed({RAW+'/catalogue.json': payload, RAW+'/sites.json': dict(
        schema=1, revision=pack['revision'], **info(payload))})


def release_feed():
    ver = '1.4.0'
    base = f'https://github.com/{REPO}/releases/download/v{ver}/'
    files = {f'GovPolicyWeekly_Setup_{ver}.exe': b'installer', 'GovPolicyWeekly_windows_portable.zip': b'portable'}
    meta = dict(schema=1, version=ver, build=21, assets={k: info(v) for k,v in files.items()})
    files['program-update.json'] = json.dumps(meta).encode()
    release = dict(tag_name='v'+ver, assets=[dict(name=k, state='uploaded', size=len(v),
                         digest='sha256:'+info(v)['sha256']) for k,v in files.items()])
    return Feed({LATEST: release, **{base+k:v for k,v in files.items()}})


class UpdateValidationTests(unittest.TestCase):
    def test_packaged_feed_matches_verified_manifest(self):
        meta = json.loads((ROOT/'updates/sites.json').read_bytes())
        self.assertEqual(info((ROOT/'updates/catalogue.json').read_bytes()), {k:meta[k] for k in ('size','sha256')})
        self.assertEqual(meta['revision'], int((ROOT/'config/site-revision.txt').read_text()))
        data, regions = catalogue(PACKAGE)
        self.assertEqual({r['name'] for r in data}, {r['name'] for r in Sources().source_data})
        self.assertTrue(regions)
        self.assertIsNone(config_offer(meta['revision'], Feed({RAW+'/sites.json':meta})))
        with tempfile.TemporaryDirectory() as tmp:
            generate(ROOT/'config',Path(tmp),meta['notes'])
            self.assertEqual((Path(tmp)/'catalogue.json').read_bytes(), (ROOT/'updates/catalogue.json').read_bytes())

    def test_untrusted_urls_and_executable_config_are_rejected(self):
        for url in ('http://github.com/', 'https://github.com.example.org/', 'https://github.com:8443/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                trusted(url)
        for change in ({'base_url':'file:///tmp/test'}, {'base_url':'https://example.org/'},
                       {'name':'../elsewhere'}, {'post_install':'arbitrary'}, {'region':'<label>'}):
            pack = copy.deepcopy(PACKAGE)
            pack['sources'][0].update(change)
            with self.assertRaises(ValueError):
                catalogue(pack)

    def test_program_offers_use_channel_and_same_version_build(self):
        feed = release_feed()
        for channel, suffix in [('installer','.exe'), ('portable','.zip')]:
            offer = app_offer({'version':'1.4.0','build':20}, channel, feed)
            self.assertTrue(offer['url'].endswith(suffix))
            self.assertEqual(offer['build'],21)
        for ver, build in [('1.4.0',21),('1.4.0',22),('2.0.0',1)]:
            self.assertIsNone(app_offer({'version':ver,'build':build},'installer',feed))
        build = dict(version='1.3.0',build=100)
        for flag in ('draft','prerelease'):
            feed[LATEST][flag] = True
            self.assertIsNone(app_offer(build,'portable',feed))
            del feed[LATEST][flag]
        feed[LATEST]['assets'] = []
        self.assertIsNone(app_offer(build,'installer',feed))

    def test_reject_manifest_and_asset_digest_mismatch(self):
        for name in ('program-update.json', 'GovPolicyWeekly_windows_portable.zip'):
            feed = release_feed()
            next(a for a in feed[LATEST]['assets'] if a['name']==name)['digest'] = None
            with self.assertRaises(ValueError):
                app_offer(dict(version='1.4.0',build=1), 'portable',feed)

    def test_incomplete_or_corrupt_download_leaves_previous_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'existing'
            path.write_bytes(b'previous')
            for data in (b'X', b'BAD', b'LONG'):
                with self.assertRaises(ValueError):
                    fetch_verified(dict(url='fixture',**info(b'new')),path,Feed(fixture=data))
                self.assertEqual(path.read_bytes(), b'previous')
                self.assertEqual(list(path.parent.iterdir()), [path])

    def test_portable_contents_and_invalid_entries(self):
        def archive(extra=None):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf,'w') as z:
                for k in ('GovPolicyWeekly.exe','_internal/file','portable.channel'):
                    z.writestr('GovPolicyWeekly/'+k,b'fixture')
                if extra is not None:
                    z.writestr(extra,b'bad')
            return buf
        link = zipfile.ZipInfo('GovPolicyWeekly/_internal/ref')
        link.external_attr = 0o120777 << 16
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            unpack_portable(archive(), dest/'ok')
            self.assertEqual((dest/'ok'/'GovPolicyWeekly.exe').read_bytes(),b'fixture')
            for i, extra in enumerate(('GovPolicyWeekly/../escape', 'GovPolicyWeekly/output/report.pdf',
                                       'GovPolicyWeekly/_internal/FILE',link)):
                with self.assertRaises(ValueError):
                    unpack_portable(archive(extra), dest/str(i))
            self.assertFalse((dest/'escape').exists())


class DesktopUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        store = SettingsStore(self.root/'settings.json', self.root/'missing')
        store.save(dict(openai_api_key='fixture-only', output_root=str(self.root/'reports')))
        self.owner = DesktopController(Sources(), store)
        self.addCleanup(self.owner.shutdown)
        self.ui = UpdateUI(self.owner, ROOT/'config', self.root, read=site_feed())

    def wait(self):
        deadline = time.monotonic()+5
        while self.ui.busy and time.monotonic()<deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertFalse(self.ui.busy)

    def download(self):
        self.ui.check()
        self.wait()
        self.assertTrue(self.ui.available)
        self.assertFalse(self.ui.active.exists())
        self.ui.download('sites')
        self.wait()
        self.assertEqual(self.ui.prepared, 'sites',self.ui.status)

    def test_apply_is_idle_only_and_restores_map_and_existing_selection(self):
        sources = self.owner.sources
        sources.toggle(0)
        selected = {r['siteName'] for r in sources.rows if r['selected']}
        self.download()
        self.owner._running = True
        self.ui.apply()
        self.assertFalse(self.ui.active.exists())
        self.owner._running = False
        self.ui.apply()
        self.assertFalse(self.ui.available)
        self.assertEqual(selected,{r['siteName'] for r in sources.rows if r['selected']})
        self.assertIn('浙江', {r['region'] for r in sources.mapLocations})
        self.assertNotIn('新地区', {r['region'] for r in sources.mapLocations})
        self.assertIn('新地区', sources.regionCounts)
        saved = self.owner.store.load()
        self.assertEqual(saved['openai_api_key'],'fixture-only')
        self.assertEqual(set(saved['selected_sources']),selected)
        with patch('gov_report.desktop.QTimer.singleShot'):
            restored = DesktopController(Sources(), self.owner.store,enable_updates=True)
        try:
            self.assertEqual(restored.sources.regionCounts,sources.regionCounts)
            self.assertEqual(restored.updater.revision, self.ui.revision)
        finally:
            restored.shutdown()

    def test_tampered_or_discarded_download_never_replaces_config(self):
        self.download()
        self.ui.ready[1].write_bytes(b'changed')
        self.ui.apply()
        self.assertFalse(self.ui.active.exists())
        self.assertIn('校验失败',self.ui.status)
        self.ui.discard()
        self.assertFalse(self.ui.prepared)
        self.assertEqual(list(self.ui.directory.iterdir()),[])

    def test_failed_check_or_bad_active_config_falls_back(self):
        self.ui.active.write_bytes(b'invalid')
        reload = UpdateUI(self.owner, ROOT/'config',self.root, read=Feed())
        self.assertIn('无效', reload.status)
        self.ui.read = Feed()
        self.ui.check()
        self.wait()
        self.assertFalse(self.ui.available)
        self.assertIn('稍后重试',self.ui.status)

    def test_installer_handoff_requires_confirmation_and_idle(self):
        self.ui.channel, self.ui.build = 'installer', dict(version='1.4.0',build=10)
        self.ui.read.update(release_feed())
        with patch.object(self.ui,'_handoff') as handoff:
            self.ui.check()
            self.wait()
            self.ui.download('app')
            self.wait()
            self.assertEqual(self.ui.prepared,'app')
            self.owner._model_testing = True
            self.ui.apply()
            handoff.assert_not_called()
            self.owner._model_testing = False
            self.ui.apply()
            handoff.assert_called_once_with(self.ui.ready[1], self.ui.exe.parent)

    def test_portable_preparation_preserves_running_copy_and_custom_files(self):
        target = self.root/'portable'
        target.mkdir()
        self.ui.channel, self.ui.exe = 'portable', target/'GovPolicyWeekly.exe'
        self.ui.exe.write_bytes(b'old exe')
        (target/'report.pdf').write_bytes(b'old report')
        with io.BytesIO() as buf:
            with zipfile.ZipFile(buf,'w') as z:
                for k in ('GovPolicyWeekly.exe','_internal/runtime','portable.channel'):
                    z.writestr('GovPolicyWeekly/'+k,b'new')
            raw = buf.getvalue()
        url = 'portable-fixture'
        self.ui.offers = {'app': dict(kind='app', url=url, name='portable.zip', **info(raw))}
        self.ui.read[url] = raw
        self.ui.download('app')
        self.wait()
        with patch.object(self.ui,'_handoff') as handoff:
            self.ui.apply()
            self.wait()
            stage, where = handoff.call_args.args
            self.assertEqual(where,target)
            self.assertEqual((stage/'new/GovPolicyWeekly.exe').read_bytes(),b'new')
            self.assertEqual(self.ui.exe.read_bytes(),b'old exe')
            self.assertEqual((target/'report.pdf').read_bytes(),b'old report')
