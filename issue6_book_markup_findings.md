# GitHub issue #6 — BOOK/DESC에 글자로 노출되는 `<br>`

2026-10-31 검토. 대상: [Issue #6](https://github.com/munument1/Oblivion-KR-Translation/issues/6).
보정 자료는 신규 `issue6_book_markup_*`와 회귀 테스트로 관리하며,
본편·언오피셜 두 빌더와 설치기 번들에 연결했다.

## 스크린샷과 원본 데이터 대조

- [로비디쿠스 경의 일기 스크린샷](https://github.com/user-attachments/assets/d7988821-2176-424a-9bf2-3653ce0222c3): 실제 책 양쪽 페이지에 `<br>` 문자열이 보인다. 본편 `Oblivion.esm / BOOK 00038B2F / MS52LordJournal / DESC` 원문은 HTML 태그가 **없고** 실제 CRLF를 사용한다. 반면 `canonical_translation_v2.csv`의 UTF-8 한국어 본문에는 소문자 `<br>`가 **37개** 들어 있다. 이미 있는 LF 바로 앞에 붙은 태그가 많아 태그만 제거하면 원래 줄 경계가 남는다.
- [상점 전단 스크린샷](https://github.com/user-attachments/assets/1973a2fb-9dfd-4a09-b400-624694c235a3): 문장과 상점 이름을 대조하여 `Oblivion.esm / BOOK 00071777 / ClutterICShop02 / DESC`로 확인했다. 원문은 `At The Main Ingredient, we only stock...`로 시작하고 HTML 태그가 없다. 한국어 `...최고의 품질을 자랑합니다.<br>`의 마지막 태그가 화면에도 그대로 나온다.
- UOP `00038B2F / MS52LordJournal` 원문에는 `<font face=5>`, 대문자 `<BR>` **20개**, `</font>`가 있다. UOP 자체 canonical 번역에는 `<div align="left">`와 소문자 `<br>` **18개**가 있고, `unofficial_text_forwarding_v1.csv`는 이 책 본문을 본편 canonical 번역으로 전달하도록 설정되어 있다. `build_unofficial_release.py`의 전달은 canonical 선택보다 나중에 실행되므로 최종 선택 본문은 본편의 37개 소문자 `<br>`일 수 있다.
- 같은 유형인 공개 알림 `BOOK 00071D50`은 이미 2026-10-25에 실제 CRLF로 수정되었으며 현 canonical에서도 `<br>`가 없다. [docs/unofficial/UOP.md](docs/unofficial/UOP.md) 17–19행 참고.

## 보정 범위와 원칙

`issue6_book_markup_manifest_v1.json`은 source SHA-256, 최종 선택된 기존 UTF-8 대상 SHA-256, 보정 후 SHA-256, 플러그인·FormID·EditorID·occurrence를 고정했다. **61개 물리 출력 대상** = 본편 **52개**(일기 1 + 상점 전단 51) + UOP가 본편 번역을 전달하는 **9개**(같은 일기 1 + 전단 8)이다.

- 원문에 태그가 없는 본편 일기·상점 전단: 번역본에 삽입된 `<br>`만 제거한다. 이미 뒤에 LF/CRLF가 있으면 원래 개행을 남기고, 독립된 `<br>`는 실제 CRLF로 대체한다. 한국어 문장·영문 고유명사·다른 태그는 보존한다.
- UOP 일기: 해당 원본에 있는 `<font face=5>`와 닫는 `</font>`를 보존하는 형태로 감싸고, 줄바꿈 태그를 대문자 `<BR>`로 정규화하며 물리 개행은 CRLF로 통일한다. 현재 번역은 원문과 문단 나누기 횟수가 달라 `<BR>`의 **개수 동일성까지는 보장하지 않는다**. 실게임에서 페이지 넘김과 글꼴을 검사해야 한다.
- 현재 canonical 본편 `BOOK/DESC` **939개** 중 원문에 HTML 서식이 없는데 번역에 `<br>`가 추가된 건 **127개**이다. 이번 선택 범위의 52개를 제외한 **75개**(다른 일지·메모·영수증 등)는 개별 문맥 검사 대상으로 남긴다. 원문에 이미 HTML이 있는 책·쇼핑 목록은 이 자동 보정에 포함시키지 않았다.

원본 `*.esm`, `*.esp` 및 공용 canonical CSV는 수정하지 않았다. `issue6_book_markup_fix.py`의 `correct_selected_book(plugin, formid, editor_id, original, chosen)`만 최종 번역 바이트를 반환한다. 대상이 아니면 원래 값을 그대로 반환하고, 대상의 원문 또는 번역 SHA가 다르면 즉시 실패한다.

## 빌더 통합 지점 (적용 완료)

1. `build_vanilla_overlay.py`의 `patch_record`: 영어 원문 매칭과 최종 replacement 선택을 완료한 다음, `encode_subrecord(field, replacement)` 직전에 `BOOK/DESC`에 한해 함수를 호출한다. `filename`, `formid`, `editor_id`, `value`(원문 바이트), `replacement` 전달. 기존 감사 기록의 source SHA는 원문을 유지한다.
2. `build_unofficial_release.py`의 `collect_changes`: `forward_text`가 끝난 다음이자 `suspicious_book_body` 검사를 하기 전에 `BOOK/DESC`에 한해 호출한다. `original.name`, `key[1]`, `old_editor`, `old`, `replacement` 전달. 앞에서 호출하면 UOP 본편 전달이 변경을 다시 덮는다.

`python issue6_book_markup_fix.py`는 고정 manifest와 양쪽 canonical CSV를 재대조한다. `python -m unittest discover -s tests -p test_issue6_book_markup.py -v`는 61개 입력/출력 SHA, 비대상 유지, 편집자·원문·번역 mismatch 거부, 태그 문법, 스크린샷과 일치하는 `00071777`을 검증한다.

2026-10-31 추가 검증: `_build/shrine_unofficial_source_20261019/UOP/Unofficial Oblivion Patch.esp` (11,705,644 bytes)의 원본 이진 레코드를 `build_unofficial_release.read_records`로 직접 읽고 UOP 대상 **9/9**의 `BOOK/DESC` EDID 및 원본 SHA-256 일치 확인. 본편 `patch_record`와 UOP `collect_changes`의 실제 함수 연결 회귀 테스트도 추가해 전체 **9/9 PASS**, 기존 `tests.test_uop_book_restoration` **8/8 PASS**.

## obCJK 렌더링 근거 및 유보 사항

저장소의 `assets/obcjk_runtime/source_changes/obCJK_XOBSEStringUtf8.h`는 xOBSE 문자열 UTF-8 변환과 UI tokenizer에 대한 수정이다. [obCJK upstream `main.cpp`](https://github.com/AophMiSaki/obCJK/blob/main/obse_plugin_example/main.cpp)는 word wrap, UTF-8 glyph, 줄바꿈 판정 후크를 설치하며, [`obCJK_LineBreakHook_UTF8.h`](https://github.com/AophMiSaki/obCJK/blob/main/obse_plugin_example/include/obCJK_LineBreakHook_UTF8.h)는 너비 초과 시 줄바꿈을 결정한다. 현재 검토 소스에서 책 HTML 태그를 직접 해석하는 별도 후크는 확인되지 않았다. 즉 스크린샷과 번역 데이터의 **문자열 노출**은 확인했지만, 소문자/대문자 태그를 어떻게 인식하는지는 Oblivion 게임 렌더러 실험으로 확정해야 한다.

실게임 설치본에 수정 적용·책을 다시 펼쳐서 표시를 확인하지 못했다. 코드/데이터 QA 성공을 실게임 PASS로 보고하지 않는다. 우선 `00038B2F` 양쪽 페이지와 `00071777` 전단, UOP 켠/끈 두 경우를 확인하면 된다.
