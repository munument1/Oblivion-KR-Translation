OOO Enhanced 6.9 한국어 패치 — 6.9-KR1.0 (2026-11-02)

원본 OOO Enhanced 6.9와 필수 모드를 먼저 설치하세요.
이 ZIP은 본편과 선택 ESP 24개의 UTF-8 번역 교체 파일만 포함합니다.
메시·텍스처·BSA 및 OOO 본체 ESM/ESP는 포함하지 않습니다.
기존 OOO 본체 한국어판과 obCJK UTF-8 표시 환경·한글 글꼴이 필요합니다.

설치
1. 6.9 원본 압축을 별도 폴더에 풉니다.
2. 이 번역 ZIP을 같은 폴더에 풀어 동일 경로의 파일을 덮어씁니다.
3. 합쳐진 폴더를 다시 압축해 MO2에서 원본과 같은 방식으로 설치합니다.
4. 선택 패치는 기존에 사용하던 구성만 선택합니다.
   Easy Difficulty와 Hard Difficulty는 함께 활성화하지 마세요.
5. Bashed Patch를 사용한다면 번역 적용 후 다시 생성합니다.

변경
6.8.3 한국어판의 기존 번역을 보존하고 원문이 일치하는 OOO 본체 번역을 재사용했습니다.
새 창 계열, 여명의 빛 관련 신전·차원문 안내, 서적·일지의 추가·변경 내용을 번역했습니다.
신명 Alduin → Namira, 살인 요구 횟수 40 → 60, 성계 방랑자 명칭도 반영했습니다.
기존 번역자와 원작자 표기는 CREDITS_KO.txt와 OOO_BASE_TRANSLATION_README.txt를 참고하세요.

검증
24개 ESP의 모든 레코드와 필드를 원본 6.9와 비교했습니다.
비번역 데이터, 스크립트 명령·인수·분기 위치, UTF-8, 서식 인자와 변경 서적 태그를 검사했습니다.
원본 스크립트 소스에만 있고 컴파일 결과에는 없는 Continue. 1개는 원본 상태를 보존했습니다.
2026-11-02 추가 xEdit 검사: ESP 24개에서 번역 추가 진단 0건.
본편의 기존 진단 140건은 원본과 한국어판에서 동일합니다.
상세 결과는 GitHub의 XEDIT_QA_6.9.md를 참고하세요. 실제 게임 실행은 미검증입니다.

한영 대조표·재현 빌더·검증 기록
https://github.com/munument1/Oblivion-KR-Translation/tree/main/mods/ooo_enhanced
원작: https://www.nexusmods.com/oblivion/mods/47187
한국어판: https://www.nexusmods.com/oblivion/mods/56742
