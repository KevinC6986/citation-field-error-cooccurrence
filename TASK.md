# Task: Field-error co-occurrence across three models

## Goal

Create a small descriptive appendix figure showing (1) how many bibliographic fields are wrong in each generated citation and (2) which two-field error combinations are most common. Analyze the native-XML citations from Qwen2.5-32B, Mistral-Small-24B, and Gemma4-31B using the same rules. This is a CPU-only analysis of final labels. Do not run a model, call an API, or re-verify citations.

## Inputs

All required files are in data/ beside this instruction:

- data/final_labels_qwen.csv
- data/final_labels_mistral.csv
- data/final_labels_gemma.csv

Each file has one row per generated citation, a unique key within that model, and final labels for title, authors, venue, year, and DOI. Use title_label, authors_label, venue_label, year_label, and doi_label. Do not use the older verifier files or the *_label_intent columns. The unit is a generated citation (one model + key); do not deduplicate by content_hash.

## Label rules and analysis sample

- Define a field-error indicator as 1 only when its *_label is wrong and 0 when correct. A DOI labeled omitted means no DOI was written; under the current verification rule it is not a wrong DOI. Assign its error indicator 0 and report the omission count separately.
- Exclude a citation from the primary analysis if any of its five labels is uncertain or missing. Do not treat uncertain as correct or wrong.
- n_wrong_fields is the sum of the five error indicators. A citation with 0 wrong fields may still have an omitted DOI; call the category 0 wrong fields, not all five fields explicitly correct.
- Apply these rules separately to each model, using one consistent complete-case sample for the distribution and pair analyses.

## Calculations

1. For each model, count citations with exactly 0, 1, 2, 3, 4, and 5 wrong fields. Report counts and percentages within that model's complete-case sample.
2. Among citations with exactly two wrong fields, count all ten unordered field pairs. For each model and pair, report the count, percentage among that model's exactly-two-error citations, and percentage among that model's complete-case citations. This is the primary meaning of two-field error combination in the figure.
3. Separately, for every model and unordered pair, count citations in which both fields are wrong regardless of how many other fields are wrong. Report the count and percentage of that model's complete-case citations in a separate CSV. Label this pairwise co-occurrence in any error profile; do not mix it with the exactly-two-error counts.
4. Make one appendix-ready figure with consistent field order and colors across models. Suggested layout: grouped bars for the 0-5 error-count distribution (percentages by model) plus a model-by-pair heatmap for exactly-two-error combinations (percentages among exactly-two-error citations). Show each model's complete-case n in the caption. A compact table is acceptable if clearer, but still provide the numeric CSVs.
5. Write 3-5 sentences describing the main patterns across models, the number excluded for uncertain/missing labels, and the DOI omission rate in each model. Keep the description factual; no significance tests or causal claims are needed.

## Deliverables

- A runnable Python script in this folder, for example analyze_field_error_cooccurrence.py. Read the supplied data/ files relative to the script and create results/ if needed.
- results/error_count_distribution.csv with model, n_wrong_fields, count, and pct_complete_case.
- results/exactly_two_field_pairs.csv with model, field_1, field_2, count, pct_exactly_two, and pct_complete_case.
- results/pairwise_cooccurrence_any.csv with model, field_1, field_2, count_both_wrong, and pct_complete_case.
- results/field_error_cooccurrence.pdf plus a PNG preview, or an appendix-ready table if it is clearer.
- results/summary.md with a short results paragraph and suggested appendix caption.

## Sanity checks

- Qwen: 5,942 rows and unique keys; 102 incomplete; 5,840 complete-case; 2,355 DOI omissions in the full file.
- Mistral: 5,263 rows and unique keys; 172 incomplete; 5,091 complete-case; 1,253 DOI omissions in the full file.
- Gemma: 5,910 rows and unique keys; 99 incomplete; 5,811 complete-case; 3,325 DOI omissions in the full file.
- For each model, the six error-count bins must sum to its complete-case n.
- For each model, the ten exactly-two-pair counts must sum to its n_wrong_fields=2 bin. Their pct_exactly_two values should sum to about 100%, allowing for rounding.
- For each model and pair, pairwise_cooccurrence_any must have at least as many citations as exactly_two_field_pairs.
- Do not pool or average the three models in the main figure or summary.
