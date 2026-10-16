import hashlib,json
from pathlib import Path
from public_game_assets import validate_manifest,seed_game_icons
ROOT=Path(__file__).resolve().parents[2]
PACK=ROOT/'pc/assets/game_icons'
def test_public_portraits_and_exact_owner_raven(tmp_path):
    m=validate_manifest(PACK)
    assert len(m)==25
    for name in ['Sam','Mike','Jessica','Emily','Matt','Ashley','Chris','Josh']:
        assert (PACK/m['2172010']['person:'+name]).is_file()
    raven=PACK/m['2322010']['raven']
    assert hashlib.sha256(raven.read_bytes()).hexdigest()=='70a4e5f7005c1c3684f228ea5c75171e67ef2933de8f37bdb9fccdedf1eb2750'
    seed_game_icons(PACK,tmp_path)
    assert len(json.loads((tmp_path/'icons/manifest.json').read_text(encoding='utf-8')))==25
