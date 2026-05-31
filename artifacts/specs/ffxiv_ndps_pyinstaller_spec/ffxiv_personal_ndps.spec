# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('ama_xiv_combat_sim')


a = Analysis(
    ['..\\..\\..\\src\\ffxiv_ndps_simulator\\sim.py'],
    pathex=['.\\src\\ffxiv_ndps_simulator'],
    binaries=[],
    datas=[('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\data\\ff14_job_skill_en_cn_map.json', 'data'), ('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\examples\\skill_lines', 'examples/skill_lines'), ('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\src\\ffxiv_ndps_simulator\\game.txt', 'ffxiv_ndps_simulator'), ('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\src\\ffxiv_ndps_simulator\\stat_fns.txt', 'ffxiv_ndps_simulator'), ('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\src\\ffxiv_ndps_simulator\\damage_cal.txt', 'ffxiv_ndps_simulator'), ('C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\src\\ffxiv_ndps_simulator\\ffxiv_ndps.ico', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ffxiv_personal_ndps',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\Mahiru\\Desktop\\FFXIV\\SIM\\src\\ffxiv_ndps_simulator\\ffxiv_ndps.ico'],
)
