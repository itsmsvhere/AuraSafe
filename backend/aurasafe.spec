# -*- mode: python ; coding: utf-8 -*-
# AuraSafe PyInstaller spec
# Run: pyinstaller aurasafe.spec

import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('templates', 'templates'),
    ],
    hiddenimports=[
        'flask', 'flask_cors', 'psutil',
        'tkinter', 'tkinter.ttk',
        'sqlite3', 'threading', 'queue',
        'win32gui', 'win32process',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='AuraSafe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # No terminal window
    icon=None,           # Add icon path here if available
)
