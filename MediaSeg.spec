# -*- mode: python ; coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.getcwd())
from mediaseg_version import get_public_version


datas = [
    ('assets', 'assets'),
    ('THIRD_PARTY_LICENSES.md', '.'),
]

a = Analysis(
    ['mediaseg_gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.QtPdf',
        'PySide6.QtQml',
        'PySide6.QtQmlMeta',
        'PySide6.QtQmlModels',
        'PySide6.QtQmlWorkerScript',
        'PySide6.QtQuick',
        'PySide6.QtVirtualKeyboard',
        'PySide6.QtVirtualKeyboardQml',
        'PySide6.QtOpenGL',
        'PySide6.QtQuickWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
    ],
    noarchive=False,
    optimize=0,
)

# Explicitly filter out unnecessary Qt frameworks from binaries and datas
excluded_frameworks = [
    'QtPdf', 'QtQml', 'QtQuick', 'QtVirtualKeyboard', 'QtOpenGL',
    'QtWebEngineCore', 'QtWebEngineWidgets', 'QtQuickWidgets'
]

filtered_binaries = []
for name, path, type in a.binaries:
    exclude = False
    for fw in excluded_frameworks:
        if fw in name or fw in path:
            exclude = True
            break
    if not exclude:
        filtered_binaries.append((name, path, type))
a.binaries = filtered_binaries

filtered_datas = []
for name, path, type in a.datas:
    exclude = False
    for fw in excluded_frameworks:
        if fw in name or fw in path:
            exclude = True
            break
    if not exclude:
        filtered_datas.append((name, path, type))
a.datas = filtered_datas

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MediaSeg',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MediaSeg',
)
app = BUNDLE(
    coll,
    name='MediaSeg.app',
    version=get_public_version(),
    icon='assets/app_icon.icns' if os.path.exists('assets/app_icon.icns') else None,
    bundle_identifier='com.jadore.mediaseg',
)
