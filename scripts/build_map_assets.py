"""Generate offline schematic map SVGs from Natural Earth's public-domain GeoJSON."""
import json
import sys
from pathlib import Path


def paths(features, project):
    result = []
    for feature in features:
        geometry = feature['geometry']
        polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
        for polygon in polygons:
            commands = []
            for ring in polygon:
                points = [project(lon, lat) for lon, lat, *_ in ring]
                commands.append('M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in points) + ' Z')
            result.append('<path d="' + ' '.join(commands) + '"/>')
    return ''.join(result)


if __name__ == '__main__':
    features = json.loads(Path(sys.argv[1]).read_text())['features']
    dest = Path(__file__).resolve().parents[1] / 'ui/preview/assets'
    world = paths(features, lambda x, y: (x + 180, 90 - y))
    region = paths([f for f in features if f['properties']['ADM0_A3'] in {'CHN', 'TWN'}],
                   lambda x, y: ((x - 70) * .82, 56 - y))
    for name, view, body, fill, stroke, thickness in (
        ('world-outline', '0 0 360 180', world, '#e4ebe8', '#cbd8d3', '.2'),
        ('china-region', '0 0 57.4 41', region, '#e5eeea', '#8caaa0', '.13'),
    ):
        (dest / (name + '.svg')).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}">'
            f'<g fill="{fill}" stroke="{stroke}" stroke-width="{thickness}" fill-rule="evenodd">{body}</g></svg>')
