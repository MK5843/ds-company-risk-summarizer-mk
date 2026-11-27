# Case Study

## What a good summary is for this team, and why

The reader is a vetting analyst deciding whether a company is worth a closer look before reading the full record. They skim many companies, so a missed risk or a wrong number costs more than a missing detail. I defined a good summary as:

1. **Risks first.** Red flags come before the general overview.
2. **Accurate.** Every number matches the record and nothing is invented.
3. **Covers the key risks:** non-active status, defendant cases and claim amounts, net loss, negative equity, falling revenue, current ratio below 1, low interest coverage, negative operating cash flow, non-clean audit opinions, a shareholder above 50%, recently appointed directors, and thin or missing financial history.
4. **Short:** 80 to 120 words, readable in about 20 seconds.
5. **Honest about gaps:** it says when data is missing instead of guessing.

## What you built

- **Pipeline:** raw record, then a computed digest (key figures plus rule-based risk flags), then an LLM writes the summary from the digest. Code does the arithmetic and the flagging, so the model never calculates.
- **v1 (baseline):** the raw record with the prompt "write a short summary".
- **v2:** the digest and flags with strict rules: risks first, 80 to 120 words, use only the numbers given, say what is missing.
- **Provider and model:** `openai/gpt-oss-120b` on Groq, using Groq's OpenAI-compatible API. Both versions used the same model and settings. Every raw response is cached in `cache/`, so the summaries can be re-scored without new calls.
- **Companies:** all 50, for both versions.
- **AI tools used:**
  - **Claude (Anthropic), via the claude.ai chat interface:** to plan the approach, draft the Python scripts (digest, LLM wrapper, generation, evaluation), debug errors, and review my write-up. I ran every script myself, checked the outputs against the records, and made the decisions on the rubric, flags and thresholds.
  - **gpt-oss-120b:** the model inside the pipeline that writes the summaries (not a development aid).

## How you know whether it's good

| Version | Unsupported-number candidates | Avg risk recall | Avg words | In 80-120 words |
|---|---|---|---|---|
| v1 (raw record) | 80 in 29 of 50 summaries | 0.99 | 397 | 0 of 50 |
| v2 (digest + flags) | 3 in 3 of 50 summaries | 1.00 | 102 | 45 of 50 |

**Checks.**
1. A script extracts every number in each summary and looks for it in the raw record or the digest, allowing for percent form, RM millions, rounding tolerance and sign.
2. A recall script checks whether each rule-based risk flag is mentioned, by keyword or by its number.
3. I read summaries side by side and the printed context of flagged numbers.

**Reading the numbers.** The checker lists candidates, not confirmed errors.
- *v2:* I checked all 3. Two were false alarms ("above 4×" when interest coverage was 4.4 to 5.7, and "2023-24" as a year range). One was a real error: SYN-001472 said "over 30 years" for a company incorporated in November 1996, which is 29 years at the 31 December 2025 record date.
- *v1:* I read the first 15 of the 80 candidates. Most were whole-number rounding of ratios, year shorthand such as "2022-23", or derived growth rates that the record does not store. For SYN-000165, v1's revenue growth of 39% and 43% compares with actual growth of 38.3% and 43.1%, so one figure is slightly off. I did not audit the other 65, so the v1 count is an upper bound on its real errors.

**Failures found in v2.**
- SYN-001472: the model computed the company's age itself and got it wrong, because the digest had no age field.
- SYN-000302 and SYN-000333: "paid-up share capital", but the record only has a share capital field.
- SYN-000029: "modest profitability" is an interpretation that no digest field supports.
- SYN-000333: the summary ends with "total cases and defendant claims are recorded as zero", which echoes internal field names and tells the reader nothing.
- SYN-000333 also changed its name four months before the record date, which the digest does not flag.
- 5 of 50 summaries fall outside 80 to 120 words (74, 77, 121, 123 and 130 words).

**What worked.**
- For the three companies with no financial statements (SYN-000302, SYN-000333, SYN-001203), v2 states "No financial statements available" instead of guessing. v1 also handles them, but needs 135 to 195 words to do it.
- v2 puts the risks first and keeps whole-record clutter, such as directors tables and ratio tables, out of the summary.

**Limits.**
- Recall is saturated and does not separate the versions. v1 mentions every topic because it dumps the whole record, and v2 is handed the flags. The real difference is brevity and risk-first structure, which my metrics do not measure.
- The number check cannot catch a correct number in a wrong sentence, and it flags rounding and year shorthand.
- Keyword recall can miss paraphrases.
- This is one run of one model, with no human labels and no LLM judge.

## What you'd do next, and how you'd keep improving it

- **Fix the digest gaps found above:** add company age, flag recent name changes, and forbid unstated wording such as "paid-up" and "profitability" in the prompt.
- **Check claims sentence by sentence,** not just numbers, for example with a second model that verifies each statement against the digest.
- **Get real analysts to label** a sample of summaries, to learn which flags matter most and to tune the thresholds (revenue fall, interest coverage, recent appointments).
- **Keep a regression set** of tricky companies (no financials, defendant cases, name changes) and re-run it after every prompt or model change.
- **Add an LLM judge** from a different model, calibrated against the human labels, to scale review.
- **Monitor in production:** number-check failures, length drift, and analyst feedback on whether summaries helped.