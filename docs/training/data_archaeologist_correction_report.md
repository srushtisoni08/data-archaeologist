# Data Archaeologist — Corrections to 16 Flagged Training Examples

## Scope
Revised examples: 3, 6, 8, 9, 10, 17, 20, 30, 47, 57, 59, 70, 74, 75, 89, 96.

The original prompts were retained verbatim. The revised completions were rewritten against the evidence in those prompts and the existing manual audit notes.

## Correction policy
- Claims explicitly stated in the prompt are labelled as verified facts.
- Explanations not demonstrated by the prompt are labelled as inferred hypotheses.
- Confidence is calibrated to the evidence, not to the fluency or specificity of the original answer.
- Unsupported statistical significance, causality, MNAR classifications, key declarations, entity matches, and automatic imputations were removed or downgraded.
- Limitations explicitly identify missing codebooks, source logs, row-level checks, sample size, domain rules, and lineage evidence where relevant.
- Recommended actions preserve raw data and defer irreversible changes until source evidence is available.

## Per-example change summary
| Example | Main correction |
|---:|---|
| 3 | Removed unsupported imputation/capping; sentinel and composite-key claims are unresolved hypotheses. |
| 6 | Removed attribution of the 37.5x speedup to one change; type migration intent is unproven; monetary FLOAT concern is conditional. |
| 8 | Replaced proven-MNAR claim with dropout-associated missingness; requires MAR/MNAR sensitivity analysis; quarantines Treatment C pending protocol review. |
| 9 | Removed unsupported p < 0.05 claim; duplicate transaction IDs and orphan references remain investigation candidates; no hash-based primary key. |
| 10 | Replaced MNAR/ethical-causation claim with observed redaction association; framework conflict may be many-to-many or annotation conflict. |
| 17 | Corrected false claim that all fuel nulls occur after lap 59; removed unsupported tire mapping and deduplication/key declarations. |
| 20 | Removed rolling-mean imputation recommendation because feature lineage may be circular; explicitly noted summary/sample contradiction. |
| 30 | Removed ID digit-stripping and inferred dates; rows 1–2 remain possible duplicate event; currency conversion requires FX metadata. |
| 47 | Prefix mapping remains a candidate; imputed values retain provenance and uncertainty; no claim that Wave 3 is genuinely complete. |
| 57 | Name/date match remains candidate only; polymorphic key needs row-level joins; negative amounts are not fraud evidence; avoids SSN linkage. |
| 59 | Right-censoring distinguished from leakage; battery increases not assumed impossible; duplicate policy requires row grain; target window must be chronological. |
| 70 | Exact sample duplicates are not declared duplicate listings; negative views flagged; variable-depth category hierarchy preserved; parse errors retained. |
| 74 | relation_code 9 remains unresolved; year-only dates preserve precision; ambiguous date and household linkage are not fabricated. |
| 75 | Four production rows cannot establish drift; unknown categories handled deterministically; zero-imputation risk is stated without asserting fraud impact. |
| 89 | Null exit on donate-confirm does not imply conversion; 24-hour inversion cause remains unconfirmed; session_uuid only candidate key for this fragment. |
| 96 | Replaced imprecise 95.5% collision wording; high exact-second frequency is not proof of truncation; no guessed Account_ID composite key. |

## Removal decision
No examples were removed. All 16 prompts contain enough evidence to produce a bounded, cautious response. Where the prompt does not support a definitive answer, the revised completion explicitly says so and recommends validation rather than inventing a conclusion.

## Validation
- Original prompt text retained for all 16 revised examples.
- Revised subset contains 16 JSONL records.
- Full candidate contains 100 JSONL records, with only the 16 flagged completions replaced.
- Every completion parses as JSON and contains the required fields: finding, classification, evidence, reasoning, confidence, limitations, recommended_next_action.
- This is a semantic correction pass for the 16 flagged examples only. The remaining 82 examples have not been manually validated. Examples 23 and 76 remain unchanged with their previously documented caveats.
