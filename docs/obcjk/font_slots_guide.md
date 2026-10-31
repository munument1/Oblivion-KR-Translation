# obCJK 글꼴 사용 위치와 교체 방법


## NorthernUI Full 한글 윤곽선 보정 (2026-10-31, 소스 설정)

NorthernUI Full에서는 바닐라 UI 슬롯 2와 별도로 **33~37번 폰트 역할**을 사용한다. 기본 한국어 프리셋에서 이 다섯 슬롯의 `OutlineMode`가 0이었기 때문에 한글 윤곽선이 보이지 않을 수 있었다. NorthernUI Away와의 시각적 차이에 관한 제보에 따라 아래 설정으로 변경했다.

- `[obCJK] NorthernUIEnable = 1`: **공식 배포된 원본 NorthernUI.dll**의 글꼴을 연결한다. 기존 값 2는 OBSE 메시징 지원을 넣어 별도로 재컴파일한 NorthernUI.dll 전용이므로 일반 설치자에게 적합하지 않다.
- `[UTF8] FontParam33~37_OutlineMode = 2`, `_OutlineSize = 1`, `_OutlineAlpha = 100`: Normal/Large/MediumLargeUpper/Shadowed/Small의 한국어 글꼴에 1px 검은 외곽선을 적용한다.
- 바닐라 슬롯 2의 2px 외곽선, 다른 슬롯의 Off 설정, 폰트 이름·크기·간격·번역 레코드는 변경하지 않았다.
- 사용자가 특별히 수정한 NorthernUI.dll(OBSE 메시징 구현)을 사용한다면 `NorthernUIEnable = 2`가 필요할 수 있다. 공식 파일을 쓰는 일반 사용자용 기본값은 1이다.

이 변경은 기존 **v1.2.0 버전을 유지한 설치기 재배포**(2026-10-31)와 Nexus 본편 설치기 갱신에 반영했다. 원본 v1.2.0 소스의 obCJK.ini 설정 6곳만 변경하고 전체 회귀 검사, Windows PyInstaller, ZIP·SHA-256 재다운로드 검증을 통과했다. Full/Away 인게임 화면 비교는 아직 하지 않았다. 과거 v1.2.0 ZIP을 내려받은 사용자는 새 ZIP을 다시 다운로드하여 기존 한국어 모드 출력 폴더를 재생성해야 적용된다. obCJK.ini를 직접 바꿀 경우 실제 적용되는 MO2 설정을 백업하고 게임을 완전히 재시작한다.

아래 2026-10-03 시험 기록은 **v1.0.8 당시의 과거 설정**을 설명한다. 당시 NorthernUI 슬롯의 외곽선을 껐던 판단과 이번 소스 변경을 혼동하지 않는다.

2026-10-03 현재 `obcjk-save-test`의 기본 게임 UI 기준이다. 설치본 obCJK의 `obcjk_iniedit_readme(EN).md`에 명시된 SLOT 역할과 실제 시험판 INI를 대조했다. UI 모드가 다른 슬롯을 지정하면 화면별 대응도 달라질 수 있다.

## 현재 글꼴과 사용 위치

| 슬롯 | 게임에서 쓰이는 곳 | 현재 글꼴 | `[UTF8]` 설정 키 | 현재 크기(ASCII / 한글) |
|---|---|---|---|---|
| 1 | 제목, 대부분의 메뉴/UI, 일반 책 | 본명조 KR Medium, 굵기 500 | `FontParam1_1`, `FontParam1_2` | 38 / 39 |
| 2 | NPC 대사 자막, HUD | 본명조 KR Medium, 굵기 500 | `FontParam2_1`, `FontParam2_2` | 40 / 40 |
| 3 | 지도 위치명, 팝업, 나머지 UI | 본명조 KR Medium, 굵기 500 | `FontParam3_1`, `FontParam3_2` | 26 / 26 |
| 4 | 데이드릭 문자 | 원본 Daedric_Font | obCJK 치환 대상 아님 | 원본 자원 사용 |
| 5 | 손글씨 스타일 책, 편지 | 이롭게 바탕체 Medium, 굵기 500 | `FontParam5_1`, `FontParam5_2` | 34 / 34 |

**대사만 고르면 슬롯 2부터 바꾸면 된다.** 같은 슬롯을 쓰는 HUD도 함께 바뀐다. 제목과 책도 슬롯 1을 공유하므로 서로 완전히 독립된 글꼴 설정은 아니다. 크기 값은 obCJK의 설정값이며 실제 화면의 최종 픽셀 크기는 게임 해상도/렌더링 배율에도 영향을 받는다.

추가 UI 모드를 사용할 때의 슬롯은 다음과 같다. 현재 시험 구성에는 MenuQue/NorthernUI가 없어 아래 설정을 바꿔도 해당 화면은 생기지 않는다.

| 슬롯 | 용도 | 키 |
|---|---|---|
| 7 / 8 | MenuQue 추가 글꼴 1 / 2 | `FontParam7_1/2`, `FontParam8_1/2` |
| 33 | NorthernUI Normal | `FontParam33_1/2` |
| 34 | NorthernUI Large | `FontParam34_1/2` |
| 35 | NorthernUI MediumLargeUpper | `FontParam35_1/2` |
| 36 | NorthernUI Shadowed | `FontParam36_1/2` |
| 37 | NorthernUI Small | `FontParam37_1/2` |

NorthernUI의 다섯 역할은 크기/스타일 역할 이름이다. 실제 어느 화면이 그 역할을 쓰는지는 NorthernUI XML 설정에 따라 달라진다.

슬롯 7/8 및 33–37은 본명조 KR Regular, 굵기 400으로 설정했다.

## 눈누에서 고른 글꼴 넣기

1. 원하는 글꼴의 TTF/OTF를 내려받아 Windows에 설치한다. MO2의 Fonts 폴더에 파일만 복사하는 것으로는 obCJK의 이름 기반 글꼴 선택이 충족되지 않는다.
2. Windows 글꼴 정보 또는 obCJK 설정 편집기의 글꼴 목록에서 **설치된 글꼴 이름**을 확인한다. 눈누 표시명이나 파일명과 Windows 등록명이 다를 수 있다.
3. 아래 시험판 파일의 **`[UTF8]` 구역**에서 원하는 슬롯의 글꼴 이름을 바꾼다. 같은 키가 `[BIG5]`에도 있으므로 구역을 확인한다.

```text
D:\Oblivion MO2\mods\Oblivion_KR_obCJK_UTF8_Test\OBSE\plugins\obCJK\obCJK.ini
```

현재 자막 설정:

```ini
[UTF8]
FontParam2_1 = Source Han Serif KR Medium,0,40,0,0,34,500,0,0
FontParam2_2 = Source Han Serif KR Medium,0,40,0,0,34,500,0,0
FontParam2_1_Native = 0
```

`_1`은 반각 영문/숫자, `_2`는 한글 등 CJK용이다. 처음에는 두 줄에 같은 글꼴을 쓰면 혼합 문장에서 스타일 차이를 줄일 수 있다. 위 값 중 첫 번째 항목이 글꼴 이름, 세 번째 `40`이 높이, 일곱 번째 `500`이 굵기다. 글꼴만 비교할 때는 이름만 바꾸고 나머지 숫자는 유지한다. INI는 UTF-8로 저장하고 게임을 다시 실행한다.

다른 사람이 같은 설정을 사용하려면 그 PC에도 해당 글꼴이 설치돼 있어야 한다. Windows/GDI가 다른 글꼴로 대체한 상태와 선택한 글꼴의 실제 적용은 구분한다.

## 고를 때 비교할 문장

```text
이곳에 오래 머물지 마십시오. 문 너머에서 무슨 일이 벌어질지 모릅니다.
값·꽃·읽음·닭·뷁  제국 감옥  체력 125/200  “기록” (ABC 123)-A
```

자막에는 긴 문장의 가독성, 지도에는 작은 크기의 받침과 긴 위치명, 책에는 여러 줄에서의 피로도를 살펴보면 된다. 같은 한글 글꼴이라도 지원 글자 범위와 영문 모양이 다르므로 위 문장과 실제 대사를 함께 비교한다.

## 이번 적용과 검증

현재는 `AsciiRenderEnable = 0`이다. obCJK 20261003의 외곽선 기능을 사용해 **슬롯 2(NPC 대사 자막/HUD)에만 Outline 2px / 100%**를 적용한다. 슬롯 1/3/5/7/8/33/34/35/36/37은 OutlineMode 0이며, NorthernUI Shadowed 역할인 슬롯 36에도 추가 Shadow 효과를 강제로 적용하지 않는다. 표의 사용자 글꼴은 한글/CJK에 적용되며, 영문·숫자·제어문자는 원래 게임 글꼴을 사용한다. 크기·간격과 FontParam 자체는 유지했다. 사용자가 정상 표시를 확인했고 같은 설정을 v1.0.8 설치기에 반영한다. 자세한 근거와 백업 위치는 [제어문자 네모 진단](control_glyph_diagnosis.md)을 참고한다.

선택한 글꼴을 Windows 현재 사용자에게 설치하고, 별도 프로세스의 GDI에서 본명조 Regular/Medium과 이롭게바탕체가 실제 선택되며 완성형 한글 11,172자 누락이 없는 것을 확인했다. 이롭게바탕체는 `Iropke Batang Medium`으로 지정해야 선택된다.

우아한세리프를 메인 메뉴에서 확인한 뒤 사용자 요청으로 슬롯 1의 ASCII/CJK 두 줄을 본명조 Medium으로 교체했다. 크기·간격·위치는 유지했다. 이후 제어문자 네모를 피하는 설정의 정상 표시를 사용자가 확인하고 배포를 요청했다. 모든 자막·책의 줄바꿈/잘림을 전수 확인한 것은 아니다.

선택한 글꼴의 적용 기록은 `_build/obcjk/font-preview/selected-fonts/`, 슬롯 1 교체 전 INI와 해시 기록은 `_build/obcjk/font-preview/menu-source-medium/`에 보관했다. 원본 obCJK 모드 및 기본 빌더의 글꼴 기본값은 바꾸지 않았다.
