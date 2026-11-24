"""Public visual-only compatibility: no owner files/processes, bridge or text changes."""
import importlib.util
import json
from pathlib import Path
import time
import threading
from types import SimpleNamespace
import pytest

from playwright.sync_api import sync_playwright
from test_installer import layout, run_script, read_json

ROOT = Path(__file__).resolve().parents[2]


def module():
    path = ROOT / 'pc/public_owner_theme.py'
    assert path.is_file(), 'The public visual-only service is missing'
    spec = importlib.util.spec_from_file_location('owner_theme_under_test', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_installer_records_mode_and_preserves_it_on_repair(layout):
    result = run_script(layout, 'install.ps1', '-AcceptDebugPort', '-OwnerThemeOnly')
    assert result.returncode == 0, result.stdout + result.stderr
    assert read_json(layout['root'] / 'install.json')['mode'] == 'owner-theme'
    result = run_script(layout, 'install.ps1', '-AcceptDebugPort')
    assert result.returncode == 0, result.stdout + result.stderr
    assert read_json(layout['root'] / 'install.json')['mode'] == 'owner-theme'
    result = run_script(layout, 'uninstall.ps1', '-RemoveData', installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not layout['root'].exists()


def test_only_packaged_game_assets_and_exact_label_associations(tmp_path):
    mod = module()
    payload = mod.payload(ROOT, '108710')
    assert payload['rail'].startswith('data:image/svg+xml;base64,')
    assert payload['icons']['Достижения'] == payload['icons']['Achievements']
    assert 'unknown invented label' not in payload['icons']
    assert mod.payload(ROOT, '../108710') is None
    assert mod.payload(ROOT, '1') is None
    # A malicious manifest may not read outside the packaged assets.
    assets = tmp_path / 'pc/assets'
    (assets / 'game_icons').mkdir(parents=True)
    (assets / 'game_styles.json').write_text(json.dumps({'108710': {'rail': '../secret.png'}}))
    (assets / 'game_icons/manifest.json').write_text(json.dumps({'108710': {'achievements': '../secret.png'}}))
    (assets.parent / 'secret.png').write_bytes(b'PRIVATE')
    bad = mod.payload(tmp_path, '108710')
    assert not bad['rail'] and not bad['icons']


def init(page):
    page.set_viewport_size({'width': 1280, 'height': 800})
    page.set_content('''<style>.gh-root{position:relative;width:1280px;height:534px}
    .gh-panel{position:absolute;left:36px;top:40px;width:440px;transform:scale(.8);transform-origin:0 0}
    .gh-factbar{position:absolute;top:420px}.gh-rule{position:absolute;top:2px;bottom:4px;width:2px}
    </style><div class="gh-root"><div class="gh-panel"><div class="gh-rule"></div>
    <img class="gh-logo" width="200" height="100"><div class="gh-title">Original title</div>
    <div class="gh-detail">Original description</div></div><div class="gh-factbar">
    <div class="gh-fact"><svg class="gh-glyph"><path d="M0 0"></path></svg><div><div class="gh-fl">Достижения</div><div>1 / 10</div></div></div>
    <div class="gh-fact"><svg class="gh-glyph"></svg><div><div class="gh-fl">Unknown fact</div></div></div>
    </div></div>''')
    page.evaluate('''()=>{window.__ghPC={ver:'fixture-owner',reply:()=>{},unload:()=>{throw Error('must never unload owner')}};
      window.__ghBridge=()=>{};window.ownerBefore=window.__ghPC;window.bridgeBefore=window.__ghBridge;
      window.fixturePath='/library/app/108710';window.SteamUIStore={WindowStore:{GamepadUIMainWindowInstance:{
        BrowserWindow:{document},m_history:{location:{get pathname(){return window.fixturePath}}}}}};
      window.beforeHTML=document.querySelector('.gh-root').outerHTML;}''')


def test_renderer_ratio_lifecycle_owner_identity_and_exact_dom_restore():
    mod = module()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            init(page)
            code = mod.script(ROOT, mod.payload(ROOT, '108710'), 'test-version', lease_ms=2500)
            page.evaluate(code)
            page.wait_for_function('document.querySelector(".continue-owner-rail")?.naturalHeight>0')
            assert page.evaluate('window.__ghPC===ownerBefore && window.__ghBridge===bridgeBefore')
            assert page.locator('.continue-owner-rail').count() == 1
            assert page.locator('.continue-owner-icon').count() == 1
            assert page.locator('.gh-fact svg').count() == 2  # originals remain the very same nodes
            page.evaluate('document.querySelector(".continue-owner-icon").remove()')
            page.wait_for_function('document.querySelectorAll(".continue-owner-icon").length===1', timeout=1500)
            page.evaluate('document.querySelector(".gh-fact svg").classList.remove("continue-owner-original")')
            page.wait_for_function('document.querySelector(".gh-fact svg").classList.contains("continue-owner-original")', timeout=1500)
            # Repeated install is idempotent; text length/logo/transform cannot change the aspect.
            for words in [0, 80, 900]:
                page.evaluate('(n)=>{document.querySelector(".gh-detail").textContent="word ".repeat(n);document.querySelector(".gh-logo").height=n?500:30}', words)
                page.evaluate(code)
                r = page.evaluate('''()=>{const x=document.querySelector('.continue-owner-rail'),r=x.getBoundingClientRect();
                  return {count:document.querySelectorAll('.continue-owner-rail').length,error:Math.abs(r.width/r.height/(x.naturalWidth/x.naturalHeight)-1)*100,
                    bottom:r.bottom,limit:document.querySelector('.gh-factbar').getBoundingClientRect().top}}''')
                assert r['count'] == 1 and r['error'] <= 2 and r['bottom'] < r['limit'], r
            # Owned nodes are removed on navigation, and later injection restores the new card.
            page.evaluate("window.fixturePath='/library/app/1'")
            page.wait_for_function('!window.__continueOwnerTheme')
            assert page.locator('.continue-owner-rail').count() == 0
            page.evaluate("window.fixturePath='/library/app/108710'")
            page.evaluate(code)
            page.evaluate('window.__ghPC={ver:"new-owner"}')
            page.wait_for_function('!window.__continueOwnerTheme')
            assert page.locator('.continue-owner-icon').count() == 0
            # Restore full baseline, then verify exact DOM restoration and heartbeat lease expiry.
            init(page)
            page.evaluate(code)
            page.evaluate('window.__continueOwnerTheme.unload()')
            assert page.evaluate('document.querySelector(".gh-root").outerHTML===beforeHTML')
            assert page.evaluate('window.__ghPC===ownerBefore && window.__ghBridge===bridgeBefore')
            page.evaluate(mod.script(ROOT, mod.payload(ROOT, '108710'), 'lease-test', lease_ms=150))
            page.wait_for_function('!window.__continueOwnerTheme')
            assert page.evaluate('document.querySelector(".gh-root").outerHTML===beforeHTML')
            # React replacing the entire root cannot leak owned nodes into the new root.
            page.evaluate(code)
            page.evaluate('document.querySelector(".gh-root").outerHTML=beforeHTML')
            page.wait_for_function('!window.__continueOwnerTheme')
            page.evaluate(code)
            assert page.locator('.continue-owner-rail').count() == 1
            page.evaluate('window.__continueOwnerTheme.unload()')
            assert page.evaluate('document.querySelector(".gh-root").outerHTML===beforeHTML')
        finally:
            browser.close()


def test_service_mode_cannot_construct_backend_bind_media_or_register_bridge(tmp_path, monkeypatch):
    mod = module()
    service_path = ROOT / 'pc/gamehub_bp.py'
    spec = importlib.util.spec_from_file_location('owner_theme_service_test', service_path)
    service = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(service)
    (tmp_path / 'install.json').write_text('{"mode":"owner-theme"}')
    config = SimpleNamespace(root=tmp_path, app=ROOT, ready=tmp_path / 'service_ready.json', token='fixture-token', version='0.1.5', cdp_port=1)
    stop = threading.Event()
    calls, receipts = [], []
    class FakeSession:
        alive = True
        def __init__(self, url, backend, pool):
            assert backend is None and pool is None
            calls.append(('connect', url))
        def evaluate(self, expression, **kwargs):
            calls.append(('evaluate', expression[:80]))
            if expression == mod.STATE_JS:
                return {'app': '108710', 'ready': True, 'active': None, 'games': 0}
            stop.set()
            return True
        def close(self): self.alive = False
    def forbidden(*args, **kwargs): raise AssertionError('Full backend/media path must never run')
    # The mode branch imports by its normal production module name.
    import sys
    monkeypatch.setitem(sys.modules, 'public_owner_theme', mod)
    monkeypatch.setattr(service, 'Backend', forbidden)
    monkeypatch.setattr(service, 'media_server', forbidden)
    monkeypatch.setattr(service, 'Session', FakeSession)
    monkeypatch.setattr(service, 'shared_ctx_ws', lambda _: 'ws://fixture')
    monkeypatch.setattr(service, 'write_json', lambda p, v: receipts.append((p, v)))
    assert service._serve_locked(config, stop) == 0
    ready = next(v for p, v in receipts if p == config.ready)
    assert ready['mode'] == 'owner-theme' and ready['media_port'] != 8793
    assert any('unload' in expression for kind, expression in calls if kind == 'evaluate')
    assert not config.ready.exists()


def test_updater_preserves_visual_only_mode(tmp_path):
    from public_update import PublicUpdater
    root = tmp_path / 'profile'
    root.mkdir()
    (root / 'install.json').write_text('{"version":"0.1.4","mode":"owner-theme"}')
    updater = PublicUpdater(root)
    updater._set_installed_version('0.1.5')
    assert json.loads((root / 'install.json').read_text())['mode'] == 'owner-theme'


def test_status_checks_its_control_socket_and_never_asks_to_close_personal_hub(layout):
    result = run_script(layout, 'install.ps1', '-AcceptDebugPort', '-OwnerThemeOnly')
    assert result.returncode == 0, result.stdout + result.stderr
    state_file = layout['profile'] / 'fixture_state.json'
    state = read_json(state_file)
    state.update(steam_running=True, cdp='steam', media='other')
    state_file.write_text(json.dumps(state))
    (layout['root'] / 'service_ready.json').write_text('{"media_port":58000,"mode":"owner-theme"}')
    result = run_script(layout, 'status.ps1', '-Json', installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    status = json.loads(result.stdout)
    assert status['mode'] == 'owner-theme' and status['control_port'] == 58000
    assert '8793' not in status['hint'] and 'Close that program' not in status['hint']


@pytest.mark.parametrize('interrupted', [False, True])
def test_mode_survives_retained_profile_and_interrupted_removal_repair(layout, interrupted):
    if interrupted:
        script = layout['package'] / 'pc/uninstall.ps1'
        source = script.read_text('utf-8')
        source = source.replace('Remove-ContinuePath $context.Manifest', 'Remove-ContinuePath $context.Manifest\n    [Environment]::Exit(86)')
        script.write_text(source, 'utf-8')
    result = run_script(layout, 'install.ps1', '-AcceptDebugPort', '-OwnerThemeOnly')
    assert result.returncode == 0, result.stdout + result.stderr
    result = run_script(layout, 'uninstall.ps1', '-KeepData', installed=True)
    assert result.returncode == (86 if interrupted else 0), result.stdout + result.stderr
    assert not (layout['root'] / 'install.json').exists()
    recovery = read_json(layout['root'] / 'uninstall-recovery.json')
    assert recovery['owner']['mode'] == 'owner-theme'
    result = run_script(layout, 'install.ps1', '-AcceptDebugPort')
    assert result.returncode == 0, result.stdout + result.stderr
    assert read_json(layout['root'] / 'install.json')['mode'] == 'owner-theme'


def test_reinjection_revision_covers_package_and_asset_bytes(tmp_path):
    mod = module()
    (tmp_path / 'pc/assets/rails').mkdir(parents=True)
    (tmp_path / 'pc/bp_owner_theme.js').write_text('// same renderer')
    (tmp_path / 'pc/assets/game_styles.json').write_text('{"108710":{"rail":"rails/108710.png"}}')
    png = tmp_path / 'pc/assets/rails/108710.png'
    png.write_bytes((ROOT / 'pc/assets/rails/108710.png').read_bytes())
    first = mod.revision(tmp_path, '108710', '0.1.5')
    assert first != mod.revision(tmp_path, '108710', '0.1.6')
    png.write_bytes(png.read_bytes() + b'changed asset')
    # A service restart reloads packaged assets; no runtime cache mutation is needed.
    restarted = module()
    assert first != restarted.revision(tmp_path, '108710', '0.1.5')


def test_death_stranding_labels_match_the_packaged_stable_icon_ids():
    mod = module()
    for app in ['1850570', '3280350']:
        value = mod.payload(ROOT, app)
        for label in ['Заказ', 'Order', 'Замовлення']:
            assert value['icons'][label] == value['icons']['order_id']
        assert value['icons']['Название заказа'] == value['icons']['order_name']
        assert value['icons']['Тип сохранения'] == value['icons']['save_slot_type']
    assert mod.payload(ROOT, '3280350')['icons']['Эпизод'] == mod.payload(ROOT, '3280350')['icons']['episode_number']
