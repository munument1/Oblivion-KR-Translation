## 2026-10-23 넥서스 56688 서적 교정 (소스 반영, 미배포)

신규 제보에서 확인된 `가장 어두운 어둠 / Darkest Darkness` 책의 UOP `BOOK/DESC 00024564`에는 `메루니스의 칼`, `Almalexia`, `Azura` 등 예전 번역이 남아 있었습니다. 본편 Oblivion.esm에는 이미 교정된 본문이 들어 있으므로 UOP 3.5.9a의 원문 SHA-256과 `Book2CommonDarkestDarkness` EDID가 일치할 때만 해당 본문을 본편의 검증된 UTF-8 번역으로 교체하도록 했습니다.

기존 제목 수준으로 잘린 BOOK 본문 112건 복구는 그대로 유지하며, 추가 1건은 `uop_book_source_forward_v1.csv`에서 별도로 추적합니다. **아직 배포된 UOP 3.5.9a-KR1.8 ZIP에는 이 변경이 포함되지 않습니다.** 다음 UOP 한국어 전체 교체본 빌드·출력 검증 및 게임 내 확인이 필요합니다.

# Unofficial Oblivion Patch 한국어 UTF-8 번역 (UOP 3.5.9a)

## 2026-10-21 계급명 및 대사 보정 (3.5.9a-KR1.8)

이번 전체 교체본 `UOP_KR_UTF8_obCJK_3.5.9a_KR1.8_20261021.zip`은 본편 번역 v1.1.5의 대사·퀘스트 로그 교정을 UOP 덮어쓰기 레코드에도 반영하고, 아레나·길드 계급명을 한국어로 전달합니다. 원문·FormID·EditorID·등급 순서 일치 검증을 통과한 필드만 교체하며, 기존 책 본문 112개 복구와 두 ESP 최상위 배치도 유지합니다. 새 설치기와 본 UOP 한국어 ZIP을 모두 업데이트하세요.

## 2026-10-19 패키지 경로 수정

두 ESP를 ZIP 최상위에 배치했습니다. 파일 이동 없이 영문 UOP 위에 덮어쓸 수 있습니다. 기존에 사용하던 플러그인의 활성화 상태를 유지하세요. `Optional` 하위 폴더는 만들지 않습니다. 배포 파일은 `UOP_KR_UTF8_obCJK_3.5.9a_KR1.7_20261019.zip`입니다. 이번 성소 메시지 레코드는 UOP에 없으며, 기존 112개 책 본문 복구를 포함합니다.

## 2026-10-15 BOOK 본문 복구

이전 한국어 UOP ESP에서 본문 대신 제목 한 줄만 표시되던 **112개 BOOK/DESC** 레코드를 복구했습니다. 책 본문은 본편 Oblivion.esm의 검증된 한국어 텍스트를 사용하며, 영문 UOP가 수정한 두 책(`00024594`, `00072296`)의 오탈자·서식 차이도 반영합니다. **진정한 바렌지아 5권**의 제목을 다른 권과 통일했습니다.

해당 수정본의 넥서스 업로드용 파일명: `Unofficial_Oblivion_Patch_KR_3.5.9a_BOOKFIX_20261015.zip`. 기존 UOP 한국어판의 `Unofficial Oblivion Patch.esp`를 교체하는 패키지이며, UOP 영문 원본 3.5.9a가 필요합니다. **Dunbarrow Cove / UODP / SSSB는 이번 파일에 포함되지 않습니다.**

재발 방지를 위해 GitHub 빌더는 `uop_book_body_restore_v1.csv`의 112개 FormID 및 원문 SHA-256을 검사해 본편 canonical에서 본문을 복원합니다. BOOK 본문이 제목 수준으로 잘리면 빌드를 중단합니다. 실제 게임 내 최종 표시 확인은 별개입니다.


대상 원본: **UOP 3.5.9a**. 다른 버전의 ESP에 적용하지 마세요.

## 구성

- 기본: `Unofficial Oblivion Patch.esp`
- 선택: `Oblivion Citadel Door Fix.esp` (다른 ESP와 같은 최상위 경로)

번역할 문자열이 없는 `UOP Vampire Aging & Face Fix.esp`는 원본을 그대로 사용합니다.

## MO2 설치

1. xOBSE, obCJK, 영문 UOP 3.5.9a를 먼저 설치합니다.
2. 본편·공식 DLC용 `Oblivion_KR_obCJK`를 활성화합니다. 글꼴과 프로필 INI는 본편 v1.1.0 설치기 안내를 따릅니다.
3. 이 ZIP을 별도 모드로 설치하고, MO2 왼쪽 목록에서 영문 UOP 및 본편 번역 모드보다 아래에 둡니다.
4. 모든 ESP는 ZIP 최상위에 있습니다. Citadel Door Fix 등 기존에 사용하던 플러그인의 활성화 상태를 유지합니다.
5. 플러그인 이름과 기존 로드 순서를 유지합니다. 이전 바이트 방식 UOP 한글 모드와 UTF-8 시험판을 끄고 MO2의 Oblivion 항목으로 실행합니다.

검증된 번역을 UTF-8로 변환하고 CELL/WRLD 한글 위치명을 적용했습니다. 종족 이름은 영어로 유지합니다. 원문 대조가 확정되지 않은 문자열은 영어로 남을 수 있습니다.

원본 대비 레코드·그룹 식별자, FormID, 필드 순서와 컴파일된 스크립트 보존을 검사했습니다. `validation.json`과 `SHA256SUMS.txt`에 파일별 검증 결과와 해시가 있습니다. 모든 퀘스트·대화·장시간 플레이의 개별 검증을 완료했다는 뜻은 아닙니다.

이 파일은 번역 ESP만 제공합니다. 원본 패치의 메시·텍스처·음성, xOBSE/obCJK DLL, 글꼴은 포함하지 않습니다. 원본 제작 크레딧은 Unofficial Patch Project Team / Arthmoor 및 원본 패치의 기여자에게 있습니다.
