# Artifact Reviewer Skill

## Purpose
LLM-as-Judge quality review using 3-layer G-Eval scoring with bias mitigations.

## Triggers
- "review artifact"
- "QA check"
- "quality gate"
- "judge output"

## Scoring Framework
| Layer | Weight | Criteria |
|-------|--------|---------|
| Format compliance | 15% | DOCTYPE, no CDN, brand strings, responsive |
| Content quality | 55% | Accuracy, completeness, relevance, reasoning |
| Presentation | 30% | Readability, engagement, accessibility |

## Hard Blocks (auto-fail)
- missing_doctype
- external_assets
- answer_key_leakage
- native_radio_inputs
- unmanaged_js_runtime
- missing_brand_string

## Bias Mitigations
- Rationale written before score (think-before-score)
- 3 independent judge calls → majority vote
- Generator model ≠ judge model
- Explicit guard: "Do not rate longer answers higher"

## Pass Threshold
overall_score ≥ 7.0 AND no critical issues
