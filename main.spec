# -*- mode: python ; coding: utf-8 -*-

datas = [
        ('C:/Users/Edouard/Documents/fuentes/mononoki Bold Nerd Font Complete Mono.ttf', './Assets/fuentes/'),
        ('C:/Users/Edouard/Documents/fuentes/Symbols.ttf', './Assets/fuentes/'),
        ('./descargas.png','./'),
        ('./descargas.ico','./'),
        ('./extencion.crx','./')
    ]

hiddenimports = ['werkzeug','flask','werkzeug.serving','flask.cli']

 # main
a = Analysis(
    ['main.py'],
    datas=datas,
    pathex=[],
    binaries=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='Download Manager',
    exclude_binaries=True,
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
    contents_directory='.',
    icon= './descargas.ico'
)

# Downloader

a2 = Analysis(
    ['Downloader.py'],
    datas=datas,
    pathex=[],
    binaries=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz2 = PYZ(a2.pure)

exe2 = EXE(
    pyz2,
    a2.scripts,
    [],
    name='Downloader',
    exclude_binaries=True,
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
    contents_directory='.',
    icon= './descargas.ico'
)

a3 = Analysis(
    ['listener.py'],
    datas=datas,
    pathex=[],
    binaries=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz3 = PYZ(a3.pure)

exe3 = EXE(
    pyz3,
    a3.scripts,
    [],
    name='listener',
    exclude_binaries=True,
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
    contents_directory='.',
    icon= './descargas.ico'
)

build_options = {
    'build': {
        'optimize': 2,
        'include_msvcr': False,
    },
}
coll = COLLECT(
    exe,
    exe2,
    exe3,
    a.binaries,
    a2.binaries,
    a3.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Download Manager',
)
