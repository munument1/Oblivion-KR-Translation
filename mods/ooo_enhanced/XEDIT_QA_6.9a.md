# OOO Enhanced 6.9a-KR1.0 xEdit 검증 (2026-11-10)

**영문 6.9a 원본과 한국어판의 진단이 완전히 일치하며, 번역으로 추가된 진단은 0건입니다.** 선택 ESP 23개는 진단이 없고 본편의 비영속 Enable Parent 참조 6건만 양쪽에 동일하게 남습니다.

[전체 검증 기록](xedit_validation_6.9a.json) · [영문 진단 원문](xedit_original_findings_6.9a.json) · [한국어 진단 원문](xedit_korean_findings_6.9a.json)

기존 검증에 사용한 TES4Edit 4.1.6r9 Lite x64 / [BB-84C automation fork](https://github.com/BB-84C/TES5Edit/tree/v4.1.6-automation.9)의 네이티브 `validation.check_for_errors`를 사용했습니다. GUI Check for Errors와 같은 `element.Check` 재귀 순회입니다. `-TES4 -automation-serve -nobuildrefs`로 격리한 두 세션에서 검사했으며 역참조 캐시 생성은 생략했습니다.

게임·공식 DLC, UOP/USIP/UODP, OOO 본체·Shivering Isles, Balanced Magic 2.5, Enhanced Economy 5.4.3 마스터를 동일하게 사용했습니다. 양쪽 플러그인의 파일 시각을 맞추고 xEdit이 보고한 실제 로드 순서도 일치하는지 확인했습니다. 한국어 ESP에만 파일별 UTF-8을 적용했습니다. 정확한 마스터 및 실행 파일 SHA-256은 전체 기록에 있습니다.

검사 대상은 ESP 24개, 네이티브 xEdit 및 바이너리 파서 모두 **76,829개 레코드**입니다. 진단의 FormID, 필드 경로, 내용, 순서까지 정규화 없이 완전히 일치했습니다. 남은 6건은 모두 본편 ESP의 `REFR / XESP - Enable Parent / Reference`에 대한 `Target is not persistent`입니다. 파일별 검사 전후 수정 상태는 false, 미저장·저장 대기 파일은 0개였습니다.

이전 [6.9 검사](XEDIT_QA_6.9.md)의 140건은 이번 원본 6.9a에서 6건으로 줄었습니다. 없어진 134건은 원작 변경에 따른 결과입니다. 한국어판에서도 같은 개선 사항을 유지합니다. 원본의 게임플레이 데이터는 임의로 수정하지 않았습니다.

배포 ZIP 내부 ESP 24개의 SHA-256을 검증 당시 파일 및 정적 검증 기록과 비교했습니다. 같은 ZIP에 정적·xEdit 검증 기록과 양쪽 진단 원문을 동봉합니다. 실제 게임 실행과 세이브 호환성은 미검증입니다.
