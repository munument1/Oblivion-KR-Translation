# OOO Enhanced 6.9a 한국어 패치 — KR1.0

원본 OOO Enhanced 6.9a의 게임플레이 변경을 유지하고 번역을 갱신했습니다. 원본 폴더 이름에는 6.9로 표시되어 있으나, 본편 ESP의 TES4/SNAM에 적힌 내부 버전은 6.9a입니다.

- 발렌우드 순찰자와 노예상인·밀수꾼 퀘스트 일지의 추가·변경 148항목 반영.
- 과거 OOO 번역 후보 140개 고유 문구를 실제 6.9a 영문과 대조해 검토하고, 인명·캠프·동굴 표기 정리. [원본 해시·FormID·필드와 검수 근거](reviewed_memory_6.9a.csv)를 기록하고 저장소의 reviewed-memory 게이트를 통과했습니다. 과거 canonical CSV를 새 번역에 직접 병합하지 않았습니다.
- 메인 퀘스트의 관문 알림을 원본과 같이 ‘두 번째’로 반영.
- 기존 선택 ESP 23개는 이전 6.9-KR1.0과 바이트 단위로 동일.
- [변경 대조표 150행](updates_6.9a.csv), [전체 대조표 15,970행](translations_6.9a.csv), [원본 해시](sources_6.9a.json)와 [정적 검증](validation_6.9a.json) 갱신.

ESP 24개·레코드 76,829개·스크립트 구간 1,422개의 정적 구조 검사와 빌더 테스트를 통과했습니다. [xEdit 검사](XEDIT_QA_6.9a.md)는 영문 원본·한국어판 진단이 동일한 6건이며, 번역으로 추가된 진단은 0건입니다. 실제 게임 실행은 미검증입니다.

원본 6.9a, 기존 OOO 본체 한국어판, obCJK UTF-8 환경과 한글 글꼴이 필요합니다. ZIP을 원본 6.9a 압축 해제 폴더에 덮어쓴 뒤 원본과 같은 방식으로 설치하세요. 사용하던 선택 패치만 적용하고 Easy/Hard는 함께 활성화하지 마세요. Bashed Patch를 사용한다면 재생성하세요. 메시·텍스처·BSA와 OOO 본체는 포함하지 않습니다.

[GitHub 릴리즈](https://github.com/munument1/Oblivion-KR-Translation/releases/tag/ooo-enhanced-6.9a-kr1.0) · [Nexus 한국어판](https://www.nexusmods.com/oblivion/mods/56742?tab=files)

[Nexus 업로드 및 등록 버전 API 검증](https://github.com/munument1/Oblivion-KR-Translation/actions/runs/42797179449)을 완료했습니다. 이전 6.9 배포본도 보존합니다.
