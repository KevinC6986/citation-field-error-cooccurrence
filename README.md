# Citation field-error co-occurrence

**For the original assignment, present `results/field_error_cooccurrence_task_only.pdf`.** It is a one-page, compact appendix table with the 0-5 error distribution and all ten exactly-two-error pairs. `TASK.md` explicitly allows a compact table instead of a graph. **For the later extension, present `results/field_error_cooccurrence.pdf`.** It has all six table pages requested in the follow-up.

| PDF page | Table |
| --- | --- |
| 1 | Number of wrong fields per citation: 0, 1, 2, 3, 4, or 5. |
| 2 | Each exact one-field error combination. |
| 3 | Each exact two-field error combination. |
| 4 | Each exact three-field error combination. |
| 5 | Each exact four-field error combination. |
| 6 | The exact five-field error combination. |

In every table, the three model columns show **the percentage of that model's complete-case citations**, followed by the citation count in parentheses. An *exact combination* means the listed fields are wrong and the other fields are not scored wrong. The total rows on pages 2-5 match their rows on page 1; page 6 has only one possible combination. An omitted DOI counts as no DOI error, so a 0-wrong-fields citation may have no DOI.

## Project files

| Location | Purpose |
| --- | --- |
| `TASK.md` | Original assignment. |
| `data/final_labels_*.csv` | Supplied final-label data for Qwen, Mistral, and Gemma. |
| `analyze_field_error_cooccurrence.py` | Runnable source that reads the data and produces all tables, CSVs, summary, PDF, and PNG. |
| `build_all.py` | Short one-command entry point; runs the analysis script. |
| `requirements.txt` | Python package needed to rebuild. |
| `results/` | Required outputs at the paths named by `TASK.md`. |
| `results/extensions/` | Added CSV for the exact 1-, 3-, 4-, and 5-field combinations. |

### Required outputs

- `results/error_count_distribution.csv`: 0-5 wrong fields per citation, by model.
- `results/exactly_two_field_pairs.csv`: every exact two-error pair, with the denominators required by `TASK.md`.
- `results/pairwise_cooccurrence_any.csv`: both fields wrong, allowing other errors too.
- `results/field_error_cooccurrence.pdf`: all six tables in one document, including the required results and later extensions.
- `results/field_error_cooccurrence.png`: preview of its first page.
- `results/summary.md`: factual results and captions for both PDF versions.

The optional `results/field_error_cooccurrence_task_only.pdf` and its PNG preview provide a compact, one-page version of just the original assignment. Its first table uses the complete-case denominator; its exactly-two table uses the exactly-two-error denominator.

The additional `results/extensions/exact_error_profiles_1_3_4_5.csv` gives counts, percentages within each exact error-count group, and percentages of the model's complete-case sample.

## Edit and rebuild

Edit `analyze_field_error_cooccurrence.py` to change labels, styling, table layout, or calculations, then run from this folder:

```bash
python3 -m pip install -r requirements.txt
python3 build_all.py
```

The PNG previews also require Poppler's `pdftoppm` command. Rebuilding replaces the files in `results/`. Both PDFs are vector-based, so a vector editor can make visual changes to a copy, but edits made directly to a PDF do not update the CSVs or source code.

The original assignment asks for the overview and exactly-two analysis; the 1-, 3-, 4-, and 5-field combination tables are the later extension.
