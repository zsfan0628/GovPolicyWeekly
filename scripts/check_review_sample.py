"""Compare manually reviewed URL labels against one report, without network calls."""

import argparse
import json
from pathlib import Path

from gov_report.crawler import normalize_url_for_dedupe


def compare(records, labels):
    found = {normalize_url_for_dedupe(r['url']) for r in records}
    expected = {}
    for row in labels:
        url, decision = row['url'], row['decision']
        key = normalize_url_for_dedupe(url)
        if not url.startswith(('http://', 'https://')) or key in expected or decision not in {'include', 'exclude', 'discuss'}:
            raise ValueError('样本需要唯一 HTTP(S) 地址和 include/exclude/discuss 标签')
        expected[key] = (url, decision)
    return dict(labeled=len(expected), must_include=sum(v[1]=='include' for v in expected.values()),
                must_exclude=sum(v[1]=='exclude' for v in expected.values()),
                missed=[url for k,(url,v) in expected.items() if v=='include' and k not in found],
                unexpected=[url for k,(url,v) in expected.items() if v=='exclude' and k in found],
                discuss=[url for url,v in expected.values() if v=='discuss'],
                unlabeled_report_urls=len(found - expected.keys()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', type=Path)
    parser.add_argument('labels', type=Path)
    args = parser.parse_args()
    result = compare(*(json.loads(p.read_text(encoding='utf-8-sig')) for p in (args.data, args.labels)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(int(bool(result['missed'] or result['unexpected'])))
