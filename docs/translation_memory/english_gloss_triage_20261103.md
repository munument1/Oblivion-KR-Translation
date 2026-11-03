# Canonical 2026-11-03 영문 괄호 후보 12건 검토 분류

기준 CSV: \`canonical_translation_v2.csv\` SHA-256 \`8d06e39e11064c2d880d16d93fad9b20894e08f5395861515aeea1a9c8fcd3a0\`

[전체 감사 기록](canonical_risk_audit.json)에서 검출된 \`한글(영문)\` 패턴 12개 레코드는 **전부 BOOK/DESC**이며, 모두 오역이라고 판정해서 일괄 삭제할 수는 없습니다. 괄호 속 영문이 원문 언어유희·발음표기·시대 표기인 경우 보존이 필요합니다.

| 원본 | FormID | 현재 판단 | 사유 / 필요한 조치 |
| --- | --- | --- | --- |
| Knights.esp | 01000EDE | 재검토 | West weald 지역 명칭과 번역의 일치 확인. 영문 병기는 원문 괄호가 아님 |
| Oblivion.esm | 00015727 | 재검토 | 밍스(Minx)는 인명 병기 가능성. 인물 이름을 공식 표기와 비교 |
| Oblivion.esm | 000243ED | 의미 보존 | fortunate와 fortuitous라는 두 영단어의 뜻 차이를 지적하는 원문 서술. 영문 단어를 지우면 맥락이 사라질 수 있음 |
| Oblivion.esm | 00024536 | 재검토 | Meat Mandate와 Undrape라는 고유 개념. 최신 용어표와 비교 후 병기 여부 결정 |
| Oblivion.esm | 00024538 | 재검토 | 리자(Rijja) 인명 병기. 이름 표기 통일 필요 |
| Oblivion.esm | 00024573 | 의미 보존 | no one, Know Wan, No Buddy, Know Not, Knoweyr: 비슷한 발음의 단어를 이용한 말장난. 단순 삭제 금지 |
| Oblivion.esm | 00024575 | 재검토 | Tuen Panai, Ten Penny 별명 관련. 현재 괄호 안에 설명문 전체가 들어가 자연스러운 문장으로 다듬을 필요 |
| Oblivion.esm | 00024589 | 원문 보존 | \`(ar-TAY-um)\`은 원문에 실제 있는 발음 안내 |
| Oblivion.esm | 0002458E | 원문 용어 보존 | \`seliffrnsae\`는 세계관 고유 용어. 문맥에 따라 병기 유지 필요 |
| Oblivion.esm | 00073A63 | 원문 보존 | \`et'Ada\` 및 \`ME2500\`은 원문에 있는 신학·연대 표기 |
| Oblivion.esm | 0007F3E7 | 언어유희 검토 | Eyelid, Akaveery, Sayessie는 화자의 잘못된 명칭 언급. 임의 삭제로 개그가 사라질 수 있음 |
| Oblivion.esm | 000908C7 | 재검토 | Brugo와 Middas는 인명/요일 표기. 공식 용어와 통일 후 병기 제거 검토 |

**결론:** 이번 감사에서 확인된 12개는 '영문 괄호가 있으니 전부 삭제'할 수 있는 오류가 아닙니다. 후속 변경은 원문 BOOK 전체와 최신 번역본을 대조하고, 텍스트·HTML 구조·인코딩을 함께 갱신한 뒤 게임 북뷰를 확인해야 합니다. 해당 작업 전까지 임의로 canonical 텍스트를 변경하지 마세요.

그 밖에 영문자가 포함된 240개 행에는 서적의 HTML 속성값, 세계관 문자·기호, NPC 등 기술적 약어가 포함될 수 있습니다. \`scripts/audit_canonical_memory.py\`의 숫자는 **검수 후보 규모**이며 오류 확정 건수가 아닙니다.
