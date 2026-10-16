import importlib.util
import sys
from pathlib import Path

def subject():
    spec = importlib.util.spec_from_file_location('pc_theme_injector', Path(__file__).parents[2] / 'pc/public_theme_cdp.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_only_native_bp_windows_are_styled():
    mod = subject()
    assert mod.window_kind('SP') == 'bp'
    assert mod.window_kind('Steam Big Picture Mode') == 'bp'
    assert mod.window_kind('Режим Big Picture') == 'bp'
    assert mod.window_kind('MainMenu_1') == 'menu'
    assert mod.window_kind('QuickAccess_3') == 'qam'
    for name in ('SharedJSContext', 'Photoshop', 'GameHub browser', 'MainMenu_evil browser'):
        assert mod.window_kind(name) is None

def test_cdp_urls_cannot_leave_steam_loopback():
    mod = subject()
    assert mod.local_ws('ws://127.0.0.1:8080/devtools/page/1', 8080)
    for url in ('ws://evil.invalid:8080/x','ws://127.0.0.1:8081/x','ws://user@127.0.0.1:8080/x','wss://127.0.0.1:8080/x'):
        assert not mod.local_ws(url, 8080)

def test_style_expression_keeps_other_plugins_and_native_styles():
    mod = subject()
    source = mod.style_expression('a{color:red}', 'fixture')
    assert "continue-pc-themes" in source
    assert "gh-themes" not in source
    assert 'remove' not in source
    assert 'a{color:red}' in source
