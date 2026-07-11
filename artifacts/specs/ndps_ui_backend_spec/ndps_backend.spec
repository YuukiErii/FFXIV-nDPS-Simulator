# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\..\\..\\scripts\\run_ndps_simulation.py'],
    pathex=['.\\src\\ffxiv_ndps_simulator'],
    binaries=[],
    datas=[('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\data\\ff14_job_skill_en_cn_map.json', 'data'), ('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\src\\ffxiv_ndps_simulator\\game.txt', 'ffxiv_ndps_simulator'), ('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\src\\ffxiv_ndps_simulator\\stat_fns.txt', 'ffxiv_ndps_simulator'), ('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\src\\ffxiv_ndps_simulator\\damage_cal.txt', 'ffxiv_ndps_simulator')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ndps_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name='ndps_backend',
)
