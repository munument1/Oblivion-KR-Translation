# Issue #8 — reporter terminology policy (2026-10-31)

**Owner decision:** Use the issue #8 reporter's active glossary spellings for each named entity, rather than selecting the most frequent legacy translation. This resolves the previously undecided terminology question in PR #12.

| English | Canonical Korean | Review status |
| --- | --- | --- |
| Cheydinhal | 체이딘할 | PR #14 text and locations |
| Ayleid / Ayleids | 에일리드 | Draft #16 |
| Mythic Dawn | 미식 던 | PR #14 text and PR #13 book 2 title |
| Crucible (SI place) | 크루시블 | Draft #16 |
| Mysterium Xarxes | 작시스의 신비 | PR #14 text |
| Knights of the Nine | 나인의 기사단 | PR #14 text |
| Jauffre | 죠프리 | Draft #16 |
| Sancre Tor | 생크 토르 | PR #11 locations and marker |
| Staff of Sheogorath | 쉐오고라스의 지팡이 | Draft #16 |
| Gatekeeper (named creature) | 게이트키퍼 | Draft #17; Shivering Isles only |
| Amber (SI craft material) | 호박석 | PR #10 equipment |
| Crusader equipment | 성기사 | PR #14 equipment and shrine references |
| Arquen | 아퀜 | Draft #16 |
| Modryn Oreyn | 모드윈 오레인 | Draft #16 |
| Vicente Valtieri | 비센테 발티에리 | Draft #16 |
| Mankar Camoran | 맨카 캐모런 | Draft #16/#19 |
| Golden Saint | 골든 세인트 | Draft #16 |
| Dark Seducer | 다크 세듀서 | Draft #16 |
| Marauder | 습격자 | Draft #17 |

**Source decisions:** Bands of the Chosen is aligned with the exact item FULL name in Draft #17. The earlier SEED `Cupboard → 선반` was a mistranslation; the source-reviewed `Cupboard → 찬장` correction is in Draft #18. `Shelf/Shelves → 선반` stays unchanged. Anvil is 앤빌 as the city and 모루 as the tool.

## Already covered

- #9: exact Crate CONT/FULL 38 corrections.
- #10: exact Amber equipment 151 corrections.
- #11: Sancre Tor real location and marker 13 corrections.
- #12: read-only source-anchored audit of 730 high-priority rows.
- #13: source-scoped Mythic Dawn Commentaries volume 2 title, now in canonical 미식 던.
- #14: 574 terminology hits across 561 distinct official text records plus 23 source-anchored location/marker records. Stacked on #11. Existing canonical text CSV remains byte-identical; edited output is assembled with original hash/record guards at build time.

**Not automatically fixed:** candidate records that omit an entity naturally, the issue's wider 631 name mentions outside targeted source-backed terms, or potentially ambiguous NPC/common-noun contexts. Verify exact English, source plugin, FormID, field, occurrence, markup and Korean grammar before editing. Glossary is authoritative for *name choice*, but not evidence that every source occurrence requires an explicit Korean name.

## Release validation

GitHub Actions regression success is not an original plugin build or game test. Verify inventory names, DIAL/INFO, BOOK, QUST/CNAM, world/map, UOP overrides and installation before release. Keep issue #8 open until remaining candidates are triaged.


## Subsequent source-backed continuation (2026-10-31)

- [Draft #15](https://github.com/munument1/Oblivion-KR-Translation/pull/15): read-only source audit; 1,503 named-term occurrences across the published official canonical and location CSVs. [Inspectable artifact](https://github.com/munument1/Oblivion-KR-Translation/actions/runs/41182797631/artifacts/13035697528).
- [Draft #16](https://github.com/munument1/Oblivion-KR-Translation/pull/16): 424 name corrections in official-text translations (Ayleid 173, Crucible 74, Jauffre 29, Staff of Sheogorath 3, Arquen 10, Modryn Oreyn 21, Vicente Valtieri 15, Mankar Camoran 19, Golden Saint 39, Dark Seducer 41). One additional physical location CELL, Modryn Oreyn's House, changes Unicode and NUL-terminated UTF-8 hex. Full regression **PASS**.
- [Draft #17](https://github.com/munument1/Oblivion-KR-Translation/pull/17): original-identity-scoped corrections of the Shivering Isles named Gatekeeper (231), Marauder enemy / quest name (16), and Bands of the Chosen (25) to match the real ARMO FULL name 선택받은 자의 팔찌. Full regression **PASS**.
- [Draft #18](https://github.com/munument1/Oblivion-KR-Translation/pull/18) resolves the Cupboard SEED error with 48 base CONT/FULL labels plus 2 Thieves Guild QUST entries and 1 book furnishing line, while preserving real Shelves. It updates the project glossary Cupboard entry from `선반 / SEED` to `찬장 / CONFIRMED` with original-source justification. Full regression **PASS**.
- Source terms and references still missing recognized Korean wording, plus the issue's wider 631 name mentions, remain open for human/game verification. Do not treat all static flags as errors.

**Merge order for dependent code PRs:** #9 → #10 → #11 → #14 → #16 → #17 → #18 → #19. #12 and #15 are read-only independent audit PRs; #13 is a separate one-book title correction and must be retested with the stacked builder before release.

CI tests source data but cannot confirm a packaged EXE, obCJK runtime, or real gameplay. Do not claim completed release.

- [Draft #19](https://github.com/munument1/Oblivion-KR-Translation/pull/19) addresses previously missed or normalized-away names in 12 distinct source records (28 exact named-term replacements): Cheydinhal quest FULL typo; Mythic Dawn variant; Mysterium Xarxes main quest references and a book header; Mankar Camoran variant; 13 old Knights of the Nine mentions and 3 Crusader relic names in a single book body; a Knights quest journal reference. No other book markup or gameplay records are altered.
