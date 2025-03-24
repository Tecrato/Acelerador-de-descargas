# -*- mode: python ; coding: utf-8 -*-

datas = [
        ('C:/Users/Edouard/Documents/fuentes/mononoki Bold Nerd Font Complete Mono.ttf', './Assets/fuentes/'),
        ('C:/Users/Edouard/Documents/fuentes/Symbols.ttf', './Assets/fuentes/'),
        ('./Assets/img/descargas.png','./Assets/img/'),
        ('./Assets/img/descargas.ico','./Assets/img/'),
        ('./extencion.crx','./'),
        ('./cerrar_listener.bat','./'),
        ('./version.txt','./'),
        ('./version','./'),
        ('./instrucciones.txt','./'),
        ('./paginas_no_soportadas.txt','./')
    ]


 # main
a = Analysis(
    ['main.py'],
    datas=datas,
    pathex=[],
    binaries=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
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
    icon= './Assets/img/descargas.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Download Manager',
)
