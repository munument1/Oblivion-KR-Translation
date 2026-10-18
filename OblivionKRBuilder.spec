# OBCJK UTF-8 installer. Release builds do not include legacy translation inventories.
tables = [
    'canonical_translation_v2.csv',
    'canonical_ui_supplement_v1.csv',
    'canonical_book_title_overrides_v1.csv',
    'canonical_locations_v2.csv',
    'menu_gmst_existing_105.csv',
    'menu_gmst_new_821.csv',
]
a = Analysis(['install_obcjk.py'], pathex=[], binaries=[],
    datas=[(name, '.') for name in tables] + [
        ('assets', 'assets'), ('video_subtitles', 'video_subtitles')],
    hiddenimports=['build_vanilla_overlay', 'build_obcjk_release', 'build_obcjk_locations',
                   'master_layout', 'build_script_messages', 'build_shrine_messages', 'build_video_subtitles', 'obcjk_runtime', 'winreg'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='OblivionKRBuilder',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False, upx_exclude=[],
    runtime_tmpdir=None, console=True, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None)
