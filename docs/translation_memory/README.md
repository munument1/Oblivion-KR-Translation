# 오블리비언 번역 소스 등급 및 재사용 규칙

**두 번째 대사 교정:** [블로티드 플로트 점거 및 테라니스 성 탈출 대사 원문 대조](manual_source_review_round2.json)로 2행을 추가 교정했습니다. 전체 Canonical CSV는 여전히 역사적 입력이며 자동 재사용 금지입니다.

**추가 의미 교정:** 원문 대조로 확인한 INFO 대사 2건의 교정 내역은 [검수 기록](manual_source_review_fixes.json)에 따로 고정합니다. 영어 원문과 이전 한국어, FormID, 원본 SHA가 모두 일치할 때만 적용하며 과거 번역 전체를 자동 대체하지 않습니다.

**컬럼 동기화:** 기존 OCRP 12행의 `obcjk_unicode_text` 열도 정확한 이전 문구와 원문 해시가 맞을 때만 갱신합니다. 변경 후보 파일 SHA를 사전에 고정하며, 전체 본편 회귀 검사에서 실패하면 커밋하지 않습니다.

**실제 canonical 수정:** 2026-11-03 OCRP 검수 원문과 인코딩이 일치한 12행만 수정했습니다(47,227행 중 12행). 나머지 과거 초안은 검수 완료로 승격하지 않았습니다. [전후 해시·ID 보고서](ocrp_canonical_applied.json)와 [전체 위험 후보 감사](canonical_risk_audit.json) 및 [괄호 영문 12건 문맥 검토](english_gloss_triage_20261103.md)를 확인하세요.

**2026-11-03: 주의 — \`canonical_translation_v2.csv\`는 모드 번역용 검수 완료 메모리가 아닙니다.** 예전 초안과 확정 번역이 혼재한 대형 역사적 빌드 입력입니다. OCRP 번역에서 과거 문구의 영문 병기 42개, 영문 잔존 5개, 원문 의미 오류 8개를 확인했습니다. 직접 복사/일괄 재사용을 금지합니다.

## 역할을 구분하세요

- **역사적 기준**: \`canonical_translation_v2.csv\`, \`applied_translations_v2.csv\`, \`patch_translation_memory.csv\`. 비교·재현 목적의 원자료이며, 검수를 거치지 않고 새 모드의 한국어 후보에 자동 수록하지 마세요.
- **기존 본편 빌드에 실제 적용하는 값**: \`build_obcjk_release.py\`는 원본 CSV를 읽은 **후에** \`issue8_...\`, \`reviewed_semantics.py\` 등 소스 고정 교정을 인메모리로 적용합니다. 원본 CSV만 가져오면 이 검수 결과가 빠집니다. 검증 없이 본편 빌드 우선순위를 바꾸지 마세요.
- **독립 검수 이력**: \`docs/v2_review/source_snapshot/V2_SOL_FINAL_OVERRIDE.csv\`는 9,049개 v2 검수 항목을 기록합니다. 이후의 교정도 있어 이를 단독으로 최신 완성본이라 가정해서는 안 됩니다.
- **OCRP 고정 검수본**: \`mods/ocrp/translations_ocrp_1.3.csv\`, \`scripts_ocrp_1.3.csv\` 및 SHA-256 매니페스트, 교정 전후 기록은 대상 원본 ESP에 한해 검증한 자료입니다.

## 다음 번역 작업의 필수 게이트

1. 대상 ESP의 실제 영어 문구, 레코드 종류, FormID, 필드, 원본 해시를 확인합니다. 영어 문구만으로 자동 병합하거나 **서로 다른 모드의 6자리 FormID 접미부만으로 결합하지 않습니다.**
2. 정식 재사용 메모리에는 \`effective_source, record_type, raw_formid, field, old_english, korean, review_status=reviewed, review_source\`를 기록하고 \`scripts/reviewed_memory_gate.py\`를 통해 검사합니다. 근거 없는 항목은 \`draft\`로 분리합니다.
3. \`한국어(English)\`, 기타 잔존 영문, 숫자·장소·퀘스트 단계·원문 누락, \`%...\`·HTML·줄바꿈을 원문과 비교합니다. 영문 괄호를 제거했다는 것만으로 검수 완료 처리하지 않습니다.
4. 빌드 전 **검수된 단일 출처와 정확한 원본 바이트**를 고정하고, 변경되지 않아야 할 스크립트/레코드가 유지되는지 테스트합니다.

## Canonical 55건 일치 교정 도구

\`scripts/reconcile_canonical_ocrp.py\`는 OCRP 검수 기록의 55개 교정만 대상으로, **영문 원문 + 이전 한국어 문구가 모두 동일**하고 레코드 종류/필드/UTF-8 및 구형 인코딩 열까지 서로 모순 없는 경우에만 기존 canonical을 변경합니다. 원문 자체를 고치지 않고, 해시와 교정 대상 레코드 ID를 기록할 수 있습니다. 다른 초안 문구를 자동으로 합격시키지는 않습니다.

\`\`\`powershell
python scripts/reconcile_canonical_ocrp.py --check --report docs/translation_memory/ocrp_canonical_check.json
python scripts/reconcile_canonical_ocrp.py --apply --report docs/translation_memory/ocrp_canonical_applied.json
python -m unittest discover -s tests -p test_translation_memory_reconciliation.py -v
\`\`\`

\`--apply\`에서 해시·인코딩·구조 검사에 걸리면 **원본 CSV는 그대로 두고 중단**합니다. 43MB 이상의 CSV를 재직렬화하므로 기존 본편 테스트와 Git diff 확인 전에는 배포하지 마세요. 검사기나 교정 도구가 완벽한 번역을 자동 보장하지 않습니다.
