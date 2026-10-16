import shutil
import subprocess
from pathlib import Path
import pytest

def test_native_pc_controls_and_achievement_history():
    node=shutil.which('node')
    if not node:
        pytest.skip('Node is required for the frontend VM')
    result=subprocess.run([node,str(Path(__file__).with_name('frontend_controls.cjs'))],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
