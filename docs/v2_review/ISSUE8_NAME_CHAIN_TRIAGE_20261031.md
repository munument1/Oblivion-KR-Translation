# Issue #8: source-anchored name chain triage (2026-10-31)

This is **static review evidence**, not a patch list. No mass substitution is authorized.
Source input SHA-256:
- \`canonical_translation_v2.csv\` (47,227 rows): \`57306d322a0cca7d18b452ecb5d0f38bc594d23ed2e6b6040a3eee828c96ca23\`
- \`canonical_locations_v2.csv\` (3,938 rows including unofficial sources): \`aa732f074ac1e4782cdcddc304351756ab90d093052113ae56a9df7e013f0724\`

The CI artifact from [PR #12 / run 41181729401](https://github.com/munument1/Oblivion-KR-Translation/actions/runs/41181729401/artifacts/13034892891) contains the **730 source-anchored candidate rows**, with English, Korean, record type, FormID, field, EditorID, occurrence, source and SHA-256. The numbers below are not unique source strings, nor counts of proven mistranslations.

| English concept | Total | Different from glossary | Matches glossary | No recognized KO phrase | Multiple KO variants |
|---|---:|---:|---:|---:|---:|
| Cheydinhal | 298 | 240 | 55 | 3 | 0 |
| Mythic Dawn | 157 | 106 | 49 | 2 | 0 |
| Mysterium Xarxes | 59 | 47 | 3 | 9 | 0 |
| Knights of the Nine | 37 | 31 | 4 | 1 | 1 |
| Crusader equipment (targeted English) | 179 | 173 | 5 | 0 | 1 |
| **Total** | **730** | **597** | **116** | **15** | **2** |

## Priority 1: Cheydinhal — glossary vs visible world conflict

- The confirmed glossary says \`Cheydinhal → 체이딘할\`, while actual \`Oblivion.esm/WRLD/0001C31C/FULL\` is \`셰이딘홀\`, and city gate/world/map locations also use \`셰이딘홀\`.
- Of 298 matches, observed KO phrase counts are \`셰이딘홀\` 148, \`쉐이딘홀\` 65, \`체이딘홀\` 27, \`체이딘할\` 55, 3 unrecognized.
- Contrast an actual dialogue topic \`Oblivion.esm/DIAL/0001FE63/FULL\` = \`셰이딘홀\` against equipment \`Oblivion.esm/ARMO/000352C9/FULL\` = \`체이딘할 방패\` and book \`BOOK/00024561/FULL\` = \`체이딘할 안내서\`.
- **Decision required before modification:** choose one naming policy for map, armor/FULL, quest journal, books and dialogue; then adjust the glossary rather than blindly enforcing its current \`CONFIRMED\` entry. Do not edit editor IDs containing Cheydinhal where the English displayed text does not.

## Priority 2: main quest book/group chains

**Mythic Dawn:** 157 hits. Current \`Oblivion.esm/BOOK/00022B04..00022B07/FULL\` use \`미씩 던\` (four volumes, plus inconsistent \`논평집/주석서\` book-title suffixes); \`DIAL/00023F8E/FULL\` = \`미씩 던\`, while gear/class FULL labels mostly use \`미식 던\`. Compare journal \`QUST/CNAM\` before selecting a canonical form. Changing only noun spelling will not resolve the Commentaries title inconsistency.

**Mysterium Xarxes:** 59 hits. Book \`BOOK/00005599/FULL\` and \`BOOK/0008B60A/FULL\`, dialogue topic \`DIAL/0000918D/FULL\`, and many journal references use \`자서스의 신비\` against confirmed glossary \`작시스의 신비\`. Notably three BOOK-body appearances already use \`작시스의 신비\`. The nine "no recognized KO phrase" rows must be read in full; paraphrases and omissions are not automatically errors.

## Priority 3: Knights of the Nine / Crusader gear

**Knights of the Nine:** 37 hits. The title \`Knights.esp/BOOK/01000ED2/FULL\` is \`나인 디바인 기사단\`, its BOOK body contains \`나인의 기사단\`; \`DIAL/01002BD2/FULL\` and much dialogue also use \`나인 디바인 기사단\`. This is a **same-book title/body discrepancy**, stronger evidence for targeted review than simple glossary count.

**Crusader set:** 179 source matches. Representative \`Knights.esp/DIAL/01002A3F/FULL\` is \`성전사의 장화\`, \`DIAL/01002AED/FULL\` is \`성전사 방패\`. Actual equipment names, journals, dialogue and \`CELL\` locations mostly prefer \`성전사\` (173 occurrences against five \`성기사\`), while glossary has multiple \`... of the Crusader → 성기사의 ...\` SEED entries. Review the complete set as an entity, not each adjective in isolation.

## Rules for subsequent changes

1. Compare source plugin + FormID + EditorID + type/field + English string, not only Korean substring. Distinguish actual player-visible records from dummy/test and edited/unofficial overrides.
2. Choose a canonical name **per entity**. For objects, record the FULL name. For dialogue, books and QUST/CNAM, preserve Korean particles, markup, placeholders and existing line break semantics.
3. Prepare a selective patch with before/after SHA and exact count; reject source drift. Audit \`build_obcjk_release.py\` and the separate location/unofficial build paths; don't assume base-game corrections propagate into unofficial DLC.
4. Run regression tests, produce actual original-ESM/ESP build outputs, then test the world map, inventory, character dialogue, book pages and journal in game. CI is not game verification.
5. The already-open #9 Crate, #10 Amber equipment, and #11 Sancre Tor are source-scoped Draft PRs; do not confuse their changes with this audit or the unmodified canonical source.

**Status:** #12 QA successful, 730-row candidate artifact uploaded. No canonical translation change, no full installer/gameplay smoke test, no release.
