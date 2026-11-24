"""Generate the independent, data-only site feed locally (never publishes)."""
import argparse
import hashlib
import json
from pathlib import Path

import yaml

from gov_report.updates import catalogue


def generate(config, destination, notes):
    def read(name):
        return yaml.safe_load((config/name).read_text(encoding='utf-8'))
    pack = dict(schema=1, revision=int(read('site-revision.txt')), sources=read('sources.yaml'),
                regions=read('map-regions.yaml'), scope=read('crawl_scope.yaml'))
    catalogue(pack)
    data = json.dumps(pack, ensure_ascii=False, separators=(',', ':'), default=str).encode()
    digest = hashlib.sha256(data).hexdigest()
    destination.mkdir(parents=True, exist_ok=True)
    manifest = destination/'sites.json'
    if manifest.exists():
        old = json.loads(manifest.read_bytes())
        if old['revision'] > pack['revision'] or (old['revision']==pack['revision'] and old['sha256']!=digest):
            raise ValueError('配置有变更，请先提高 config/site-revision.txt 中的版本号')
    (destination/'catalogue.json').write_bytes(data)
    manifest.write_text(json.dumps(dict(schema=1, revision=pack['revision'], notes=notes,
                                        size=len(data), sha256=digest), ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notes', default='更新采集站点、栏目与地区代表点')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    generate(root/'config', root/'updates', args.notes)
