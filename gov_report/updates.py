"""Read-only update feeds. Trust is anchored to this repository over HTTPS."""
from __future__ import annotations

import hashlib
import json
import math
import ntpath
import os
import re
import tempfile
import zipfile
from pathlib import Path, PureWindowsPath
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

from .scope import apply_scope

def reserved_name(part):
    if hasattr(ntpath, 'isreserved'):
        return ntpath.isreserved(part)
    return PureWindowsPath(part).is_reserved()

REPO = 'zsfan0628/GovPolicyWeekly'
RAW = f'https://raw.githubusercontent.com/{REPO}/main/updates'
LATEST = f'https://api.github.com/repos/{REPO}/releases/latest'
HOSTS = {'github.com', 'api.github.com', 'raw.githubusercontent.com', 'release-assets.githubusercontent.com',
         'objects.githubusercontent.com'}
MAX_CONFIG = 4 * 1024**2
MAX_BINARY = 600 * 1024**2


def trusted(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (443, None):
        raise ValueError('更新地址不受信任')
    return url


class Redirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, trusted(newurl))


def read_url(url, limit, *, output=None, cancelled=lambda: False, progress=lambda n: None):
    data = bytearray()
    size = 0
    digest = hashlib.sha256()
    with build_opener(Redirect()).open(trusted(url), timeout=15) as stream:
        while True:
            if cancelled():
                raise ValueError('更新已取消')
            chunk = stream.read(256 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise ValueError('更新文件超过大小限制')
            digest.update(chunk)
            if output is None:
                data.extend(chunk)
            else:
                output.write(chunk)
                progress(size)
    return bytes(data) if output is None else (size, digest.hexdigest())


def require(condition, message='更新数据无效或格式不兼容'):
    if not condition:
        raise ValueError(message)


def positive(n):
    return type(n) is int and 0 < n < 2**53


def label(s):
    return isinstance(s, str) and 0 < len(s) <= 200 and bool(s.strip()) and not re.search(r'[<>\x00-\x1f]', s)


def site_url(url):
    require(isinstance(url, str) and len(url) < 4096 and not re.search(r'[\\\s\x00-\x1f]', url))
    p = urlsplit(url)
    require(p.scheme in ('https', 'http') and (p.hostname or '').endswith('.gov.cn') and
            not p.username and not p.password and p.port in (None, 80, 443), '配置含非政府站点或无效网址')


def catalogue(pack):
    require(isinstance(pack, dict) and set(pack) == {'schema','revision','sources','scope','regions'}
            and type(pack['schema']) is int and pack['schema'] == 1 and positive(pack['revision']))
    sources, scope, regions = pack['sources'], pack['scope'], pack['regions']
    require(isinstance(sources, list) and 0 < len(sources) <= 1000 and isinstance(regions, list) and len(regions) <= 1000)
    require(isinstance(scope, dict) and set(scope) <= {'column_names','date_stop','minimum_pages','old_pages_required'}
            and isinstance(scope['column_names'], list) and all(label(v) for v in scope['column_names']))
    for key in ('minimum_pages','old_pages_required'):
        require(positive(scope.get(key, 3)) and scope.get(key, 3) <= 100)
    require(isinstance(scope.get('date_stop', True), bool))
    names, result = set(), []
    for s in sources:
        require(isinstance(s, dict) and set(s) <= {'name','department','region','base_url','list_urls','channel_names',
                                                   'entry_overrides','last_checked'})
        require(all(label(s[k]) for k in ('name','department','region')) and s['name'] not in names)
        require(not re.search(r'[\\/:*?"|]', s['name']) and s['name'] not in ('.','..'))
        names.add(s['name'])
        require(isinstance(s['list_urls'], list) and isinstance(s['channel_names'], dict))
        overrides = s.get('entry_overrides', {})
        require(isinstance(overrides, dict))
        for url in [s['base_url'], *s['list_urls'], *s['channel_names'], *overrides, *overrides.values()]:
            site_url(url)
        require(all(label(v) for v in s['channel_names'].values()))
        labels = dict(s['channel_names'])
        for old, new in overrides.items():
            labels.setdefault(new, labels.get(old, ''))
        row = apply_scope(dict(s, channel_names=labels), scope)
        # A worker reading this snapshot must not reapply an older bundled scope.
        row.setdefault('crawl_scope', {})
        result.append(row)
    used = set()
    for r in regions:
        require(isinstance(r, dict) and set(r) == {'region','city','title','lon','lat','lx','ly'} and
                all(label(r[k]) for k in ('region','city','title')) and r['region'] not in used)
        used.add(r['region'])
        for k, lo, hi in [('lon',70,140),('lat',15,56),('lx',0,.80),('ly',0,.80)]:
            require(type(r[k]) in (int,float) and math.isfinite(r[k]) and lo <= r[k] <= hi)
    return result, regions


def asset(info, limit):
    require(isinstance(info, dict) and positive(info['size']) and info['size'] <= limit and
            re.fullmatch(r'[0-9a-f]{64}', info['sha256']))
    return dict(size=info['size'], sha256=info['sha256'])


def version(s):
    require(isinstance(s, str) and re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}', s))
    return tuple(map(int, s.split('.')))


def config_offer(current, read=read_url):
    try:
        meta = json.loads(read(RAW+'/sites.json', 16384))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    require(meta['schema']==1 and positive(meta['revision']))
    if meta['revision'] <= current:
        return None
    return dict(kind='sites', revision=meta['revision'], url=RAW+'/catalogue.json',
                note=str(meta.get('notes',''))[:500], **asset(meta, MAX_CONFIG))


def app_offer(build, channel, read=read_url):
    release = json.loads(read(LATEST, 256*1024))
    if release.get('draft') or release.get('prerelease'):
        return None
    tag = release['tag_name']
    require(tag.startswith('v'))
    ver = version(tag[1:])
    if ver < version(build['version']):
        return None
    files = {a['name']:a for a in release['assets'] if a.get('state')=='uploaded'}
    if 'program-update.json' not in files:
        return None  # Releases predating the updater.
    base = f'https://github.com/{REPO}/releases/download/{tag}/'
    meta_bytes = read(base+'program-update.json', 16384)
    require(files['program-update.json'].get('digest') == 'sha256:'+hashlib.sha256(meta_bytes).hexdigest())
    meta = json.loads(meta_bytes)
    require(meta['schema']==1 and meta['version']==tag[1:] and positive(meta['build']))
    if (ver,meta['build']) <= (version(build['version']),build['build']):
        return None
    require(channel in ('installer','portable'))
    name = (f'GovPolicyWeekly_Setup_{tag[1:]}.exe' if channel=='installer' else 'GovPolicyWeekly_windows_portable.zip')
    info = asset(meta['assets'][name], MAX_BINARY)
    require(files[name]['size']==info['size'] and files[name].get('digest')=='sha256:'+info['sha256'])
    return dict(kind='app', name=name, channel=channel, version=meta['version'], build=meta['build'],
                note=str(release.get('body',''))[:1200], url=base+name, **info)


def fetch_verified(offer, path, read=read_url, **options):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
    try:
        with temp.open('wb') as out:
            size, digest = read(offer['url'], offer['size'], output=out, **options)
        require(size == offer['size'] and digest == offer['sha256'], '更新文件校验失败，保留原版本')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def verify_stream(stream, offer):
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: stream.read(256 * 1024), b''):
        size += len(chunk)
        require(size <= offer['size'])
        digest.update(chunk)
    require(size == offer['size'] and digest.hexdigest() == offer['sha256'], '下载文件已改变，请重新下载')
    stream.seek(0)


def unpack_portable(archive, destination):
    # Only unpack managed program files. Never treat user data as part of the distribution.
    root = Path(destination)
    root.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        total = 0
        seen = set()
        for entry in z.infolist():
            parts = entry.filename.rstrip('/').split('/')
            require(parts[0]=='GovPolicyWeekly' and all(
                p not in ('','.','..') and not p.endswith(('.', ' ')) and not re.search(r'[\\:|*?"<>\x00-\x1f]', p)
                and not reserved_name(p) for p in parts), '便携包路径无效')
            require(entry.external_attr >> 28 != 10, '便携包包含不支持的符号链接')
            if len(parts)==1:
                require(entry.is_dir())
                continue
            require(parts[1]=='_internal' or (len(parts)==2 and parts[1] in ('GovPolicyWeekly.exe','portable.channel')))
            key = '/'.join(parts).casefold()
            require(key not in seen)
            seen.add(key)
            total += entry.file_size
            require(total <= 2*1024**3 and len(seen) <= 40000)
            target = root.joinpath(*parts[1:])
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as out, z.open(entry) as inp:
                    import shutil
                    shutil.copyfileobj(inp, out)
    require((root/'GovPolicyWeekly.exe').is_file() and (root/'_internal').is_dir() and
            (root/'portable.channel').is_file(), '便携包不完整')
