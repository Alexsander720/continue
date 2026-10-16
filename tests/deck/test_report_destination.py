from pathlib import Path
import importlib.util
import zipfile


def test_report_uses_redirected_known_folder(tmp_path,monkeypatch):
    source=Path(__file__).resolve().parents[2]/'plugin/py_modules/tester_report.py'
    spec=importlib.util.spec_from_file_location('public_report_destination',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    redirected=tmp_path/'redirected desktop';redirected.mkdir()
    monkeypatch.setattr(module,'windows_known_folder',lambda _:redirected)
    monkeypatch.setattr(module,'home_dir',lambda:tmp_path/'missing-home')
    destination=module.save('{"fixture":true}')
    assert destination.parent==redirected
    with zipfile.ZipFile(destination) as archive:assert archive.read('report.json')==b'{"fixture":true}'
