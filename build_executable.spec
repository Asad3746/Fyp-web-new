# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['home.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('logo.png', '.'),
        ('back.png', '.'),
        ('next.png', '.'),
        ('previous.png', '.'),
        ('face_cascade.xml', '.'),
        ('face_samples', 'face_samples'),
        # profile_pics is created at runtime, don't bundle it
    ],
    hiddenimports=[
        'cv2',
        'PIL',
        'tkinter',
        'facerec',
        'register',
        'dbHandler',
        'numpy',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CriminalDetectionSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can add an .ico file here if you have one
)
