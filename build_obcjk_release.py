"""Build the OBCJK UTF-8 release directly from the original game files.

The release path uses only audited Unicode/UTF-8 canonical data. It does not
create or consume a legacy Korean intermediate plugin.
"""
from __future__ import annotations

import configparser
import csv
import json
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from build_obcjk_ui import build as build_ui
from book_title_overrides import apply_book_title_overrides
from build_vanilla_overlay import (
    HERE, MASTER, OFFICIAL, PRINTF_PATTERN, load_translations, patch_plugin,
    sha256_file, structure_signature,
)
from build_video_subtitles import build_videos
from master_layout import apply_layout
from build_script_messages import build as build_script_messages
from build_shrine_messages import build as build_shrine_messages
from obcjk_runtime import bundle_manifest as runtime_manifest, install_runtime

ORIGINAL_FONT_SETTINGS = (
    '[Fonts]\n'
    'SFontFile_1=Data\\Fonts\\Kingthings_Regular.fnt\n'
    'SFontFile_2=Data\\Fonts\\Kingthings_Shadowed.fnt\n'
    'SFontFile_3=Data\\Fonts\\Tahoma_Bold_Small.fnt\n'
    'SFontFile_4=Data\\Fonts\\Daedric_Font.fnt\n'
    'SFontFile_5=Data\\Fonts\\Handwritten.fnt\n'
)


def default_ini():
    """Return the Korean preset with the verified xOBSE UTF-8 correction enabled."""
    return (HERE / 'assets/obcjk_fonts/obCJK.ini').read_bytes()


def load_utf8_menu_gmsts(path: Path):
    result = []
    seen = set()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for line, row in enumerate(csv.DictReader(stream), 2):
            fid = int(row['formid'], 16)
            key = row['edid'].encode('ascii')
            english = row['english']
            korean_text = row['korean']
            korean = korean_text.encode('utf-8') + b'\0'
            if not 0 < fid <= 0x00FFFFFF:
                raise ValueError(f'invalid Oblivion.esm menu GMST file slot at line {line}: {fid:08X}')
            if fid in seen:
                raise ValueError(f'duplicate menu GMST at line {line}: {fid:08X}')
            if PRINTF_PATTERN.findall(english) != PRINTF_PATTERN.findall(korean_text):
                raise ValueError(f'menu GMST placeholder mismatch at line {line}')
            result.append((fid, key + b'\0', english.encode('cp1252') + b'\0', korean))
            seen.add(fid)
    return tuple(result)


def build(args):
    output = args.output.resolve()
    source = args.data_dir.resolve()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('Output must be separate from original Data')
    if output.exists() and any(output.iterdir()):
        raise ValueError('obCJK output folder must be empty; keep variants separate')
    if args.ini:
        raise ValueError('--ini is not used by the OBCJK build; use profile-local original fonts')

    ini_bytes = args.obcjk_ini.read_bytes() if args.obcjk_ini else default_ini()
    config = configparser.ConfigParser(interpolation=None)
    config.read_string(ini_bytes.decode('utf-8-sig'))
    if config.get('obCJK', 'ActiveCodePage', fallback='').upper() != 'UTF8':
        raise ValueError('obCJK INI must explicitly select ActiveCodePage = UTF8')
    if not (source / MASTER).is_file():
        raise FileNotFoundError(source / MASTER)

    runtime_manifest()

    supplement = HERE / 'canonical_ui_supplement_v1.csv'
    extra_tables = (supplement, *(path.resolve() for path in args.extra_csv))
    translations = load_translations(
        args.csv.resolve(), extra_tables,
        encoded_column='obcjk_utf8_hex')
    apply_book_title_overrides(translations, HERE / 'canonical_book_title_overrides_v1.csv')
    menu_gmsts = load_utf8_menu_gmsts(HERE / 'menu_gmst_new_821.csv')
    menu_formids = frozenset(item[0] for item in menu_gmsts)

    output.mkdir(parents=True, exist_ok=True)
    audit = []
    reports = {}

    with tempfile.TemporaryDirectory(prefix='obcjk-direct-') as temporary, \
            tempfile.TemporaryDirectory(prefix='obcjk-location-tables-') as table_temp:
        temp = Path(temporary)
        stage = temp / 'stage'
        locations = temp / 'locations'
        stage.mkdir()

        for name in OFFICIAL:
            src = source / name
            if not src.is_file():
                continue
            counts = Counter()
            target = stage / name
            patch_plugin(
                src, target, name, translations, counts, audit,
                menu_gmsts if name == MASTER else (),
                utf8_untranslated=True,
            )
            if counts['applied'] == 0 and counts['utf8_untranslated'] == 0 and counts['new_menu_gmst'] == 0:
                target.unlink(missing_ok=True)
                print(f'{name}: unchanged; omitted')
                continue
            before = structure_signature(src)
            after = structure_signature(target, menu_formids if name == MASTER else frozenset())
            if before != after:
                raise ValueError(f'{name}: record structure or compiled script changed')
            if name == MASTER and counts['new_menu_gmst'] != len(menu_gmsts):
                raise ValueError('unexpected menu GMST count')
            reports[name] = {
                'source_sha256': sha256_file(src),
                'applied_strings': counts['applied'],
                'utf8_untranslated': counts['utf8_untranslated'],
                'changed_records': counts['changed_records'],
                'ambiguous': counts['ambiguous'],
                'new_menu_gmst': counts['new_menu_gmst'],
                'structure': before,
                'direct_utf8_sha256': sha256_file(target),
            }
            print(f"{name}: {counts['applied']} translated strings in {counts['changed_records']} records")

        # Location canonical is Unicode-native and applied directly to the UTF-8 stage.
        tables = Path(table_temp)
        shutil.copyfile(HERE / 'canonical_locations_v2.csv', tables / 'canonical_locations_v2.csv')
        from build_obcjk_locations import build as build_locations
        location_reports = build_locations([stage], tables, locations)

        for name in reports:
            src = locations / name if (locations / name).is_file() else stage / name
            shutil.copyfile(src, output / name)
            reports[name]['location_changes'] = len(location_reports.get(name, {}).get('changes', []))
            reports[name]['output_sha256'] = sha256_file(output / name)

        # Preserve the captured native Oblivion.esm record ordering/layout.
        master = output / MASTER
        ordered = temp / 'Oblivion.ordered.esm'
        native_report = apply_layout(
            master, ordered, HERE / 'assets/oblivion_native_layout.json.gz',
            source_sha256=sha256_file(source / MASTER))
        copied = master.with_suffix('.esm.native-building')
        shutil.copyfile(ordered, copied)
        if sha256_file(copied) != native_report['output_sha256']:
            raise ValueError('Native layout copy checksum mismatch')
        copied.replace(master)
        reports[MASTER]['before_native_layout_sha256'] = reports[MASTER]['output_sha256']
        reports[MASTER]['output_sha256'] = native_report['output_sha256']
        reports[MASTER]['native_master_layout'] = native_report

        # Apply the five in-game-verified sewer-exit labels after the strict
        # native layout check. The pinned script and byte-for-byte readback
        # allow only fixed-length literal payload changes, preserving offsets.
        script_output = temp / 'Oblivion.script-messages.esm'
        script_report = build_script_messages(master, script_output)
        shutil.copyfile(script_output, copied)
        if sha256_file(copied) != script_report['output_sha256']:
            raise ValueError('Script-message copy checksum mismatch')
        copied.replace(master)
        reports[MASTER]['script_messages'] = script_report
        reports[MASTER]['output_sha256'] = script_report['output_sha256']

        # Both the base scripts and Knights overrides must be translated.
        for name in (MASTER, 'Knights.esp'):
            target = output / name
            if not target.is_file():
                continue
            shrine_output = temp / (name + '.shrine-messages')
            shrine_report = build_shrine_messages(target, shrine_output, name)
            copied_shrine = target.with_suffix(target.suffix + '.shrine-building')
            shutil.copyfile(shrine_output, copied_shrine)
            if sha256_file(copied_shrine) != shrine_report['output_sha256']:
                raise ValueError('Wayshrine message copy checksum mismatch')
            copied_shrine.replace(target)
            reports[name]['shrine_messages'] = shrine_report
            reports[name]['output_sha256'] = shrine_report['output_sha256']

        shutil.copyfile(locations / 'location_validation.json', output / 'location_validation.json')

    ui_report = build_ui(HERE / 'assets/menus/strings.xml', output / 'menus/strings.xml')

    videos = {}
    if args.video_subtitles != 'off':
        videos = build_videos(
            source, output, HERE / 'video_subtitles',
            required=args.video_subtitles == 'required')

    (output / 'FONT_SETTINGS.txt').write_text(ORIGINAL_FONT_SETTINGS, encoding='utf-8')
    ini_path = output / 'OBSE/plugins/obCJK/obCJK.ini'
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    ini_path.write_bytes(ini_bytes)
    runtime_report = install_runtime(output)

    validation = {
        name: {
            'source_sha256': report['source_sha256'],
            'output_sha256': report['output_sha256'],
            'structure': report['structure'],
            'location_changes': report['location_changes'],
            **({'native_master_layout': report['native_master_layout']} if 'native_master_layout' in report else {}),
            **({'script_messages': report['script_messages']} if 'script_messages' in report else {}),
            **({'shrine_messages': report['shrine_messages']} if 'shrine_messages' in report else {}),
        }
        for name, report in reports.items()
    }
    (output / 'obcjk_validation.json').write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    translation_audit = {
        'files': reports,
        'applied': audit,
        'videos': videos,
        'text_backend': 'obcjk-direct-utf8',
        'legacy_intermediate': False,
        'obcjk_runtime': runtime_report,
        'utf8_validation': 'obcjk_validation.json',
        'location_validation': 'location_validation.json',
        'menu_xml': ui_report,
        'obcjk_ini_sha256': sha256_file(ini_path),
        'runtime_verified': False,
        'korean_locations': bool(getattr(args, 'korean_locations', False)),
    }
    (output / 'translation_audit.json').write_text(
        json.dumps(translation_audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0
