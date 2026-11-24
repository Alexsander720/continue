"""Offline, optional decorative metadata shared by public Windows and Deck cards."""
import base64
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET


def _static_svg(data):
    """Small authored rail vocabulary only: no code, raster, filters or references out."""
    if len(data) > 16384 or b'<!' in data or b'<?' in data:
        return False
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError):
        return False
    ns = '{http://www.w3.org/2000/svg}'
    if root.tag != ns + 'svg' or any(root.get(k) != v for k, v in {
        'width': '48', 'height': '768', 'viewBox': '0 0 48 768',
        'preserveAspectRatio': 'xMidYMid meet',
    }.items()):
        return False
    tags = {'svg', 'defs', 'linearGradient', 'radialGradient', 'stop', 'path', 'rect', 'circle', 'ellipse'}
    attrs = {'width', 'height', 'viewBox', 'preserveAspectRatio', 'id', 'x', 'y', 'x1', 'x2',
             'y1', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'd', 'fill', 'stroke', 'stroke-width',
             'opacity', 'fill-opacity', 'offset', 'stop-color', 'stop-opacity', 'gradientUnits',
             'gradientTransform'}
    nodes = list(root.iter())
    if len(nodes) > 128:
        return False
    for node in nodes:
        if node.tag not in {ns + tag for tag in tags} or (node.text or '').strip() or (node.tail or '').strip():
            return False
        for key, value in node.attrib.items():
            if key not in attrs or len(value) > 1024:
                return False
            if key in ('fill', 'stroke', 'stop-color') and not re.fullmatch(
                    r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?|none|url\(#[A-Za-z][\w-]*\)', value):
                return False
    return True


@lru_cache(maxsize=4)
def _manifest(path, modified, size):
    if size > 262144:
        return {}
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    return value if isinstance(value, dict) else {}


@lru_cache(maxsize=64)
def _rail(path, modified, size):
    if not 33 <= size <= 30720:
        return {}
    data = Path(path).read_bytes()
    if Path(path).suffix == '.svg':
        if len(data) != size or not _static_svg(data):
            return {}
        return {'rail': 'data:image/svg+xml;base64,' + base64.b64encode(data).decode('ascii'),
                'rail_sha256': hashlib.sha256(data).hexdigest(), 'rail_width': 48}
    if len(data) != size or data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        return {}
    width, height = struct.unpack('>II', data[16:24])
    if not 1 <= width <= 48 or not 64 <= height <= 4096 or data[25] not in (4, 6):
        return {}
    return {'rail': 'data:image/png;base64,' + base64.b64encode(data).decode('ascii'),
            'rail_sha256': hashlib.sha256(data).hexdigest(), 'rail_width': width}


def game_visual(assets, appid):
    """A missing/malformed asset keeps legacy CSS; never prevents a save card."""
    result = {}
    try:
        if isinstance(appid, bool) or not re.fullmatch(r'[1-9][0-9]{0,9}', str(appid)):
            return result
        root = Path(assets)
        manifest = root / 'game_styles.json'
        if root.is_symlink() or manifest.is_symlink():
            return result
        stat = manifest.stat()
        rows = _manifest(str(manifest), stat.st_mtime_ns, stat.st_size)
        if str(appid) not in rows:
            return result
        row = rows[str(appid)]
        if not isinstance(row, dict):
            return result
        accent = row.get('accent')
        if isinstance(accent, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', accent):
            result['accent'] = accent
        if row.get('palette') in ('courier-blue', 'courier-black'):
            result['palette'] = row['palette']
        result['fallback'] = 'legacy'
        if row.get('rail') not in (f'rails/{appid}.png', f'rails/{appid}.svg'):
            return result
        path = root / row['rail']
        if path.is_symlink() or path.parent.is_symlink():
            return result
        stat = path.stat()
        result.update(_rail(str(path), stat.st_mtime_ns, stat.st_size))
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return result
