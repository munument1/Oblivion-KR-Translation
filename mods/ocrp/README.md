# Oblivion Content Restoration Project 한국어 번역

오리지널 **Oblivion**의 삭제 콘텐츠 복원 모드(OCRP) 1.3, Reduced 1.0, Knights 및 OOO Enhanced 호환 패치를 위한 UTF-8 한국어 번역 자료입니다. 기존 본편 번역 데이터와 용어를 우선 재사용하고, 새 대사·일지·서적·이름 및 표시용 컴파일 스크립트 문구를 번역했습니다. **원본 모드의 ESP/리소스를 GitHub에 재배포하지 않습니다.**

## 번역 대상과 설치 의존성

| 번역 ESP | 확인한 원본 | 번역 텍스트 필드 | 표시 스크립트 문구 |
| --- | --- | ---: | ---: |
| `Oblivion Content Restoration Project.esp` | OCRP 1.3 (Nexus 45909) | 1,297 | 59 |
| `Oblivion Content Restoration Project - Reduced.esp` | Reduced 1.0 (Nexus 56306) | 76 | 0 |
| `Oblivion Content Restoration Project -- Knights.esp` | OCRP Knights (Nexus 45909) | 4 | 0 |
| `Infiltration Fix for OOO Enhanced and ORP.esp` | OOO Enhanced OCRP 1.0 (Nexus 55402) | 11 | 0 |
| **합계** | | **1,388** | **59** |

원본 ESP에서 읽은 실제 `MAST` 요구 파일입니다.

- **기본 OCRP**: `Oblivion.esm`, `Unofficial Oblivion Patch.esp`, `Unofficial Shivering Isles Patch.esp`. 원본의 요구 패치를 먼저 설치하고, 해당 ESP 위에 한국어 ESP를 덮어씌웁니다.
- **Reduced**: `Oblivion.esm`, `DLCShiveringIsles.esp`, **`Oblivion Content Restoration Project.esp`**. 기본 OCRP가 반드시 필요하며, 기본판을 대체하는 별도 독립 실행판이 아닙니다.
- **Knights**: `Oblivion.esm`, 두 언오피셜 패치, `Knights.esp`, `Knights - Unofficial Patch.esp`, **기본 OCRP**. 모든 마스터를 설치한 경우에만 사용합니다.
- **OOO Enhanced 호환 패치**: `Oblivion.esm`, `OOO Enhanced.esp`를 마스터로 요구합니다. 대상 모드와의 실제 조합은 별도 게임 테스트가 필요합니다.

## 번역 데이터

- [한영 대조표](translations_ocrp_1.3.csv): 원본 파일·레코드 유형·FormID·서브레코드 순서·영문·한국어·재사용/신규 번역 방식
- [스크립트 표시 문자열 대조표](scripts_ocrp_1.3.csv): 스크립트 FormID 및 Message/MessageBox 원문·번역
- [고정 원본 해시·안전 조건](sources_ocrp_1.3.json): 대상 4개 ESP의 SHA-256, 레코드 수, 번역 자료 SHA-256, 번역하지 않는 내부 식별자 8개
- [독립 재현 빌더](build.py), [검증 테스트](test_build.py), [컴파일 스크립트 문자열 처리 도구](bytecode.py)

기존 한글 메모리의 같은 FormID·필드·영문이 확인된 문구를 우선 적용했습니다. 정확히 대조되지 않는 문구는 수동 번역했습니다. **초기 OCRP 대조에서 과거 번역 메모리의 `한국어(English)` 영문 병기 42건, 영문 표기 잔존 5건, 추가 의미 오류 8건을 확인해 원문과 다시 대조하여 총 55행을 교정했습니다.** 상세 비교는 [교정 기록](legacy_retranslation_20261103.json)에 있습니다. 번역 빌더는 한국어 내용에 남은 라틴 문자를 발견하면 중단합니다(서적 HTML 태그 제외). 대화 주제의 내부 식별자나 런타임용 설명 문구 등 위험한 내부 항목 8개는 원문 그대로 유지했습니다.

스크립트 메시지는 컴파일된 `SCDA`에서 실제 `Message/MessageBox` 문자열 길이 지정 인자를 확인한 59건만 번역했습니다. `SCHR` 바이트코드 길이와 `SCTX` 소스를 동기화하고, 실행 명령·비문자열 인수·분기/루프 대상이 보존되는지 비교합니다. 디버깅 메시지와 컴파일된 문구가 없는 스크립트 소스 문자열은 번역하지 않습니다.

## 재현 빌드

Python 3.10 이상 표준 라이브러리만 사용합니다. GitHub 저장소를 내려받고 원본 4개 ESP가 있는 상위 폴더를 지정하세요.

```powershell
python mods/ocrp/build.py "C:\경로\원본_OCRP_모드_모음" "C:\경로\새_한국어_출력_폴더"
python mods/ocrp/test_build.py "C:\경로\원본_OCRP_모드_모음"
```

빌더는 원본 파일을 **읽기 전용**으로 열고 SHA-256을 일치 검증합니다. 모든 번역 항목의 원문과 위치가 맞는 경우에만 ESP를 생성하며 **기존 출력 폴더는 덮어쓰지 않습니다.** 결과 ESP는 원본과 이름이 동일합니다. 동일 파일의 원본을 모드 관리자에서 대체하거나 원본 모드에 덮어씌워 사용하세요. 다른 모드에서 제공하는 파일이나 리소스는 원본 모드의 안내를 따릅니다.

빌더는 레코드/서브레코드 수, FormID, 비번역 필드, 스크립트 비문자열 실행 인수, 바이트코드 분기 대상, 내부 메시지 길이를 검증하고 출력 폴더에 `OCRP_KR_STATIC_VALIDATION.json`을 작성합니다.

## 검증 현황과 주의

**2026-11-03 기준:** 제공된 원본 4개 ESP에 대하여 텍스트 1,388필드 및 스크립트 표시 문구 59개가 포함된 한국어 ESP 4종을 생성하고 정적 원본/번역 구조 비교에 통과했습니다. **xEdit·CS 또는 게임에서 실제 로드/대화/일지/스크립트 이벤트 플레이테스트는 아직 수행하지 않았습니다.** 특히 여러 언오피셜 패치 및 다른 모드와의 로드 순서, 번역 UI 출력, 저장/불러오기 회귀 검사가 필요합니다. 따라서 검증 완료 정식 릴리스로 간주하지 마세요.

원작 OCRP·Reduced·Knights·OOO Enhanced 호환 패치 제작자의 작업을 존중합니다. 이 저장소에는 오직 번역 문자열과 재현용 도구만 포함합니다.
