"""Offline regressions for defects observed in the r13 live PC audit."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(os.environ.get('CONTINUE_R14_ROOT', Path(__file__).resolve().parents[1]))
if not (ROOT / 'py_modules').is_dir() and not (ROOT / 'plugin/py_modules').is_dir():
    ROOT = Path(__file__).resolve().parents[2]
if (ROOT / 'plugin/py_modules').is_dir():
    MODULES, PC = ROOT / 'plugin/py_modules', ROOT / 'pc'
else:
    MODULES = ROOT / 'py_modules'
    PC = ROOT.parents[1] / 'pc_bp'
sys.path[:0] = [str(PC), str(MODULES)]


@pytest.fixture(params=['pc', 'deck', 'base'])
def manager(request, tmp_path):
    from standalone_media import MediaManager
    from public_media_policy import PCMediaManager
    from deck_music_media import DeckMediaManager
    return {'pc': PCMediaManager, 'deck': DeckMediaManager, 'base': MediaManager}[request.param](tmp_path)


def test_only_exact_final_valid_theme_is_enumerated(manager, monkeypatch):
    manager.media.mkdir(parents=True)
    for name in ['391540_theme.part.m4a', '391540_theme.part.temp.m4a', '391540_theme.tmp',
                 '391540_theme.m4a.tmp', '391540_theme.mp4', '391540_theme.m4a', '42_theme.m4a']:
        (manager.media / name).write_bytes(b'valid-fixture' if name != '42_theme.m4a' else b'bad')
    monkeypatch.setattr(manager, '_valid_audio', lambda p: p.read_bytes() == b'valid-fixture')
    assert manager.music_files() == {'391540': manager._relative(manager.media / '391540_theme.m4a')}


def test_part_alone_cannot_become_a_theme(manager, monkeypatch):
    manager.media.mkdir(parents=True)
    (manager.media / '391540_theme.part.m4a').write_bytes(b'complete-but-staged')
    monkeypatch.setattr(manager, '_valid_audio', lambda p: True)
    assert manager.music_files() == {}


def test_failed_download_removes_all_staging_files(manager, monkeypatch):
    monkeypatch.setattr(manager, '_ytdlp_command', lambda: ['stub'])
    def run(command, **kw):
        (manager.media / '42_theme.part.m4a').write_bytes(b'partial')
        (manager.media / '42_theme.part.temp.m4a').write_bytes(b'partial')
        raise subprocess.TimeoutExpired(command, 300)
    monkeypatch.setattr(manager, 'run', run)
    with pytest.raises(Exception):
        manager._download_youtube('https://www.youtube.com/watch?v=abcdefghijk', '42_theme', {}, audio=True)
    assert list(manager.media.iterdir()) == []


@pytest.mark.parametrize('platform', ['pc', 'deck'])
@pytest.mark.parametrize('message,reason', [
    ('Connection timed out', 'theme_timeout'),
    ('Unable to download webpage: Temporary failure in name resolution', 'theme_network_error'),
    ('Requested format is not available', 'theme_format_unavailable'),
    ('Postprocessing: ffmpeg exited with code 1', 'theme_encode_failed'),
    ('unrecognized failure', 'theme_download_failed'),
    ('Permission denied: file is being used by another process', 'theme_file_busy'),
])
def test_download_reason_survives_worker_status_and_cooldown(tmp_path, monkeypatch, platform, message, reason):
    from public_media_policy import PCMediaManager, get_game_media_status
    from deck_music_media import DeckMediaManager
    manager = (PCMediaManager if platform == 'pc' else DeckMediaManager)(tmp_path)
    monkeypatch.setattr(manager, '_own_ytdlp', lambda: None)
    monkeypatch.setattr(manager, 'locate_ytdlp', lambda: Path('stub'))
    monkeypatch.setattr(manager, '_ytdlp_command', lambda: ['stub'])
    monkeypatch.setattr(manager, 'store_data', lambda *a: {'name': 'Fixture'})
    monkeypatch.setattr(manager, 'youtube_candidates', lambda *a, **kw: [{'url': 'https://www.youtube.com/watch?v=abcdefghijk'}])
    calls = []
    def run(command, **kw):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, stdout=b'', stderr=message.encode())
    monkeypatch.setattr(manager, 'run', run)
    settings = {'theme_music_consent': True, 'hub_music': True}
    result = manager._maybe_theme(42, 'Fixture', settings)
    assert result.get('reason') == reason
    assert get_game_media_status(manager, 42, 'Fixture', settings)['music']['status'] == reason
    assert manager._maybe_theme(42, 'Fixture', settings).get('reason') == reason
    assert len(calls) == 1
    assert manager._maybe_theme(42, 'Fixture', settings, force=True).get('reason') == reason
    assert len(calls) == 2  # explicit retry, never an automatic retry storm


@pytest.mark.parametrize('filtered', [False, True])
def test_empty_or_filtered_search_is_typed_and_bounded(manager, monkeypatch, filtered):
    monkeypatch.setattr(manager, '_own_ytdlp', lambda: None)
    monkeypatch.setattr(manager, 'locate_ytdlp', lambda: Path('stub'))
    monkeypatch.setattr(manager, '_ytdlp_command', lambda: ['stub'])
    monkeypatch.setattr(manager, 'store_data', lambda *a: {'name': 'Fixture™ Complete Edition'})
    monkeypatch.setattr('time.sleep', lambda seconds: None)
    calls = []
    def run(command, **kw):
        calls.append(command)
        row = {'webpage_url': 'https://www.youtube.com/watch?v=abcdefghijk', 'title': 'Unrelated OST', 'duration': 90}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(row) if filtered else '', stderr='')
    monkeypatch.setattr(manager, 'run', run)
    with pytest.raises(RuntimeError) as error:
        manager.build_theme(42, 'Fixture', {'theme_music_consent': True})
    assert str(error.value) == ('theme_title_filtered' if filtered else 'theme_no_candidate')
    assert len(calls) == 2
    assert '™' not in calls[1][1] and 'Edition' not in calls[1][1]
    assert 'OST' in calls[1][1] or 'soundtrack' in calls[1][1]


def test_alternate_search_finds_normalized_title(manager, monkeypatch):
    monkeypatch.setattr(manager, '_own_ytdlp', lambda: None)
    monkeypatch.setattr(manager, 'locate_ytdlp', lambda: Path('stub'))
    monkeypatch.setattr(manager, '_ytdlp_command', lambda: ['stub'])
    monkeypatch.setattr(manager, 'store_data', lambda *a: {'name': 'Fixture™ Complete Edition'})
    monkeypatch.setattr('time.sleep', lambda seconds: None)
    queries = []
    def run(command, **kw):
        queries.append(command[1])
        row = {'webpage_url': 'https://www.youtube.com/watch?v=abcdefghijk', 'title': 'Fixture OST', 'duration': 90}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(row) if len(queries) == 2 else '', stderr='')
    monkeypatch.setattr(manager, 'run', run)
    monkeypatch.setattr(manager, '_download_youtube', lambda *a, **kw: manager.media / '42_theme.m4a')
    assert manager.build_theme(42, 'Fixture', {'theme_music_consent': True})['ok']
    assert len(queries) == 2


def test_pc_localized_reason_and_close_during_preparation():
    import shutil
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required')
    harness = Path(__file__).with_name('r14_music_lifecycle.cjs')
    bundle = MODULES.parent if (MODULES.parent / 'dist/index.js').is_file() else PC.parent.parent / 'continue-public/plugin'
    result = subprocess.run([node, str(harness), str(PC), str(bundle)], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'closed-modal playback PASS' in result.stdout


def test_broken_native_logo_is_not_requested_again_by_continue():
    bundle = MODULES.parent if (MODULES.parent / 'dist/index.js').is_file() else PC.parent.parent / 'continue-public/plugin'
    source = (bundle / 'dist/index.js').read_text(encoding='utf-8')
    anchor = source.index('const src = img?.getAttribute("src")')
    body = source[source.rfind('      const doc = rootRef', 0, anchor):source.index('    }, 200);', anchor)]
    code = """
const assert=require('assert');let picked=null,tries=0;const appid=42,t=0;
const img={complete:true,naturalWidth:0,getAttribute:()=>'/customimages/42_logo.png'};
const rootRef={current:{ownerDocument:{baseURI:'https://steamloopback.host/',querySelector:()=>img}}};
const DFL={appDetailsHeaderClasses:{TitleImageContainer:'native-header'}},uiBusy=()=>false,setSteamLogo=v=>{picked=v;};
function tick(){BODY}
tick();assert.equal(picked,null,'broken Steam logo must not create a second request');
img.complete=false;img.naturalWidth=256;tick();assert.equal(picked,null,'unfinished native load');
img.complete=true;tick();assert.equal(picked,'https://steamloopback.host/customimages/42_logo.png');
console.log('native broken logo PASS');
""".replace('BODY', body)
    result = subprocess.run(['node', '-e', code], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr


def test_deck_closed_settings_still_notify_real_audio_hook():
    source = (MODULES.parent / 'assets/deck_music.js').read_text(encoding='utf-8').split('function DeckMusicSection', 1)[0]
    code = """
const assert=require('assert');let LANGUAGE='en',IS_LINUX=true,useStandaloneMusic;
let ready=false,mounted=true,plays=0;const cleanups=[],sourceListeners=new Set(),settingsListeners=new Set(),DATA='http://fixture/';
const document={visibilityState:'visible',body:{appendChild(){}},addEventListener(){},removeEventListener(){},
createElement(){return {paused:true,play(){this.paused=false;plays++;return Promise.resolve();},pause(){this.paused=true;},removeAttribute(){},remove(){},load(){}};}};
const window={},uiDocument=()=>document,uiBusy=()=>false,continueMusicAllowed=()=>true,seekResume=()=>{},homeLiveRefresh=()=>{};
const useRef=value=>({current:value}),useEffect=fn=>{const c=fn();if(c)cleanups.push(c);};
const nativeTimeout=setTimeout,nativeInterval=setInterval;
setTimeout=(fn,ms)=>nativeTimeout(()=>{mounted=false;ready=true;fn();},1);
setInterval=(fn,ms)=>nativeInterval(fn,1);
async function call(method){if(method==='music_job_status')return ready?{done:true,result:{ok:true}}:{done:false};if(method==='get_music_files')return ready?{'42':'media/42_theme.m4a'}:{};throw Error(method);}
SOURCE
useDeckMusic(42,{standalone:true,theme_music_consent:true,hub_music:true},{});
(async()=>{await resolveDeckMusicJob({pending:true,job:'fixture'},()=>mounted,42);await new Promise(r=>nativeTimeout(r,25));assert(!mounted);assert(plays>0,'Deck audio after settings closed');cleanups.reverse().forEach(f=>f());console.log('Deck closed-modal playback PASS');})().catch(e=>{console.error(e);process.exitCode=1;cleanups.reverse().forEach(f=>f());});
""".replace('SOURCE', source)
    result = subprocess.run(['node', '-e', code], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr


def test_operation_deadline_is_classified_as_timeout():
    from standalone_media import theme_failure_reason
    assert theme_failure_reason(RuntimeError('media job deadline exceeded; retry when ready')) == 'theme_timeout'


def test_encoder_timeout_keeps_reason_and_cleans_staging(manager, monkeypatch):
    import standalone_media as sm
    monkeypatch.setattr(sm.shutil, 'which', lambda name: 'stub-ffmpeg')
    if hasattr(manager, 'tool'):
        monkeypatch.setattr(manager, 'tool', lambda name: 'stub-ffmpeg')
    monkeypatch.setattr(manager, '_probe_duration', lambda source: 40)
    manager.media.mkdir(parents=True)
    source = manager.media / '42_theme.part.m4a'
    source.write_bytes(b'fixture')
    def run(command, **kw):
        Path(command[-1]).write_bytes(b'partial-encode')
        raise subprocess.TimeoutExpired(command, 180)
    monkeypatch.setattr(manager, 'run', run)
    with pytest.raises(RuntimeError, match='theme_timeout'):
        manager._ffmpeg_loop(source, manager.media / '42_theme.m4a', 'light', audio=True)
    assert not list(manager.media.glob('*.encode.part*'))


def test_search_partial_failure_preserves_valid_candidate(manager, monkeypatch):
    monkeypatch.setattr(manager, '_ytdlp_command', lambda: ['stub'])
    row = {'webpage_url': 'https://www.youtube.com/watch?v=abcdefghijk', 'title': 'Fixture Theme', 'duration': 90}
    monkeypatch.setattr(manager, 'run', lambda command, **kw: subprocess.CompletedProcess(command, 1,
        stdout=json.dumps(row), stderr='ERROR: another result: Unable to download webpage: timed out'))
    rows = manager.youtube_candidates('Fixture', audio=True)
    assert len(rows) == 1 and rows[0]['url'] == row['webpage_url']
