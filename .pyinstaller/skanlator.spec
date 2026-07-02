# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

current_spec_dir = os.path.abspath(SPECPATH)
project_root = os.path.dirname(current_spec_dir)

app_src = os.path.join(project_root, "app", "src")
core_src = os.path.join(project_root, "core", "src")

datas = []
binaries = []
datas += collect_data_files('rapidocr')
binaries += collect_dynamic_libs('llama_cpp')

datas += [(os.path.join(project_root, 'assets', 'skanlator.ico'), '.')]

sys.path.insert(0, app_src)
sys.path.insert(0, core_src)

a = Analysis(
    [os.path.join(current_spec_dir, 'run.py')],
    pathex=[app_src, core_src],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'app',
        'core',
        'core.capture.mss',
        'core.ocr.rapid',
        'core.translation.llama_cpp',
        'imagehash',
        'numpy',
        'PIL',
        'PySide6',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Skanlator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, 'assets', 'skanlator.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Skanlator',
)
