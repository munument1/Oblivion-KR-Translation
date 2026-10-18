# 성소 메시지 누락 조사 · 2026-10-19

제보 문구 `Love beauty and honor its mysteries. Pray at my chapel altars to receive my blessings.`는 `SCPT:00177218` / `ShrineDibella`의 `MessageBox` 문자열이다. `Oblivion.esm`, `Knights.esp`, `Knights - Unofficial Patch.esp`가 같은 FormID를 포함한다. 후순위 플러그인이 이전 플러그인의 스크립트를 덮어쓰므로 세 파일을 모두 처리해야 한다.

## 확인한 범위와 수정

9개 성소 전부에서 메시지 번역이 누락됐다. 대상 FormID는 `00177201`, `00177213`–`0017721A`이며 Mara, Julianos, Kynareth, Zenithar, TiberSeptim, Akatosh, Dibella, Arkay, Stendarr에 해당한다.

| 플러그인 | SCPT 레코드 | 메시지 발생 위치 |
| --- | ---: | ---: |
| Oblivion.esm | 9 | 27 |
| Knights.esp | 9 | 45 |
| Knights - Unofficial Patch.esp | 9 | 72 |
| 합계 | 27 | 144 |

서로 다른 문구는 14종이다. 신별 교훈, 축복 안내, 명성 부족, 회색 두건 착용 거부, 참회, 순례 완료, 죄 사면을 모두 번역했다. 비공식 패치의 반복 등장 문구도 모두 처리한다.

`build_shrine_messages.py`는 플러그인명·FormID·EditorID·원본 SCPT 전체 SHA-256을 검사한다. `SCDA`의 실제 문자열과 `SCTX`의 소스 문자열을 함께 수정한다. 한글 UTF-8 바이트가 원래 길이를 넘지 않게 번역하고 남는 바이트를 공백으로 채운다. 명령 길이, 분기 오프셋, SCHR, 참조 테이블, 레코드 및 그룹 길이는 유지한다. 전체 파일을 문자열만 역치환하여 입력과 일치하는지도 확인한다. 알려진 원본과 다르면 작업을 중단한다.

`build_obcjk_release.py`와 `build_unofficial_release.py`에 통합했으며 설치기 PyInstaller 설정에도 모듈을 포함했다. 원본 Data와 기존 MO2 모드는 수정하지 않았다. 후속 배포 요청에 따라 설치기 v1.1.4와 UODP 27-KR1.7을 준비했다. UOP/UODP의 모든 ESP는 ZIP 최상위에 배치한다.

## 성소 외 누락 후보

사용자가 지정한 원본 Data와 `Oblivion_KR_Mod`의 공식 플러그인 10개를 비교했다. `Message` / `MessageBox`가 있는 레코드는 919개로 SCPT 822개, INFO 96개, QUST 1개였다. 이 중 918개는 SCDA가 원본과 동일했다. 3,152개 따옴표 리터럴 발생 위치 중 3,147곳에서 원문이 번역본 SCDA에도 남아 있었다.

이는 일반 문자열 테이블과 별개로 스크립트 메시지에 광범위한 누락이 있음을 보여준다. 기존 패쳐의 스크립트 전용 번역은 하수도 출구 5개 문구만 처리했다. 위 수치는 미사용·디버그 스크립트와 버튼 문자열을 포함한 조사 후보이며, 실제 플레이에서 보이는 미번역 문구 수나 고유 문구 수가 아니다. 이번 수정 범위는 9개 성소와 이를 덮어쓰는 플러그인이다. 다른 후보는 별도 번역 작업이 필요하다.

재현 도구:

```powershell
python scripts/audit_script_messages.py --source 'C:\Games\Steam\steamapps\common\Oblivion\Data' --translated 'D:\Oblivion MO2\mods\Oblivion_KR_Mod' --output '_build\script_message_inventory.json'
```

## 검증과 남은 확인

- 자동 테스트 80개 통과. 성소 신규 테스트 5개는 본편·기사단·반복 메시지, 바이트 보존, 원본 불일치 및 길이 오류 거부, 대상 누락·중복 거부를 확인했다.
- 원본 Data에서 본편·공식 DLC 전체 빌드 성공. 원본 UOP/USIP/UODP에서 비공식 패치 전체 빌드 성공.
- 기존 설치본을 입력으로 별도 핫픽스 3개를 생성했고 27개 SCPT / 144곳을 수정했다. 각 파일에서 허용된 리터럴 이외의 모든 바이트가 보존됨을 검증했다.
- 게임 내 실제 표시, 줄바꿈 및 세이브에서의 실행은 아직 확인하지 않았다. 후순위의 다른 모드가 같은 SCPT를 덮어쓰면 그 모드도 별도 확인해야 한다.
