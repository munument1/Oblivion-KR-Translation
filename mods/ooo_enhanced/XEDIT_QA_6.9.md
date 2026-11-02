# OOO Enhanced 6.9-KR1.0 xEdit 검증 (2026-11-02)

**번역으로 추가된 xEdit 진단은 0건입니다.** 선택 ESP 23개는 오류가 없고, 본편 ESP는 영문 원본과 한국어판에서 같은 140건이 보고됩니다. 따라서 번역 ESP를 수정하거나 다시 배포할 필요는 발견하지 못했습니다. 원본의 게임플레이 데이터는 보존했습니다.

- [전체 검증 요약·파일별 검사 수·마스터 해시](xedit_validation_6.9.json)
- [영문 원본 진단 원문](xedit_original_findings_6.9.json)
- [한국어판 진단 원문](xedit_korean_findings_6.9.json)

## 환경과 방법

설치되어 있던 **TES4Edit 4.1.6r9 Lite x64 / BB-84C automation fork**를 `-TES4 -automation-serve -nobuildrefs`로 실행했습니다. [해당 빌드 소스](https://github.com/BB-84C/TES5Edit/tree/v4.1.6-automation.9)의 `validation.check_for_errors`는 GUI의 Check for Errors와 같은 `element.Check` 재귀 순회를 사용합니다. 역참조 캐시 생성은 생략했으며 FormID 해석과 레코드 검사는 수행했습니다. `system.capabilities`의 계약 버전은 0.23입니다.

원본 6.9와 GitHub/Nexus에 배포한 6.9-KR1.0 ESP 24개를 각각 격리한 폴더에 복사했습니다. 게임·공식 DLC, UOP/USIP/UODP, OOO 본체와 OOO Shivering Isles 마스터를 동일하게 사용했습니다. 추가 선택 마스터는 Nexus API로 원작 배포본에서 확보한 Balanced Magic 2.5 및 Enhanced Economy 5.4.3입니다. 정확한 출처 파일 ID와 해시는 JSON에 기록했습니다.

두 폴더의 플러그인 수정 시각을 일치시켜 오블리비언의 시각 기반 정렬 차이를 제거했고, xEdit이 보고한 모든 파일의 로드 순서가 같은지 확인했습니다. 한국어 ESP에는 파일별 UTF-8 설정을 적용하고 영문 마스터에는 기본 CP1252를 유지했습니다.

두 검사 모두 ESP 24개, xEdit 기준 **76,801개 레코드**를 순회했습니다. 기존 바이너리 파서는 76,802개를 세며 이 한 개 차이는 원본과 한국어판 모두에 있습니다. xEdit이 인식한 트리를 기준으로 검사 수를 기재했습니다. 이를 원본이 완전히 오류 없다는 뜻으로 해석하면 안 됩니다.

## 결과

| 본편에서 보고된 진단 | 영문 원본 | 한국어판 |
| --- | ---: | ---: |
| MGEF 저항값 `$FF` 미인식 | 21 | 21 |
| 퀘스트 단계 참조 경고 (INFO 106, PACK 5) | 111 | 111 |
| 비영속 대상을 가리키는 Enable Parent | 6 | 6 |
| ALCH 스크립트 효과 참조 해석 실패 | 1 | 1 |
| LAND의 Cell 참조 형식 불일치 | 1 | 1 |
| 합계 | 140 | 140 |

네이티브 API는 위 140건 모두를 `xedit_check_error`로 분류합니다. 그중 111건은 메시지 내용이 `<Warning: Quest Stage ...>`입니다. 원본에서 이미 보고되는 진단을 자동 정리하거나, 퀘스트 단계·영속성·LAND 데이터에 추측으로 손대지는 않았습니다.

진단의 파일, FormID, 레코드 종류, 필드 경로, 메시지, 중복 개수를 대조했습니다. 메시지에 포함된 퀘스트 표시명 `Slavers and Smugglers` / `노예상인과 밀수꾼`만 대조표의 정확한 FULL 번역으로 정규화하면 **모든 진단이 일치**합니다. FormID와 단계 번호 및 실제 진단 문구는 그대로 비교했습니다.

검사 전후 `dirtyBefore`, `dirtyAfter`, `dirtyChanged`가 모두 false이고, 세션의 미저장 파일·저장 대기 파일은 0개였습니다. 한국어 ESP 24개가 기존 ZIP 내용과 바이트 단위로 같으며, 영문·한국어 파일의 SHA-256도 기존 매니페스트와 일치합니다.

검증한 ZIP: `OOO_Enhanced_Korean_UTF8_6.9_KR1.0.zip`

SHA-256: `54df9e68a75dbbb5cb2fefb2c8b8cf069719eafbf108606211fde19ef9500030`

**실제 게임 실행은 검증하지 않았습니다.** 이 보고서는 xEdit 레코드 검사 및 영문 대비 추가 진단 확인 결과이며, 게임 내 동작이나 원본의 위 진단들이 무해하다는 보증은 아닙니다.
