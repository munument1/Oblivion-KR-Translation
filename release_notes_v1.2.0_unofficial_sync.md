# v1.2.0 언오피셜 패치 용어 동기화 (2026-10-31)

본편 [Oblivion Original KR v1.2.0](https://github.com/munument1/Oblivion-KR-Translation/releases/tag/v1.2.0)의 용어 통일에 맞춘 **언오피셜 한국어 ESP 호환 업데이트**입니다. 본편 설치기 1.2.0 자체는 다시 배포하지 않습니다.

## 변경된 한국어판

- **UOP 3.5.9a-KR1.13**: UOP KR1.12에서 288개 필드 수정 (기본 번역 266, 패치 문맥 5, 지도·셀 16, 패치 고유 위치명 1). 단순히 같은 FormID라고 전체 텍스트를 교체하지 않고, 축약된 퀘스트 일지 1건과 이미 맞는 책 제목 1건은 보존했습니다.
- **USIP 1.6.2-KR1.10**: USIP KR1.9에서 131개 필드 수정 (기본 130, 고유 문맥 1).
- **UODP v27-KR1.11**: UODP KR1.10에서 76개 필드 수정 (기본 번역 75, 기사단 DLC 셀 1).

총 **495개** 플레이어 표시 필드의 번역을 v1.2.0 용어집과 동기화했습니다. 체이딘할, 생크 토르, 미식 던, 에일리드, 성기사, 게이트키퍼 등 기존 언오피셜 ESP가 본편의 새 한글 표기를 덮어쓰는 경우가 확인됐습니다.

## 구조 보존

- 실제 GitHub v1.2.0 공개 UOP/USIP/UODP ZIP의 **SHA-256을 고정한 입력**만 사용.
- TES4 master ownership, record type, FormID, field, occurrence로 본편/공식 DLC의 변경 레코드에 연결. 471개 원문 텍스트·17개 위치명은 수정 전 문자열과 정확히 일치하는 경우만 변경.
- 패치 고유 문구 7건은 각각 확인한 **이름 부분만** 바꿨습니다. 패치가 의도적으로 줄인 내용은 복원하지 않습니다.
- 기존 ESP와 수정 ESP의 전체 레코드/선택되지 않은 서브레코드, 컴파일된 스크립트와 구조 서명을 대조했습니다. 이외 게임 데이터, 대사 처리, 퀘스트 스크립트의 변경은 없습니다.
- 각 ZIP 안의 `validation.json`, `previous_validation.json`, `SHA256SUMS.txt`에 원본·출력 해시와 필드 수정 목록을 포함합니다.
- 전체 Python 회귀 테스트 169개 통과. 실제 게임 실행 검증은 요청에 따라 생략했습니다.

## 설치

본편 [v1.2.0 설치기](https://github.com/munument1/Oblivion-KR-Translation/releases/tag/v1.2.0)로 생성한 한국어 모드를 그대로 사용하면서, 사용 중인 UOP·USIP·UODP 한국어 ZIP은 위 새 버전으로 교체하세요. 각각의 영문 언오피셜 패치 원본은 기존 설치본을 유지합니다. 로드 순서는 변경할 필요가 없습니다. 이 업데이트는 세 ZIP의 번역 ESP만 갱신합니다.

이슈 제보 및 증거: [#8](https://github.com/munument1/Oblivion-KR-Translation/issues/8), [교차 대조 및 패치 PR #23](https://github.com/munument1/Oblivion-KR-Translation/pull/23).
