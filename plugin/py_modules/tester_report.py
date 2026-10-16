"""Local tester diagnostics: bounded, sanitized JSON only, never raw saves."""
from __future__ import annotations
import getpass
import json
import os
from pathlib import Path
import re
import time
import uuid
import zipfile

MAX_REPORT_BYTES = 512 * 1024
MAX_LOG_BYTES = 32768
SETTING_KEYS = ('preset', 'bg_source', 'disk_limit_gb', 'youtube_consent', 'recording_enabled',
                'theme_music_consent', 'home_live', 'home_music', 'hub_music', 'live_bg',
                'home_installed_first', 'brightness_bar', 'pdb_button', 'pdb_tiles', 'game_source', 'game_bg',
                'hide_launch_notice', 'music_provider')
CACHE_KEYS = ('cached_backgrounds', 'cached_games', 'files', 'bytes', 'disk_limit_gb', 'limit_bytes',
              'ffmpeg', 'yt_dlp', 'yt_dlp_verified', 'youtube_experimental', 'error', 'busy')

SCHEMA_KEYS = frozenset(SETTING_KEYS + CACHE_KEYS + (
    'schema', 'versions', 'plugin', 'decky', 'steamos', 'steam', 'VERSION_ID', 'BUILD_ID',
    'language', 'settings', 'log_tail', 'games', 'background_cache', 'privacy', 'unavailable_versions',
    'appid', 'name', 'status', 'error', 'card', 'place', 'facts', 'id', 'label', 'value', 'parse_ms',
))


def home_dir():
    from ddsaves._common import deck_home
    return deck_home()


def usernames():
    values = {home_dir().name, os.environ.get('USER', ''), os.environ.get('USERNAME', '')}
    try:
        values.add(getpass.getuser())
    except (OSError, KeyError):
        pass
    return sorted(x for x in values if x and x not in ('/', '<user>'))


def steam_identities(steam_root):
    values = []
    try:
        with (Path(steam_root) / 'config/loginusers.vdf').open('rb') as stream:
            text = stream.read(262144).decode('utf-8', 'replace')
        values.extend(re.findall(r'"(?:AccountName|PersonaName)"\s+"([^"\n]+)"', text, re.I))
        for identity in re.findall(r'"(7656119\d{10})"', text):
            values.append(str(int(identity) & 0xFFFFFFFF))
    except OSError:
        pass
    return [x for x in values if x]


def sanitize(value, names=None):
    """Apply to keys too. All identities, including the author's, are private."""
    names = usernames() if names is None else names
    if isinstance(value, dict):
        return {str(k) if str(k) in SCHEMA_KEYS else sanitize(str(k), names): sanitize(v, names)
                for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v, names) for v in value]
    # Reader values are normally small counters, but a malformed/community
    # reader can return a SteamID as an integer.  JSON would otherwise bypass
    # all string redaction and the public STOP scanner would catch the leak.
    if isinstance(value, int) and re.fullmatch(r'7656119\d{10}', str(value)):
        return '<steamid>'
    if not isinstance(value, str):
        return value
    text = value
    text = re.sub(r'\\\\[^\\/"<>\r\n]+\\[^\\/"<>\r\n]+', r'\\\\<server>\\\\<share>', text)
    text = re.sub(r'(?i)([A-Z]:[\\/]+Users[\\/]+)[^\\/"<>\r\n]+', r'\1<user>', text)
    text = re.sub(r'(?i)\b[A-Z]:[\\/]+(?!Users[\\/]+)[^\\/"<>\r\n]+', '<path>/<secret>', text)
    text = re.sub(r'(?i)\b[A-Z]:[\\/]+', '<path>/', text)
    text = re.sub(r'/run/media/[^/"<>\r\n]+/[^/"<>\r\n]+', '/run/media/<user>/<volume>', text)
    text = re.sub(r'(/home/|/Users/|/run/media/)[^/"<>\r\n]+', r'\1<user>', text)
    text = re.sub(r'(?i)(userdata[\\/]+|SaveGames[\\/]+)\d+', r'\1<steamid>', text)
    text = re.sub(r'\b7656119\d{10}\b', '<steamid>', text)
    text = re.sub(r'\b\d{17}\b', '<steamid>', text)
    text = re.sub(r'\[U:\d+:\d+\]', '<steamid>', text, flags=re.I)
    text = re.sub(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])', '<address>', text)
    text = re.sub(r'(?i)\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b', '<address>', text)
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', '<email>', text)
    text = re.sub(r'(?i)\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{30,}|AIza[A-Za-z0-9_-]{30,}|\d{8,10}:[A-Za-z0-9_-]{35,})\b', '<secret>', text)
    text = re.sub(r'(?i)(\bauthorization\s*[=:]\s*)(?:Bearer\s+)?[^\s,;]+', r'\1<secret>', text)
    text = re.sub(r'(?i)((?:token|password|secret|api[_-]?key|authorization)\s*[=:]\s*)[^\s,;]+', r'\1<secret>', text)
    for name in sorted(names, key=len, reverse=True):
        if not isinstance(name, str) or not name or name.startswith('<'):
            continue
        if len(name) <= 2:
            if text.casefold() == name.casefold():
                text = '<user>'
        else:
            # Underscores delimit embedded identities in generated save names.
            text = re.sub(r'(?i)(?<![A-Za-zА-Яа-яЁёІіЇїЄєҐґ0-9])(?<!<)' + re.escape(name) + r'(?![A-Za-zА-Яа-яЁёІіЇїЄєҐґ0-9])(?!>)', '<user>', text)
    return text


def privacy_names(steam_root):
    """Known local identities for reports and for errors raised while making one."""
    return usernames() + steam_identities(steam_root)


def encode(report):
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if len(payload.encode('utf-8')) > MAX_REPORT_BYTES:
        raise ValueError('Report exceeds the local size limit')
    return payload


def read_tail(path, count=100):
    try:
        with Path(path).open('rb') as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - MAX_LOG_BYTES))
            return '\n'.join(stream.read(MAX_LOG_BYTES).decode('utf-8', 'replace').splitlines()[-count:])
    except (OSError, ValueError):
        return ''


def installed(libraries):
    games = {}
    for library in libraries:
        for manifest in sorted((Path(library) / 'steamapps').glob('appmanifest_*.acf')):
            try:
                text = manifest.read_text(encoding='utf-8', errors='replace')[:65536]
                appid = int(re.search(r'"appid"\s+"(\d+)"', text)[1])
                name = re.search(r'"name"\s+"([^"\n]*)"', text)
                games[appid] = (name[1] if name else str(appid))[:180]
            except (OSError, ValueError, TypeError):
                continue
    return sorted(games.items())


def game_results(libraries, readers, read, data_dir):
    results = []
    for appid, name in installed(libraries):
        started = time.perf_counter()
        row = {'appid': appid, 'name': name, 'status': 'unsupported', 'error': None}
        if appid in readers:
            try:
                result = read(appid, data_dir)
                if isinstance(result, dict) and result.get('error'):
                    row.update(status='error', error=str(result['error'])[:1200])
                elif result:
                    row['status'] = 'found'
                    # Do not copy arbitrary reader dicts or raw progress. The
                    # visible result is enough to reproduce UI questions.
                    save = result.get('save') or {}
                    row['card'] = {'place': save.get('place'),
                                   'facts': [{k: f.get(k) for k in ('id', 'label', 'value')}
                                             for f in (result.get('facts') or [])[:40]]}
                else:
                    row['status'] = 'missing'
            except Exception as error:
                row.update(status='error', error=f'{type(error).__name__}: {error}'[:1200])
        row['parse_ms'] = round((time.perf_counter() - started) * 1000, 3)
        results.append(row)
    return results


def versions(plugin_dir, decky, steam_root):
    result = {'plugin': None, 'decky': None, 'steamos': None, 'steam': None}
    try:
        result['plugin'] = json.loads((Path(plugin_dir) / 'RELEASE.json').read_text(encoding='utf-8')).get('version')
    except (OSError, ValueError, AttributeError):
        pass
    decky_version = getattr(decky, 'DECKY_VERSION', None) or os.environ.get('DECKY_VERSION')
    if isinstance(decky_version, (str, int, float)):
        result['decky'] = str(decky_version)[:100]
    try:
        text = Path('/etc/os-release').read_text(encoding='utf-8')
        fields = dict(re.findall(r'^(VERSION_ID|BUILD_ID)=(.*)$', text, re.M))
        result['steamos'] = {k: v.strip('"')[:100] for k, v in fields.items()} or None
    except OSError:
        pass
    try:
        text = (Path(steam_root) / 'package/steam_client_ubuntu12.installed').read_text(encoding='utf-8')[:32768]
        version = re.search(r'"version"\s+"(\d+)"', text)
        result['steam'] = version[1] if version else None
    except OSError:
        pass
    return result


def collect(plugin, settings, decky, data_dir):
    from ddsaves._common import lang, steam_libraries
    import deck_saves
    manager = getattr(plugin, '_standalone_media', None)
    cache = manager.status() if manager is not None else {'cached_backgrounds': 0, 'busy': False}
    # Inspect only this plugin logger's file handler; never Decky's global log.
    logs = []
    for handler in getattr(decky.logger, 'handlers', []):
        filename = getattr(handler, 'baseFilename', None)
        if filename:
            logs.append(read_tail(filename))
    report = {'schema': 1, 'versions': versions(plugin._plugin_dir(), decky, plugin._steam_root()),
              'language': lang(), 'settings': {k: settings[k] for k in SETTING_KEYS if k in settings},
              'log_tail': '\n'.join(logs)[-MAX_LOG_BYTES:],
              'games': game_results(steam_libraries(), deck_saves.READERS, deck_saves.read, data_dir),
              'background_cache': {k: cache[k] for k in CACHE_KEYS if k in cache},
              'privacy': 'Only this reviewed JSON is saved. No save files, account IDs, usernames, or media files.',
              'unavailable_versions': 'null means not available locally; no external requests were made'}
    return sanitize(report, privacy_names(plugin._steam_root()))


def windows_known_folder(folder_id):
    import ctypes
    import os
    if os.name!='nt':return None
    guid=(ctypes.c_byte*16).from_buffer_copy(uuid.UUID(folder_id).bytes_le)
    result=ctypes.c_void_p()
    shell=ctypes.WinDLL('shell32',use_last_error=True)
    shell.SHGetKnownFolderPath.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)]
    shell.SHGetKnownFolderPath.restype=ctypes.c_long
    if shell.SHGetKnownFolderPath(ctypes.byref(guid),0,None,ctypes.byref(result))!=0:return None
    try:return Path(ctypes.wstring_at(result))
    finally:
        ole=ctypes.WinDLL('ole32');ole.CoTaskMemFree.argtypes=[ctypes.c_void_p];ole.CoTaskMemFree(result)


def save(payload, home=None):
    # Saving accepts only the already-reviewed JSON text from the server token.
    if len(payload.encode('utf-8')) > MAX_REPORT_BYTES:
        raise ValueError('Report exceeds the local size limit')
    json.loads(payload)
    directories=[]
    if home is None:
        for folder in ('B4BFCC3A-DB2C-424C-B029-7FE99A87C641','374DE290-123F-4565-9164-39C4925E467B'):
            try:
                directory=windows_known_folder(folder)
                if directory:directories.append(directory)
            except (OSError,AttributeError):pass
    home = Path(home) if home is not None else home_dir()
    directories.extend(home/name for name in ('Desktop','Downloads'))
    errors = []
    for directory in dict.fromkeys(directories):
        if not directory.is_dir():
            continue
        destination = directory / ('continue-report-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8] + '.zip')
        try:
            with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('report.json', payload.encode('utf-8'))
            return destination
        except OSError as error:
            errors.append(type(error).__name__)
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
    raise OSError('No writable Desktop/Downloads folder: ' + ', '.join(errors))
