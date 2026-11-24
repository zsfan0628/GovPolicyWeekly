"""Desktop update state machine. Workers never mutate a Qt model."""
from __future__ import annotations

import json
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt
from PySide6.QtWidgets import QFileDialog

from .updates import MAX_CONFIG, app_offer, catalogue, config_offer, fetch_verified, positive, read_url, require, unpack_portable, verify_stream, version


class UpdateUI(QObject):
    changed = Signal()
    result = Signal(str, object)

    def __init__(self, owner, config_dir, data_dir, *, read=read_url):
        super().__init__(owner)
        self.owner, self.config, self.data, self.read = owner, Path(config_dir), Path(data_dir), read
        self.exe = Path(sys.executable)
        self.channel = None
        self.build = {}
        self.revision = int((self.config/'site-revision.txt').read_text())
        self.active = self.data/'active-sites.json'
        self.directory = self.data/'updates'
        self.stop = threading.Event()
        self.offers = {}
        self.ready = None
        self.working = False
        self.message = ''
        self.result.connect(self._result, Qt.QueuedConnection)
        try:
            if self.active.is_file():
                require(self.active.stat().st_size <= MAX_CONFIG)
                pack = json.loads(self.active.read_bytes())
                if pack['revision'] > self.revision:
                    self.owner.sources.install(*catalogue(pack))
                    self.revision = pack['revision']
        except (OSError, ValueError, KeyError, TypeError):
            self.message = '本地站点配置无效，已使用随软件配置'
        if sys.platform == 'win32' and getattr(sys, 'frozen', False):
            try:
                build = json.loads((self.config/'program-build.json').read_text(encoding='utf-8-sig'))
                version(build['version'])
                require(positive(build['build']))
                markers = [ch for ch in ('installer','portable') if (self.exe.parent/(ch+'.channel')).is_file()]
                if len(markers) == 1:
                    self.channel, self.build = markers[0], build
            except (OSError, ValueError, KeyError, TypeError):
                pass

    @Property(bool, notify=changed)
    def available(self):
        return bool(self.offers or self.ready)

    @Property(bool, notify=changed)
    def busy(self):
        return self.working

    @Property(str, notify=changed)
    def status(self):
        return self.message

    @Property('QVariantList', notify=changed)
    def items(self):
        return [dict(kind=k, title=(f"站点配置 · {v['revision']}" if k=='sites' else
                                    f"软件 v{v['version']} · 构建 {v['build']}"),
                     size=(f"{v['size']/1024:.0f} KB" if k=='sites' else f"{v['size']/1024**2:.1f} MB"),
                     note=v['note']) for k,v in self.offers.items()]

    @Property(str, notify=changed)
    def prepared(self):
        return self.ready[0]['kind'] if self.ready else ''

    def _work(self, kind, fn, message):
        self.working, self.message = True, message
        self.changed.emit()
        def run():
            try:
                value = fn()
            except Exception as exc:
                # Do not expose proxy addresses, private paths or upstream response text.
                if not self.stop.is_set():
                    self.result.emit('error', f'{message}失败（{type(exc).__name__}），原版本未更改')
            else:
                if not self.stop.is_set():
                    self.result.emit(kind, value)
        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def check(self):
        if self.stop.is_set() or self.working or self.ready:
            return
        revision = self.revision
        def work():
            offers, failed = {}, []
            for key, check in [('sites', lambda: config_offer(revision, self.read)),
                               ('app', lambda: app_offer(self.build, self.channel, self.read) if self.channel else None)]:
                try:
                    value = check()
                    if value:
                        offers[key] = value
                except Exception:
                    failed.append('站点配置' if key=='sites' else '程序版本')
            return offers, failed
        self._work('checked', work, '检查更新')

    @Slot(str)
    def download(self, key):
        if self.working or self.ready or key not in self.offers:
            return
        offer = self.offers[key]
        def work():
            self.directory.mkdir(parents=True, exist_ok=True)
            folder = Path(tempfile.mkdtemp(prefix='download-', dir=self.directory))
            path = folder/offer.get('name', 'sites.json')
            try:
                last = -10
                def progress(n):
                    nonlocal last
                    pct = n * 100 // offer['size']
                    if pct >= last + 5 and not self.stop.is_set():
                        self.result.emit('progress', pct)
                        last = pct
                fetch_verified(offer, path, self.read, cancelled=self.stop.is_set, progress=progress)
                if key=='sites':
                    pack = json.loads(path.read_bytes())
                    data = catalogue(pack)
                    require(pack['revision']==offer['revision'])
                    return offer, path, data
                return offer, path, None
            except Exception:
                shutil.rmtree(folder, ignore_errors=True)
                raise
        self._work('downloaded', work, '下载并校验')

    @Slot(str, object)
    def _result(self, kind, value):
        if self.stop.is_set():
            return
        if kind == 'progress':
            self.message = f'正在下载：{value}%'
            self.changed.emit()
            return
        self.working = False
        if kind=='checked':
            self.offers, failed = value
            self.message = ('、'.join(failed)+'检查失败，可稍后重试' if failed else
                            '发现可用更新' if self.offers else '当前没有可用更新')
        elif kind=='downloaded':
            self.ready = value
            offer, path, data = value
            if data:
                old = {s['name']:s for s in self.owner.sources.source_data}
                new = {s['name']:s for s in data[0]}
                self.message = (f'校验通过：新增 {len(new.keys()-old.keys())} 站，移除 {len(old.keys()-new.keys())} 站，'
                                f'变更 {sum(old[n]!=new[n] for n in old.keys() & new.keys())} 站。')
            else:
                self.message = '程序包校验通过。任务结束后可安装并重启。'
        elif kind=='prepared_portable':
            stage, target = value
            if self._blocked():
                shutil.rmtree(stage, ignore_errors=True)
                self.message = '请等待当前任务结束后再安装'
            else:
                try:
                    self._handoff(stage, target)
                except OSError:
                    shutil.rmtree(stage, ignore_errors=True)
                    self.message = '未能启动更新助手，旧程序保持不变'
        else:
            self.message = value
        self.changed.emit()

    def _blocked(self):
        return self.owner.running or self.owner.modelTesting or self.owner.modelsLoading

    @Slot()
    def discard(self):
        if not self.working and self.ready:
            shutil.rmtree(self.ready[1].parent, ignore_errors=True)
            self.ready = None
            self.message = ''
            self.changed.emit()

    def shutdown(self):
        self.stop.set()
        # Never remove a payload once the external helper has taken ownership.
        if self.ready and not self.working:
            shutil.rmtree(self.ready[1].parent, ignore_errors=True)
            self.ready = None

    @Slot()
    def apply(self):
        if self.working or not self.ready or self._blocked():
            return
        offer, path, data = self.ready
        try:
            if data:
                with path.open('rb') as source:
                    raw = source.read(MAX_CONFIG + 1)
                verify_stream(io.BytesIO(raw), offer)
                with tempfile.NamedTemporaryFile(dir=self.active.parent, delete=False) as out:
                    pending = Path(out.name)
                try:
                    pending.write_bytes(raw)
                    os.replace(pending, self.active)
                finally:
                    pending.unlink(missing_ok=True)
                self.owner.sources.install(*data)
                self.revision = offer['revision']
                self.owner.saveConfig({})
                self.offers.pop('sites', None)
                self.discard()
                self.message = '站点配置已更新，下次新任务生效'
            elif self.channel=='installer':
                self._handoff(path, self.exe.parent)
            elif self.channel=='portable':
                target = self.exe.parent
                try:
                    stage = Path(tempfile.mkdtemp(prefix='.gov-update-', dir=target))
                except OSError:
                    selected = QFileDialog.getExistingDirectory(None, '当前位置不可写，请选择新便携目录的上级目录')
                    if not selected:
                        return
                    target = Path(selected)/'GovPolicyWeekly'
                    target.mkdir(exist_ok=True)
                    if any(target.iterdir()):
                        raise OSError('Target directory is not empty')
                    stage = Path(tempfile.mkdtemp(prefix='.gov-update-', dir=target))
                def extract():
                    try:
                        with path.open('rb') as archive:
                            verify_stream(archive, offer)
                            unpack_portable(archive, stage/'new')
                        return stage, target
                    except Exception:
                        shutil.rmtree(stage, ignore_errors=True)
                        raise
                self._work('prepared_portable', extract, '准备便携更新')
        except ValueError:
            self.message = '更新文件校验失败，请放弃本次下载并重新下载，原版本未更改'
        except OSError:
            self.message = '无法应用更新，请确认目录可写；更换便携目录时请选择空的新目录'
        self.changed.emit()

    def _handoff(self, payload, target):
        # The helper must live outside the managed application directory.
        helper = self.ready[1].parent/'apply-update.ps1'
        shutil.copyfile(self.config/'apply-update.ps1', helper)
        env = dict(os.environ, GPW_PID=str(os.getpid()), GPW_MODE=self.channel, GPW_TARGET=str(target),
                   GPW_PAYLOAD=str(payload), GPW_SHA=self.ready[0]['sha256'], PYINSTALLER_RESET_ENVIRONMENT='1')
        shell = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        subprocess.Popen([str(shell), '-NoProfile', '-NonInteractive','-ExecutionPolicy','RemoteSigned',
                          '-File',str(helper)], cwd=helper.parent, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        self.working = True
        self.owner.closeReady.emit()
