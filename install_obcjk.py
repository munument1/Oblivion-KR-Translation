"""기존 번역 빌더에 obCJK 설정과 OFL 글꼴 설치를 더합니다."""
from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from obcjk_fonts import ROOT, bundle_manifest, install_fonts, preset_ini


def documents_ini():
    """Use the same Documents/My Games path as the original installer."""
    buffer = ctypes.create_unicode_buffer(32768)
    if ctypes.WinDLL('shell32').SHGetFolderPathW(None, 5, None, 0, buffer) != 0:
        raise OSError('문서 폴더를 찾을 수 없습니다.')
    return Path(buffer.value) / 'My Games/Oblivion/Oblivion.ini'


def update_existing_ini(path, font_settings, *, dry_run=False):
    """Change only font lines, preserving all other bytes and the original backup."""
    path = Path(path).resolve()
    if not path.is_file() or path.suffix.lower() != '.ini':
        raise ValueError('기존 Oblivion.ini 파일을 지정하세요.')
    raw = path.read_bytes()
    replacements = {line.split('=', 1)[0].lower().encode('ascii'): line.encode('ascii')
                    for line in font_settings.splitlines() if line.startswith('SFontFile_')}
    found = set()
    section = b''
    lines = raw.splitlines(keepends=True)
    for index, line in enumerate(lines):
        stripped = line.removeprefix(b'\xef\xbb\xbf').strip()
        if stripped.startswith(b'['):
            section = stripped.lower()
        if section != b'[fonts]' or b'=' not in stripped:
            continue
        key = stripped.split(b'=', 1)[0].strip().lower()
        if key in replacements:
            newline = b'\r\n' if line.endswith(b'\r\n') else b'\n' if line.endswith(b'\n') else b''
            bom = b'\xef\xbb\xbf' if line.startswith(b'\xef\xbb\xbf') else b''
            lines[index] = bom + replacements[key] + newline
            found.add(key)
    if found != set(replacements):
        raise ValueError('Oblivion.ini is missing one or more SFontFile settings')
    changed = b''.join(lines)
    if dry_run:
        return changed != raw
    if changed == raw:
        return None
    backup = path.with_name(path.name + '.before_oblivion_kr.bak')
    if not backup.exists():
        with backup.open('xb') as stream:
            stream.write(raw)
    temporary = path.with_name(path.name + '.obcjk-fonts.building')
    with temporary.open('xb') as stream:
        stream.write(changed)
    temporary.replace(path)
    return str(backup)

def main():
    # Frozen Python ignores PYTHONIOENCODING. Keep the console's encoding,
    # but do not abort installation when its code page cannot print Korean.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    # The frozen builder invokes itself for the legacy intermediate conversion.
    if '--text-backend' in sys.argv:
        from build_vanilla_overlay import main as builder_main
        return builder_main()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, help='원본 게임 Data 폴더')
    parser.add_argument('--output', type=Path, help='MO2에 넣을 번역 모드 출력 폴더')
    parser.add_argument('--ini', type=Path, help='기존 Oblivion.ini; 생략하면 문서 폴더에서 자동 검색')
    parser.add_argument('--fonts-only', action='store_true', help='번역 데이터 생성 없이 글꼴만 설치')
    parser.add_argument('--diagnose-display', action='store_true', help='제보된 글자 깨짐과 게이트 레코드를 읽기 전용 검사')
    parser.add_argument('--load-order', type=Path, help='진단용 활성 플러그인 목록(로드 순서); 생략 시 덮어쓰기 우선순위 미판정')
    parser.add_argument('--video-subtitles', choices=('auto', 'required', 'off'), default='off',
                        help='인트로·엔딩 자막 영상: 기본 off. auto/required는 이미 설치된 FFmpeg·ffprobe·RAD만 사용')
    args = parser.parse_args()
    if args.diagnose_display:
        if not args.data_dir or args.output or args.fonts_only or args.ini:
            parser.error('--diagnose-display는 --data-dir와 선택적인 --load-order만 사용합니다.')
        from diagnose_display import diagnose
        print(json.dumps(diagnose(args.data_dir,args.load_order),ensure_ascii=False,indent=2))
        return 0
    if args.load_order:
        parser.error('--load-order는 --diagnose-display와 함께 사용하세요.')
    bundle_manifest()
    if args.fonts_only:
        if args.data_dir or args.output or args.ini:
            parser.error('--fonts-only와 --data-dir/--output/--ini는 함께 사용할 수 없습니다.')
        install_fonts()
    else:
        if not args.data_dir or not args.output:
            parser.error('--data-dir와 --output을 지정하세요.')
        from build_obcjk_release import build, ORIGINAL_FONT_SETTINGS
        output = args.output.resolve()
        report_path = output.parent / (output.name + '.validation.json')
        if report_path.exists():
            raise FileExistsError(f'기존 검증 보고서가 있습니다. 새 출력 폴더를 사용하세요: {report_path}')
        ini = args.ini or documents_ini()
        if ini.is_file():
            update_existing_ini(ini, ORIGINAL_FONT_SETTINGS, dry_run=True)
            print(f'자동 적용할 기존 INI: {ini}')
        elif args.ini:
            raise FileNotFoundError(ini)
        preset = ROOT / 'assets/obcjk_fonts/obCJK.ini'
        if preset.read_bytes() != preset_ini():
            raise ValueError('포함된 obCJK 글꼴 설정이 검증본과 다릅니다.')
        build(SimpleNamespace(data_dir=args.data_dir, output=output, ini=None, obcjk_ini=preset,
                              csv=ROOT / 'canonical_translation_v2.csv', extra_csv=[],
                              video_subtitles=args.video_subtitles, korean_locations=True))
        reports = {}
        for name in ('translation_audit.json', 'obcjk_validation.json', 'location_validation.json'):
            path = output / name
            reports[name] = json.loads(path.read_text(encoding='utf-8'))
        videos = reports['translation_audit.json'].get('videos', {})
        if videos:
            from build_video_subtitles import EXPECTED_SHA256
            if set(videos) != set(EXPECTED_SHA256) or any(not (output / 'Video' / name).is_file() for name in videos):
                raise ValueError('인트로·엔딩 자막 영상 중 일부가 누락되었습니다.')
        reports['video_subtitles'] = {'mode': args.video_subtitles,
                                      'status': 'generated' if videos else 'disabled' if args.video_subtitles == 'off' else 'skipped'}
        reports['fonts'] = install_fonts()
        reports['ini_backup'] = update_existing_ini(ini, ORIGINAL_FONT_SETTINGS) if ini.is_file() else None
        reports['font_settings'] = ORIGINAL_FONT_SETTINGS
        with report_path.open('x', encoding='utf-8') as stream:
            json.dump(reports, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        for name in ('translation_audit.json', 'obcjk_validation.json', 'location_validation.json', 'FONT_SETTINGS.txt'):
            (output / name).unlink()
        print(f'번역 모드 생성 완료: {output}')
        if videos:
            print('인트로·엔딩 한국어 자막 영상 2개 생성 완료: Video 폴더')
        elif args.video_subtitles != 'off':
            print('주의: 동영상 자막은 생성되지 않았습니다. 로컬 생성에는 FFmpeg·ffprobe·RAD Video Tools가 필요합니다. 배포용 영상은 Nexus 별도 파일을 사용하세요.')
        if not ini.is_file():
            print('기존 Oblivion.ini가 없어 INI 설정을 건너뛰었습니다. README의 글꼴 설정을 확인하세요.')
    print('글꼴 설치 완료. 생성된 모드 폴더를 MO2에 넣고 활성화하세요.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'설치 실패: {error}', file=sys.stderr)
        raise SystemExit(1)
