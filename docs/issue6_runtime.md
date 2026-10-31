# Issue #6 — obCJK/xOBSE·UOP/USIP·OOO·질병 문자열 조사

조사: 2026-10-31. 원제보: [Oblivion-KR-Translation #6](https://github.com/munument1/Oblivion-KR-Translation/issues/6).

## 판정과 실제 수정 산출물

1. **UOP/USIP 영문 설정창은 원본 패치 ESP 안의 컴파일된 스크립트 미번역으로 확인했다.**
   `issue6_unofficial_menu_scripts.py`를 신규 작성했다. 스크립트 전체 SHA-256을 검사하고,
   `SCDA`(실행 바이트코드의 문자열)와 `SCTX`(스크립트 소스의 문자열)를 함께 UTF-8 한국어로 바꾼다.
   원본 문자열의 길이를 공백으로 맞춰, 모든 바이트 오프셋과 기존 컴파일 길이·명령·분기·다른 레코드를 보존한다.
   UOP 21종/81회(두 필드 합계 162곳), USIP 6종/16회(합계 32곳)를 교체한다.
   원래 `OK`는 2바이트라 한국어 글자를 넣을 수 없어 보존한다. 게임 내 신규 표시 검증은 남아 있다.
2. **MOO 선택창의 `예아니요`는 xOBSE 22.13 `MessageBoxEX` 구분자 처리 결함으로 로컬 재현했다.**
   `_mbsbtype`/`_mbclen`이 UTF-8 문자 마지막 바이트와 파이프 구분자를 CP949 문자처럼 처리한다.
   이 오류는 현행 obCJK의 `_mbstok_s` 보정 범위 바깥이다.
3. **업데이트한 xOBSE에서 `?`가 생기는 원인은 호환성 검사 실패 가능성을 우선 확인해야 한다.**
   현행 obCJK 임시 해결본은 확인된 xOBSE 22.13의 특정 PE 빌드와 호출 위치만 허용한다.
   현재 제보자의 22.14 실제 `obse_1_2_416.dll` 바이너리/로그가 없으므로 재현 확정은 아니다.
4. **OOO 아이템명·질병명은 번역 소유 플러그인의 winning record를 아직 확인하지 못했다.**
   게임 화면에 영어가 남은 사실과 별개로 모드 원본·폼 ID 없이 UOP/본편 원장에 임의 편입하면 안 된다.

## xOBSE/obCJK 버전 호환

- `obcjk_runtime.py`는 `assets/obcjk_runtime/obCJK.dll`을 설치한다.
  임시 해결본 2 SHA-256 `ac215af221e680e03e3bbab03e890c34f7dcdfae422d7b82b21256f261b73d06`.
  `assets/obcjk_runtime/manifest.json`에 2026-10-15의 `temporary-fix-2`로 기재되어 있다.
- `assets/obcjk_runtime/source_changes/obCJK_XOBSEStringUtf8.h`의
  `ObCJKInstallXOBSEStringUtf8()`는 xOBSE DLL의 PE 시간 `0x684B4FE5`, `SizeOfImage=0x125000`,
  x86 머신 타입, IAT 위치/원래 호출 대상 및 하드코딩된 호출 opcode를 확인한다.
  누락·불일치 시 `skipped`로 로깅한다. 우회하거나 검사값만 변경하면 안 된다.
- UTF-8 모드와 `XOBSEStringUtf8Enable=1`에서만 16개 `MultiByteToWideChar`,
  6개 `WideCharToMultiByte` 호출의 `CP_ACP` 사용을 `CP_UTF8`로 교정하고,
  UI 메뉴 관련 `_mbstok_s` 호출 2곳(`0x499DE`, `0x499EC`)을 보정한다.
- [xOBSE Nexus 변경 기록](https://www.nexusmods.com/oblivion/mods/37952?tab=logs)에
  2026-10-26의 22.14 업데이트 기록이 있다. 표시 버전과 실제 PE 빌드가 같다는 보증은 없다.
  **22.14에서 보정이 반드시 실패한다고 단정하지 않는다.** 현재 사용 중인 DLL의 PE 타임스탬프,
  이미지 크기, SHA-256과 이번 실행의 `obCJK.log`를 받아야 판단할 수 있다.

수정 경로: 검증된 22.14 바이너리와 해당 소스/호출 지점에 맞춰
`obCJK_XOBSEStringUtf8.h`의 호환 후킹을 이식·검사 후 **32비트 obCJK DLL을 새로 컴파일**한다.
`obcjk_runtime.py`의 체크섬·manifest·테스트도 새 DLL에 맞게 갱신해야 한다.
Python 설치기만 다시 빌드해서는 xOBSE 내부 동작을 고치지 못한다.
게임 설정은 `[obCJK] ActiveCodePage=UTF8`, `XOBSEStringUtf8Enable=1`이며
MO2에서 실제 승리하는 설정 파일과 DLL의 해시를 확인한다.

## MOO 소유권 선택창의 구분자 누락 — 재현 확정

총괄 작업자가 MOO `MOOClaimScript`의 `SCDA`에서
`이 물건의 소유권을 주장하겠는가?|예|아니요`를 확인했다.
원본 xOBSE 22.13 소스 `obse/obse/Commands_Game.cpp:409-449`의
`Cmd_MessageBoxEX_Execute`는 한글 UTF-8을 CP949 DBCS로 판단한 다음 1~2바이트를 건너뛴다.
`예`의 UTF-8 `EC 98 88` 끝 바이트 `0x88`은 CP949 선행 바이트로 판정될 수 있어
다음 `|`(ASCII `0x7C`)를 건너뛰게 된다. 결과는 예/아니요가 한 버튼으로 합쳐진다.

`py issue6_runtime_messagebox_probe.py`를 Windows의 `msvcrt` CP949 상태에서 실행한 결과:

| 입력 | 감지한 파이프 수/기대 수 | 버튼 |
|---|---:|---|
| `...?\|예\|아니요` | 1/2 | `예\|아니요` 한 개 |
| `...?\|예 \|아니요` | 2/2 | `예 `, `아니요` 두 개 |
| `...?\|예\| 아니요` | 1/2 | 여전히 합쳐짐 |
| `ASCII\|One\|Two` | 2/2 | `One`, `Two` |

대응 경로는 두 가지다. MOO 소유 `SCDA/SCTX` 원본 해시가 일치하는 경우
**`예` 뒤, 구분자 앞에 ASCII 공백 한 개 삽입**하는 제한적 소스 패치로 분리할 수 있다.
길이가 늘어나는 compiled literal은 기존 스크립트의 크기/bytecode length/그룹 구조를 적절히
재작성·검증해야 한다. 더 일반적인 해결은 xOBSE `MessageBoxEX`가 UTF-8을 인식하도록
native 소스를 수정해 x86 컴파일하는 것이다. 기존 obCJK 보정은
`Commands_Menu.cpp`의 `_mbstok_s`를 가로채므로 이 `Commands_Game.cpp` 직접 스캔 루프는 보정하지 않는다.
스크린샷의 메뉴에서 `예아니요`로 실제 출력되었고, 로컬 함수 수준에서도 동일하게 재현했다.
별도 제공하는 MOO 5.0.7 KR1.3 ZIP에서는 컴파일 문자열 길이를 유지하기 위해
질문 끝의 물음표를 제거하고 `|예 |아니요`로 교체하여 SCDA/SCTX를 모두 수정했다.
수배지 2개의 `WANTED` 그림 제목과 영어 대명사 노출도 함께 보정했다.
ESP 17,413개 레코드 중 해당 SCPT 1개와 BOOK 2개만 변경했으며,
수정 ESP의 실게임 클릭·선택값 확인은 별도다.

## UOP/USIP 설정 두루마리 — 원본 소유권 및 코드

확인한 로컬 ESP 사본은 빌드용 `_build/csv_merge/probe-before/`에 보존되어 있다.

| 플러그인 | 원본 SHA-256 | SCPT FormID / EditorID | 스크립트 body SHA-256 |
|---|---|---|---|
| `Unofficial Oblivion Patch.esp` | `3ebf1155a618c10452a6fe73bfb80bdf553a60dbadcc36ea000ef2b08bbf5e1c` | `01016EA6 UOPMenuScript` | `1fa2982b3c96a4b1b440334462b66fd903b723eb3271430cda8b99324375aff6` |
| `Unofficial Shivering Isles Patch.esp` | `37ba725d7634998361f8da652abe6875677ec82c77cdfd281ec2a2bd12817c4b` | `030037FD USIPMenuScript` | `8460f0cd7b586c5104f49ce79453dc49f5aed90d9959414df65c7dd95aa19eb0` |

UOP 원본 compiled `SCDA`에는 `Unofficial Oblivion Patch v3.5.8`,
`Exit and return to Oblivion`, `Turn OFF Poisoned Apple warning` 등이 있다.
USIP 원본 compiled `SCDA`에는 `Unofficial Shivering Isles Patch v1.6.1`,
`Turn ON excessive ambient sound fix`, `Turn ON Escort fast-travel fix` 등이 있다.
두 스크립트 모두 `SCTX`에 영문 호출문이 반복된다. 게임에서 표시된 이전 버전 번호
`3.5.8`과 `1.6.1`은 실제 배포 대상인 UOP 3.5.9a/USIP 1.6.2와 다르다.
이번 교정에서는 구버전 번호를 임의 최신화하지 않고 기존 메시지 내용의 의미를 유지했다.

실제 원본 보관 경로인 `_build/shrine_unofficial_source_20261019/UOP/Unofficial Oblivion Patch.esp`
(11,705,644바이트, SHA-256 `2a71820bd290f25eee0b839d133d5df4b60e71398ed692654cbc49333536e044`),
`_build/shrine_unofficial_source_20261019/USIP/Unofficial Shivering Isles Patch.esp`
(2,139,325바이트, SHA-256 `a68d3ea9aa7ee40e9a95575263e72f90549cebe02919e75488257d060d3fbbce`)에서도
두 SCPT body의 SHA-256이 위 표와 **정확히 동일**했다. 본문·스크립트가 일치하므로
보관 원본과 중간 probe-before 산출본 둘 다 독립 QA 대상으로 사용했다.

`build_unofficial_release.py`의 `TEXT_FIELDS`는 `FULL/DESC/NAM1/CNAM/DATA/RDMP` 등이고
`SCDA/SCTX`를 포함하지 않는다. 기존 빌드는 **compiled script 원형 보존을 검증**하기 때문에
원본에 포함된 영문 메뉴까지 그대로 전달한 것이다. 게임 자체의 아이템 `FULL` 번역과 별개의 경로다.

신규 모듈은 `PINS`에 지정된 정확한 스크립트 원본만 허용하며, 모든 원문 literal이
`MessageBox`의 `SCTX`에 존재하고 `SCDA` 안에도 동일한 횟수로 존재하는지 검사한다.
`SCDA` 문자열 앞의 16비트 길이, 스크립트 본문 전체 길이, 비문자 subrecord 전체,
전체 ESP의 나머지 모든 바이트가 불변임을 역패치해 확인한다.
기본 메시지박스 `OK`는 UTF-8 한글 1자(최소 3바이트)보다 짧아 그대로 두었다.

독립 검증 명령:

```powershell
py issue6_runtime_menu_inventory.py
py issue6_runtime_menu_scripts_test.py
```

실물 ESP 2종 × 원본·중간 산출본 각 1개, 총 4개 파일 대상으로 3개 테스트 통과:
(1) 출력의 전체 파일 역변환과 문자열 외 바이트 동일,
(2) 원본 스크립트 변형 시 SHA 불일치로 중단,
(3) SCDA string length prefix 변형을 독립적으로 거부. 산출물은 별도 임시 디렉터리에 쓰고
검증 후 자동 삭제한다. 실제 게임 실행·저장·로드는 이번 조사에서 수행하지 않았다.

`build_unofficial_release.py`는 일반 번역·게이트 수정 및 기존 스크립트 불변 검사를
완료한 뒤에만 UOP/USIP의 해당 SCPT를 보정한다. `issue6_unofficial_menu_scripts.build`
결과의 해시와 역패치 검증을 감사 보고서에 별도로 남긴다.
실제 보관된 원본 14개 ESP로 `--prior-kr` 없이 전체 빌드하여 **14/14 PASS**했다.
UOP 81회, USIP 16회 메뉴 문자열 보정도 감사 JSON에서 확인했다.
기존 KR 파일을 `--prior-kr`로 주는 다른 경로는 과거 `Knights - Unofficial Patch.esp`의
SCDA 차이가 원본 보존 검사에 걸려 중단되었으므로, 그 실행은 전체 PASS가 아니다.
실제 두루마리 표시와 메뉴 분기 동작은 여전히 게임에서 확인해야 한다.

## OOO 및 질병명 — 소유권 미확정

- 제보 인벤토리 화면에서 `Silver Nugget`과 영어 설명
  `A beautiful metal of surprising versatility, Silver is used for ...`가 보인다.
  같은 목록의 `Simple Crafts`는 다른 제작 모드 OCRAFT 계열에서 쓰이는 이름일 수 있어
  스크린샷의 모든 영어 아이템을 OOO 하나의 데이터로 분류할 수 없다.
- 별도의 질병 툴팁은 `질병: Panniculitis Suppurative (30)`이다.
  기본/언오피셜 번역 CSV에서 `Panniculitis`·`Suppurative`를 조회했으나 해당 문자열을 찾지 못했다.
  제보자가 추측한 MOO 소유권은 아직 검증되지 않았다.
- MOO Wanted 포스터의 표제 `WANTED`는 이미지 텍스처에 연결된 제목이었으며,
  `Imperial`과 `He`는 런타임 스크립트가 본문에 삽입하던 값이다. 위 KR1.3에서는
  해당 문구를 한국어 제목과 동적 변수 중심 표현으로 보정했다.

최소 재현은 제보자의 활성 ESP/ESM 목록, 로드 순서, 해당 개체의 xEdit FormID와
최종 `FULL`/`DESC`/`SPEL` 또는 `SCPT` 소유 레코드 확인이다. `Silver Nugget`은
`MISC/INGR` 등 이름·설명 필드, `Panniculitis Suppurative`는 `SPEL/FULL`을 먼저 조회하고,
원문 파일과 충돌 후 최종 승리 플러그인도 대조한다. 확인된 원본을 대상으로
별도의 모드 소유권 보존 번역을 만들면 된다. 현행 저장소에 소유 원본을 찾지 못한 상태에서
영문 문자열만 근거로 FormID나 번역 타깃을 임의 생성하지 않는다.

## 필요한 게임 검증

1. `obse_1_2_416.dll`의 실제 SHA-256·PE timestamp·image size와 obCJK DLL/INI 우선권 및
   **동일 실행 시점**의 `obCJK.log`에서 `installed test2` 또는 `skipped` 기록 확인.
2. UOP 설정 두루마리의 기능별 메뉴 ON/OFF·선택 동작, USIP 메뉴 4개 상태 분기,
   `%` 변수와 효과 슬롯 번호 보존 확인.
3. MOO 소유권 질문 `예`·`아니요` 각 별도 버튼 및 선택 결과(실제 소유권/돈 변화) 검증.
4. OOO·OCRAFT·MOO 등 동시 활성과 단독 상태의 `Silver Nugget`/질병/수배지 비교,
   winning record와 실제 화면 대응 확인.

이 문서에 적은 PASS는 로컬 소스·파일 및 CRT 함수 수준의 검증이다.
제보 환경에서 이미 수정되었다거나 모든 모드에서 호환된다는 판정은 아직 없다.
