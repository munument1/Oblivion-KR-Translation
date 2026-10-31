# Issue #8 — reporter terminology policy (2026-10-31)

**Owner decision:** Use the issue #8 reporter's active glossary spellings for each named entity, rather than selecting the most frequent legacy translation. This resolves the previously undecided terminology question in PR #12.

| English | Canonical Korean | Review status |
| --- | --- | --- |
| Cheydinhal | 체이딘할 | PR #14 text and locations |
| Ayleid / Ayleids | 에일리드 | per-record follow-up |
| Mythic Dawn | 미식 던 | PR #14 text and PR #13 book 2 title |
| Crucible (SI place) | 크루시블 | per-record follow-up |
| Mysterium Xarxes | 작시스의 신비 | PR #14 text |
| Knights of the Nine | 나인의 기사단 | PR #14 text |
| Jauffre | 죠프리 | per-record follow-up |
| Sancre Tor | 생크 토르 | PR #11 locations and marker |
| Staff of Sheogorath | 쉐오고라스의 지팡이 | per-record follow-up |
| Gatekeeper (named creature) | 게이트키퍼 | context required: generic 문지기 differs |
| Amber (SI craft material) | 호박석 | PR #10 equipment |
| Crusader equipment | 성기사 | PR #14 equipment and shrine references |
| Arquen | 아퀜 | per-record follow-up |
| Modryn Oreyn | 모드윈 오레인 | per-record follow-up |
| Vicente Valtieri | 비센테 발티에리 | per-record follow-up |
| Mankar Camoran | 맨카 캐모런 | per-record follow-up |
| Golden Saint | 골든 세인트 | per-record follow-up |
| Dark Seducer | 다크 세듀서 | per-record follow-up |
| Marauder | 습격자 | review NPC/generic context |

**Exceptions requiring context:** Bands of the Chosen has distinct object FULL and topic names; inspect source identity before picking a form. Cupboard→선반 is only a SEED entry, and may itself be a literal mistranslation; do not force it on 찬장 without evidence. Anvil is 앤빌 as the city and 모루 as the tool.

## Already covered

- #9: exact Crate CONT/FULL 38 corrections.
- #10: exact Amber equipment 151 corrections.
- #11: Sancre Tor real location and marker 13 corrections.
- #12: read-only source-anchored audit of 730 high-priority rows.
- #13: source-scoped Mythic Dawn Commentaries volume 2 title, now in canonical 미식 던.
- #14: 574 terminology hits across 561 distinct official text records plus 23 source-anchored location/marker records. Stacked on #11. Existing canonical text CSV remains byte-identical; edited output is assembled with original hash/record guards at build time.

**Not automatically fixed:** the original issue's other named-entity and mention examples, including Ayleid, Crucible, Jauffre, Gatekeeper, NPC names and 631 mention flags. Verify exact English, source plugin, FormID, field, occurrence, markup and Korean grammar before editing. Glossary is authoritative for *name choice*, but not evidence that an arbitrary substring is the same entity.

## Release validation

GitHub Actions regression success is not an original plugin build or game test. Verify inventory names, DIAL/INFO, BOOK, QUST/CNAM, world/map, UOP overrides and installation before release. Keep issue #8 open until remaining candidates are triaged.
