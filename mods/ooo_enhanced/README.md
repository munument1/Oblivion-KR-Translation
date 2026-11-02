# OOO Enhanced 6.9 Korean UTF-8

[한국어 설치 안내](README_KO.txt) · [한영 대조표](translations_6.9.csv) · [정적 검증 기록](validation_6.9.json)

6.8.3-KR1.0의 번역을 보존하고, 원문이 정확히 일치하는 기존 OOO 본체 번역을 재사용했습니다. 6.9에 추가·변경된 창 계열과 여명의 빛 신전·서적·일지를 포함해 고유 문구 112개, 항목 134개를 검토했습니다. 문법·대소문자·공백만 바뀐 문구는 의미가 같은 기존 번역을 유지했습니다. 전체 대조표는 내부 표기와 스크립트 소스 문자열을 포함한 15,835행이며 파일·레코드·FormID·필드·원문·번역·처리 방법을 기록합니다.

원본 [OOO Enhanced 6.9](https://www.nexusmods.com/oblivion/mods/47187), 기존 OOO 본체 한국어판과 obCJK UTF-8 환경이 필요합니다. [한국어판 Nexus 페이지](https://www.nexusmods.com/oblivion/mods/56742).

## 재현

Python 3 표준 라이브러리만 사용합니다. 원본 리소스와 플러그인은 저장소에 포함하지 않습니다.

```powershell
python mods/ooo_enhanced/build.py '원본 6.9 압축 해제 폴더' '새 출력 폴더'
python mods/ooo_enhanced/test_build.py
```

빌더는 원본 ESP 24개와 대조표의 SHA-256을 먼저 확인하고, 원문이 일치하는 필드만 변경합니다. 기존 출력 폴더는 덮어쓰지 않습니다. 레코드 수·비번역 필드·참조·통계·리소스 경로를 비교하고, 스크립트의 문자열 길이와 SCHR 크기 및 블록·루프 주소를 보정합니다. 원문으로 되돌린 각 명령의 비문자열 인수까지 검사합니다. `bytecode.py`는 2026-10-23 OOO 확장 번역 작업에서 검증한 도구를 재사용했습니다.

원본 SCTX에는 있지만 SCDA에는 없는 `Continue.` 1개는 기존 소스 그대로 보존하며 검증 기록에 남깁니다. 기존 번역의 서적 표시용 서식 보정은 유지하고, 이번에 검토한 서적은 원본 HTML 태그 보존을 별도로 확인했습니다. [xEdit 추가 검증](XEDIT_QA_6.9.md)에서 ESP 24개의 번역 추가 진단은 0건으로 확인했습니다. 원본과 한국어판 본편의 진단 140건은 동일합니다. 게임 실행은 미실시입니다.

## 배포

[OOO 전용 Nexus 업로드 작업](../../.github/workflows/nexus-ooo-enhanced-upload.yml)은 저장소의 기존 `NEXUSMODS_API_KEY` secret과 공식 Nexus v3 업로드 Action을 사용합니다. 키를 코드나 대조표에 넣지 않습니다.

1. 빌드한 ESP 24개를 원본 상대 경로로 묶고 `_한국어패치_안내` 문서와 검증 기록을 넣습니다.
2. `ooo-enhanced-6.9-kr1.0` GitHub Release에 `OOO_Enhanced_Korean_UTF8_6.9_KR1.0.zip`과 `.sha256`을 올립니다.
3. 워크플로의 `inspect`를 실행해 Nexus v3 파일 그룹 ID를 확인합니다. 이 ID는 웹페이지의 구형 다운로드 파일 ID와 다릅니다.
4. 같은 워크플로를 `upload`, 릴리즈 태그, 확인한 `file_id`로 실행합니다. 기존 배포본을 유지한 채 새 버전을 올리고 Nexus 응답의 버전·파일 ID를 재검증합니다.

현재 한국어판 파일 그룹 ID `8217540`은 워크플로 기본값에 저장했습니다. [6.9-KR1.0 릴리즈](https://github.com/munument1/Oblivion-KR-Translation/releases/tag/ooo-enhanced-6.9-kr1.0)와 [Nexus 업로드·API 검증 성공 기록](https://github.com/munument1/Oblivion-KR-Translation/actions/runs/41380846286)을 확인할 수 있습니다.

`qa-note`는 배포 ZIP의 SHA-256과 완료된 xEdit 검증 기록을 확인한 뒤, 기존 6.9-KR1.0의 Nexus 변경 기록에 검증 결과를 덧붙입니다. 새 ESP 버전은 올리지 않습니다. Nexus 변경 기록 API는 추가 방식이므로 같은 보고서를 중복 실행하지 마세요.

현재 업로드 검사기는 이번 6.9 패키지 구성과 검증 기록을 확인합니다. 다음 버전에서는 대조표·원본 해시·빌드 검증 기록과 워크플로의 버전·ESP 개수 검사를 함께 갱신하세요.

기존 번역 출처와 기여자 안내는 배포 ZIP의 `CREDITS_KO.txt`와 `OOO_BASE_TRANSLATION_README.txt`에 그대로 동봉합니다.
