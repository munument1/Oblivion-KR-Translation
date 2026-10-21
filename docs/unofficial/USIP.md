# Unofficial Shivering Isles Patch 한국어 UTF-8 번역 (USIP 1.6.2-KR1.6)

## 2026-10-21 궁정 계급명 보정

이번 전체 교체본 `USIP_KR_UTF8_obCJK_1.6.2_KR1.6_20261021.zip`은 쉬버링 아일즈 궁정의 계급명 원문과 등급 순서의 불일치를 고치고, 영문 패치의 덮어쓰기 레코드에서도 검증된 한국어 명칭을 사용합니다. 본편 설치기 v1.1.5와 함께 업데이트하고 기존 ESP 로드 순서를 유지하세요.

대상 원본: **USIP 1.6.2**. 다른 버전의 ESP에 적용하지 마세요.

## 구성

- 기본: `Unofficial Shivering Isles Patch.esp`

## MO2 설치

1. Shivering Isles, xOBSE, obCJK, 영문 USIP 1.6.2를 먼저 설치합니다.
2. 본편·공식 DLC용 `Oblivion_KR_obCJK`를 활성화합니다. 글꼴과 프로필 INI는 본편 v1.1.0 설치기 안내를 따릅니다.
3. 이 ZIP을 별도 모드로 설치하고, MO2 왼쪽 목록에서 영문 USIP 및 본편 번역 모드보다 아래에 둡니다.
4. 플러그인 이름과 기존 로드 순서를 유지합니다. 이전 바이트 방식 USIP 한글 모드와 UTF-8 시험판을 끄고 MO2의 Oblivion 항목으로 실행합니다.

검증된 번역을 UTF-8로 변환하고 CELL/WRLD 한글 위치명을 적용했습니다. 종족 이름은 영어로 유지합니다. 원문 대조가 확정되지 않은 문자열은 영어로 남을 수 있습니다.

원본 대비 레코드·그룹 식별자, FormID, 필드 순서와 컴파일된 스크립트 보존을 검사했습니다. `validation.json`과 `SHA256SUMS.txt`에 파일별 검증 결과와 해시가 있습니다. 모든 퀘스트·대화·장시간 플레이의 개별 검증을 완료했다는 뜻은 아닙니다.

이 파일은 번역 ESP만 제공합니다. 원본 패치의 메시·텍스처·음성, xOBSE/obCJK DLL, 글꼴은 포함하지 않습니다. 원본 제작 크레딧은 Unofficial Patch Project Team / Arthmoor 및 원본 패치의 기여자에게 있습니다.
