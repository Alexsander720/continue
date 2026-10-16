"""Stable task entrypoint, installed outside the replaceable app directory."""
from pathlib import Path
import importlib.util
import os
import runpy
import subprocess
import sys


def main():
    root=Path(__file__).resolve().parent
    if (root/'install-transaction.json').exists():
        command=[os.path.join(os.environ['SystemRoot'],'System32/WindowsPowerShell/v1.0/powershell.exe'),
                 '-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(root/'recover-install.ps1')]
        result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=120)
        if result.returncode:return result.returncode
    if (root/'update-journal.json').exists():
        helper=root/'update-helper.py'
        if not helper.is_file() or helper.is_symlink():raise RuntimeError('Update recovery helper is missing')
        spec=importlib.util.spec_from_file_location('continue_update_recovery',helper)
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        updater=module.PublicUpdater(root)
        updater.recover()
        if updater._child is not None:return 0
    entry=root/'app/pc/gamehub_bp.py'
    sys.path.insert(0,str(entry.parent));sys.argv=[str(entry),*sys.argv[1:]]
    runpy.run_path(str(entry),run_name='__main__')
    return 0


if __name__=='__main__':raise SystemExit(main())
