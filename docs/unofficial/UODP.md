# Unofficial Oblivion DLC Patches 한국어 UTF-8 번역 27-KR1.8

## 2026-10-21 본편 대사·레코드 보정

이번 전체 교체본 `UODP_KR_UTF8_obCJK_v27_KR1.8_20261021.zip`은 v1.1.5에서 검증한 대사 및 퀘스트 로그 수정이 비공식 DLC 패치의 레코드 덮어쓰기로 사라지지 않도록 전달한 파일입니다. 기존 기사단 성소 메시지 72곳의 수정, BOOK 본문 복구 및 ESP 최상위 배치는 그대로 포함합니다. 설치기 v1.1.5와 함께 한국어 ESP를 교체하고 기존 활성화 상태와 로드 순서를 유지하세요.


대상 원본: **UODP v27**. 다른 버전의 ESP에 적용하지 마세요.

## 2026-10-19 성소 메시지 번역

`Knights - Unofficial Patch.esp`가 본편과 기사단 DLC의 성소 스크립트를 덮어쓰므로, 본편 설치기만 업데이트해도 이 패치를 사용하면 영어 메시지가 다시 표시됩니다. 나인 디바인 9개 성소 스크립트의 메시지 72곳(중복 포함)을 모두 번역했습니다. 디벨라의 아름다움과 신비에 관한 문구, 각 신의 교훈, 축복·참회·순례 완료 안내가 포함됩니다.

넥서스 업로드 파일은 `UODP_KR_UTF8_obCJK_v27_KR1.7_SHRINEFIX_20261019.zip`입니다. 기본 ESP 9개와 선택 SSSB ESP를 포함하는 **전체 교체본**이며, 아래의 기존 책 본문 복구도 포함합니다. 본편은 v1.1.4 설치기로 다시 생성하고 UODP 한국어 모드도 이 ZIP으로 교체하세요. 이번 성소 수정으로 UOP·USIP 한국어 모드를 교체할 필요는 없습니다.

원본 SCPT 전체 SHA-256과 문자열 길이를 검사하고, SCDA와 SCTX의 표시 문자열만 원래 바이트 길이로 수정했습니다. 명령·참조·분기 위치와 모든 비문자열 바이트를 보존했으며, 상세 결과는 ZIP의 `validation.json`에 포함했습니다. 게임 안의 실제 표시는 아직 확인하지 않았습니다.

## 2026-10-16 책 본문 복구

기본 ESP 9개와 선택 SSSB ESP의 모든 BOOK 15개를 원본과 대조했습니다. 본문이 제목 한 줄로 축약된 다음 4개를 기존 `canonical_unofficial_translation_v2.csv`에서 복구했습니다. 새 보정 CSV는 추가하지 않았습니다.

| 플러그인 | FormID | 책 | 이전 본문 → 복구 본문 |
|---|---|---|---|
| DLCSpellTomes - Unofficial Patch.esp | 02001281 | Fenrik's Welcome Tome | 21자 → 502자 |
| Knights - Unofficial Patch.esp | 02000ED2 | The Knights of the Nine | 10자 → 1,987자 |
| Knights - Unofficial Patch.esp | 02000ED4 | Shezarr and the Divines | 9자 → 1,901자 |
| Knights - Unofficial Patch.esp | 02000ED8 | The Song of Pelinal, v 5 | 13자 → 1,236자 |

공식 DLC의 전체 한국어 본문을 기반으로 복구하고, UODP의 주문 잠금 난이도 변경(상급 → 중급)을 반영했습니다. 복구 대상의 연도·거지 살해 사건 등 원문과 어긋난 일부 표현도 바로잡았습니다. 책 제목 FULL과 다른 레코드, 나머지 정상 본문 11개는 유지합니다.

언오피셜 전체 14개 ESP 빌드와 단위 테스트 74개가 통과했습니다. 생성된 ESP에서 15개 본문을 다시 읽어 CSV·UTF-8 일치를 확인했고, 이번 수정 대상 ESP 2개를 제외한 12개 출력은 이전과 바이트 단위로 동일합니다. UOP의 기존 112개 책 본문 복구도 유지했습니다. 원문·출력 해시와 전체 목록은 [전수 검증 기록](https://github.com/munument1/Oblivion-KR-Translation/blob/main/docs/unofficial/uodp_book_body_audit_20261016.json)에 있습니다. 실제 게임 화면에서의 페이지 표시 검증은 별도입니다.

이전 책 복구 배포 파일: `UODP_KR_UTF8_obCJK_v27_BOOKFIX_20261016.zip` (현재 성소 수정본에 포함). **UODP 전체 교체용 ZIP**이며 기존 영문 UODP v27 위에 설치합니다. UOP·USIP 파일과 DLL은 들어 있지 않습니다. 본편 설치기만 다시 실행해도 기존 UODP 한국어 ESP는 바뀌지 않으므로, 이 ZIP으로 UODP 한국어 모드를 교체하세요.

## 구성

기본 ESP 9개:

- `DLCBattlehornCastle - Unofficial Patch.esp`
- `DLCFrostcrag - Unofficial Patch.esp`
- `DLCHorseArmor - Unofficial Patch.esp`
- `DLCMehrunesRazor - Unofficial Patch.esp`
- `DLCOrrery - Unofficial Patch.esp`
- `DLCSpellTomes - Unofficial Patch.esp`
- `DLCThievesDen - Unofficial Patch.esp`
- `DLCVileLair - Unofficial Patch.esp`
- `Knights - Unofficial Patch.esp`

선택: `DLCThievesDen - Unofficial Patch - SSSB.esp` (다른 ESP와 같은 최상위 경로).

## MO2 설치

1. 해당 공식 DLC, xOBSE, obCJK, 영문 UODP v27을 먼저 설치합니다.
2. 본편·공식 DLC용 `Oblivion_KR_obCJK`를 활성화합니다. 글꼴과 프로필 INI는 본편 v1.1.0 설치기 안내를 따릅니다.
3. 이 ZIP을 별도 모드로 설치하고, MO2 왼쪽 목록에서 영문 UODP 및 본편 번역 모드보다 아래에 둡니다.
4. 모든 ESP는 ZIP 최상위에 있습니다. SSSB 등 기존에 사용하던 플러그인의 활성화 상태를 유지하고, 설치한 DLC에 해당하는 ESP만 활성화합니다.
5. 플러그인 이름과 기존 로드 순서를 유지합니다. 이전 바이트 방식 UODP 한글 모드와 UTF-8 시험판을 끄고 MO2의 Oblivion 항목으로 실행합니다.

검증된 번역을 UTF-8로 변환하고 CELL/WRLD 한글 위치명을 적용했습니다. 종족 이름은 영어로 유지합니다. 원문 대조가 확정되지 않은 문자열은 영어로 남을 수 있습니다.

원본 대비 레코드·그룹 식별자, FormID, 필드 순서를 검사했습니다. 성소 스크립트는 허용된 표시 문자열만 수정하고 실행 코드와 분기 위치를 보존했습니다. `validation.json`과 `SHA256SUMS.txt`에 파일별 검증 결과와 해시가 있습니다. 모든 퀘스트·대화·장시간 플레이의 개별 검증을 완료했다는 뜻은 아닙니다.

이 파일은 번역 ESP만 제공합니다. 원본 패치의 메시·텍스처·음성, xOBSE/obCJK DLL, 글꼴은 포함하지 않습니다. 원본 제작 크레딧은 Unofficial Patch Project Team / Arthmoor 및 원본 패치의 기여자에게 있습니다.
