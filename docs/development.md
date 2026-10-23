# 빌드와 저장소 구성

현재 main은 v1.1.6 OBCJK UTF-8 직접 빌드를 기준으로 합니다. 사용자 안내는 루트 README.md 한 곳에서 관리합니다.

## Windows 설치기 빌드

```powershell
python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm --clean OblivionKRBuilder.spec
python package_obcjk_installer.py --exe dist/OblivionKRBuilder.exe --output dist/Oblivion_Original_KR_Installer_v1.1.5.zip --version 1.1.5
```

설치기 ZIP에는 EXE, 한국어 BAT, 사용자 안내, 글꼴 출처와 OFL 라이선스, obCJK 수정본의 출처·수정 소스를 넣습니다. EXE 내부의 `assets/obcjk_runtime`에 게임에서 확인한 임시 해결본 2 DLL을 포함하고, 빌더가 수정 DLL의 SHA-256을 확인한 뒤 번역 모드에 복사합니다. 게임의 원본 ESM/ESP, xOBSE DLL, MO2 프로필, 세이브는 포함하지 않습니다. 설치기를 MO2에서 실행할 필요는 없습니다.

## 코드와 자료

일반 게임 텍스트와 대사의 신규 번역·수정은 `canonical_translation_v2.csv`를 단일 원본으로 관리합니다. 같은 성격의 보정 CSV를 새로 만들지 않고, 기존 원문·FormID·필드·occurrence를 확인해 해당 행을 수정합니다. Unicode와 UTF-8 hex 및 기존 바이트 인코딩 열은 같은 번역을 유지하고, 다른 행과 파일 형식은 보존합니다.

장소·지도 마커는 `canonical_locations_v2.csv`, 언오피셜 패치 전용 텍스트는 `canonical_unofficial_translation_v2.csv`, 언오피셜 장소는 `canonical_unofficial_locations_v2.csv`에서 관리합니다. 특수 UI, 책 제목·본문 복구, 스크립트 표시 문구처럼 구조상 별도 처리가 필요한 기존 전용 자료는 유지합니다.

2026-10-16 Crowhaven 대사 통합은 `Oblivion.esm / INFO / 00038ED7 / NAM1 / occurrence 1`의 기존 행 한 개를 수정했습니다. UI 보충 테이블에서 같은 응답을 덮어쓰던 중복 행도 제거했습니다. 메인 CSV 47,227행의 UTF-8과 원본 ESM의 네 응답을 확인했으며, 대상 행 외의 메인 CSV 바이트와 다른 응답은 보존했습니다.

통합 검증에서 단위 테스트 67개가 통과했고, 본편·공식 DLC 출력 10개의 SHA-256 및 빌드 감사 보고서가 변경 전과 일치했습니다. 언오피셜 원본 14개를 개별 확인한 결과 12개 출력도 변경 전과 일치했습니다. 나머지 `DLCSpellTomes - Unofficial Patch.esp`의 `02001281`과 `Knights - Unofficial Patch.esp`의 `02000ED2`는 변경 전후 모두 기존 BOOK/DESC 제목 축약 보호 검사에 걸립니다. 따라서 언오피셜 전체 CLI 빌드 성공은 확인하지 못했으며, 이 별도 번역 데이터 문제와 게임 내 실플레이 검증은 이번 통합 범위에 포함하지 않았습니다.

이후 같은 날짜에 [UODP 책 전수 검증·본문 복구](unofficial/UODP.md)를 수행해 위 빌드 중단 원인을 해결했습니다. 기존 언오피셜 CSV의 BOOK/DESC 4행만 수정했고, UOP·USIP·UODP 전체 14개 ESP 빌드와 테스트 74개가 통과했습니다. 위 문단은 대사 CSV 통합 당시의 검증 기록입니다.

- `install_obcjk.py`: 기존 INI 자동 검색·글꼴 경로 복원, 번역 빌더 호출, 글꼴 등록.
- `build_vanilla_overlay.py`, `build_obcjk_release.py`: canonical UTF-8 데이터를 원본 ESM/ESP에 직접 적용하는 본편·공식 DLC 빌드 경로입니다.
- `build_unofficial_release.py`: UOP/USIP/UODP 원본에 번역과 CELL/WRLD/REFR/REGN 위치 canonical을 함께 적용하는 OBCJK UTF-8 전용 빌더입니다.
- `build_obcjk_locations.py`: 지도 마커·현재 위치·발견 위치용 이름을 적용합니다. 현재 레코드 순회·검증 공용 함수 때문에 `build_obcjk_overlay.py`, `obcjk_text_backend.py`, `oblivion_korean_codec.py`를 간접 사용하므로 이 세 파일은 삭제하지 않습니다.
- `build_obcjk_ui.py`, `master_layout.py`, `obcjk_fonts.py`: 메뉴 UI, 원본 레코드 배열 보존, 글꼴 설치·검증.
- `build_shrine_messages.py`: 본편·기사단 DLC·UODP의 9개 성소, 총 27개 SCPT / 메시지 144곳을 원본 스크립트 SHA-256으로 검사하고 고정 길이 UTF-8로 번역합니다. 최종 보고서의 `shrine_messages`에 결과를 기록합니다. 앞 단계 `structure`의 스크립트 해시는 성소 표시 문자열 수정 전 값이며 최종 해시는 `output_sha256`입니다.
- `build_script_messages.py`: 원본 전체 스크립트 SHA-256을 확인한 뒤 하수도 출구의 SCDA/SCTX 표시 문구 다섯 건만 같은 바이트 길이로 번역합니다. 기존 구조·스크립트 검증과 native layout 검증이 끝난 후 적용하며, 최종 파일의 모든 바이트를 입력과 허용한 문구 변경에 대조합니다. 검증 보고서의 `structure`와 `native_master_layout`은 이 단계 이전 값이며, 최종 파일 해시와 문구 변경 내역은 `script_messages`에 기록합니다.
- 루트 CSV 23개: 설치기의 실제 번역 입력. 이름에 legacy/remaster가 있어도 현재 canonical 및 언오피셜 빌드 입력에 사용되므로 임의로 삭제하지 않습니다.
- `assets/obcjk_fonts`: 원본 글꼴 3개, obCJK.ini, 라이선스와 SHA-256 목록.
- `obcjk_runtime.py`, `assets/obcjk_runtime`: 고정된 SHA-256의 비공식 obCJK 수정 DLL, 검증 정보, 원제작자 출처와 수정 소스. UTF-8 보정을 기본 활성화하고 출력 검증 보고서에 적용 DLL 해시를 기록합니다.
- `assets/Fonts`, `assets/menus`: 인코딩 변환 및 UI 입력 자료.
- `build_video_subtitles.py`, `video_subtitles`: Nexus 별도 배포용 인트로·엔딩 Bink 1 영상 2개를 재생성하는 개발 도구와 자막 소스입니다. 일반 설치기는 `--video-subtitles off`를 사용합니다.
- `package_obcjk_installer.py`, `package_obcjk_unofficial.py`: GitHub 설치기와 Nexus 언오피셜 ZIP 패키징.
- `tests`: 현재 빌드에서 사용하는 문자열·바이너리 보존, 위치명, INI, 글꼴, 언오피셜 및 영상 검증.
- `docs/obcjk`: 설정 설명과 실행 검증 기록.
- `docs/v2_review`: 과거 번역 검수 결과 보관 자료. 실행 코드가 아니며 현재 빌드에는 포함되지 않습니다.
- `docs/legacy`: 과거 사용자 안내. 과거 배포의 재현은 해당 버전 태그를 사용합니다.
- `_build`, `build`, `dist`, `output`, `release`, `v2_work`: 로컬 작업·출력이며 Git에서 제외합니다.

## Nexus ZIP 분리

```powershell
python package_obcjk_unofficial.py --patch UOP --input-dir _build/obcjk/UOP --output dist/UOP_KR_UTF8_obCJK_v1.1.0.zip
python package_obcjk_unofficial.py --patch USIP --input-dir _build/obcjk/USIP --output dist/USIP_KR_UTF8_obCJK_v1.1.0.zip
python package_obcjk_unofficial.py --patch UODP --input-dir _build/obcjk/UODP --output dist/UODP_KR_UTF8_obCJK_v1.1.0.zip
```

모든 ESP는 해당 ZIP 최상위에 둡니다. Citadel Door Fix와 SSSB도 하위 폴더로 분리하지 않으며 기존 플러그인 활성화 상태를 유지합니다. 패키징은 통합 OBCJK 빌드의 release_audit.json과 ESP SHA-256을 확인하며, 각 ZIP에 해당 모드의 ESP만 포함합니다. 이 세 ZIP은 GitHub 본편 설치기에 넣지 않고 Nexus에서 별도 배포합니다.

## main 정리

main에는 현재 v1.1.5 빌드·검증·패키징에 필요한 Python만 유지합니다. 번역 검수 과정에서 사용한 `v2_tools`, 루트 audit/extract/export 도구, native 재정렬 일회성 검증 스크립트는 제거했으며 필요하면 Git 기록과 이전 태그에서 확인할 수 있습니다. 과거 검수 결과 자체는 `docs/v2_review`에 보관합니다.

## v1.1.6 전체 번역 정합성

`unofficial_text_forwarding.py`는 본편 canonical·UI 보충·모피 보정·책 제목 보정·지명 테이블을 실제 본편 빌더와 같은 순서로 읽습니다. `unofficial_text_forwarding_v1.csv`는 번역문 사본이 아닌 양쪽 원문 해시와 정체성 연결 자료입니다. 영문 변경을 유사도로 추측하는 코드는 런타임에 없습니다. `scripts/audit_unofficial_alignment.py`는 공개 배포본의 전체 표시 필드를 대조해 manifest 및 `docs/unofficial/alignment_audit_v1.1.6.json.gz`을 재생성하는 개발 도구입니다. 철자 등가 규칙은 개발 단계에서만 사용하며 의미 변경은 보존합니다.

`unofficial_manual_fixes_v1.csv`는 별도 교정한 51항목의 정체성과 원문 해시만 보관하며, 실제 한국어는 기존 `canonical_unofficial_translation_v2.csv`에서 읽습니다. `scripts/release_unofficial_sync.py`는 고정 해시의 공개 v1.1.5 ZIP에서 같은 데이터로 텍스트만 갱신하고 모든 비선택 필드를 비교합니다. 사용자 원본이나 세이브는 접근하지 않습니다. 일반 영문 원본의 새 빌드도 `build_unofficial_release.py`에서 동일한 canonical 연결을 사용합니다.
