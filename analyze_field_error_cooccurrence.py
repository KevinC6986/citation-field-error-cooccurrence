#!/usr/bin/env python3
"""Build the required CSVs and a six-page, table-based appendix PDF.

Each table cell is an exact-profile count and a percentage of that model's
complete-case citations. The five field-combination pages include the
additional 1-, 3-, 4-, and 5-error analysis requested after TASK.md.
"""

from __future__ import annotations

import csv
import itertools
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
EXTRA = RESULTS / "extensions"
FIELDS = ("title", "authors", "venue", "year", "doi")
PAIRS = tuple(itertools.combinations(FIELDS, 2))
MODELS = (
    ("Qwen2.5-32B", "qwen"),
    ("Mistral-Small-24B", "mistral"),
    ("Gemma4-31B", "gemma"),
)
EXPECTED = {
    "qwen": (5942, 102, 5840, 2355),
    "mistral": (5263, 172, 5091, 1253),
    "gemma": (5910, 99, 5811, 3325),
}
PAGE_W, PAGE_H = 920, 650
DARK = colors.HexColor("#182330")
MUTED = colors.HexColor("#5B6674")
NAVY = colors.HexColor("#263F70")
TEAL = colors.HexColor("#228A88")
LIGHT = colors.HexColor("#EEF3F7")
GRID = colors.HexColor("#D8E0E7")


def percent(numerator: int, denominator: int) -> float:
    return 100 * numerator / denominator if denominator else 0.0


def load_model(name: str, slug: str) -> dict:
    path = DATA / f"final_labels_{slug}.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"key", *(f"{field}_label" for field in FIELDS)}
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        rows = list(reader)

    keys = [row["key"] for row in rows]
    if any(not key for key in keys) or len(set(keys)) != len(keys):
        raise ValueError(f"{path}: keys must be nonempty and unique")

    allowed = {"correct", "wrong", "uncertain", ""}
    for line, row in enumerate(rows, start=2):
        for field in FIELDS:
            label = (row[f"{field}_label"] or "").strip().lower()
            possible = allowed | ({"omitted"} if field == "doi" else set())
            if label not in possible:
                raise ValueError(f"{path}:{line}: unexpected {field}_label={label!r}")
            row[f"{field}_label"] = label

    complete = [
        row for row in rows
        if all(row[f"{field}_label"] in (
            {"correct", "wrong", "omitted"} if field == "doi" else {"correct", "wrong"}
        ) for field in FIELDS)
    ]
    omissions = sum(row["doi_label"] == "omitted" for row in rows)
    observed = (len(rows), len(rows) - len(complete), len(complete), omissions)
    if observed != EXPECTED[slug]:
        raise ValueError(f"{path}: sanity counts {observed} do not match {EXPECTED[slug]}")

    profiles = [
        tuple(field for field in FIELDS if row[f"{field}_label"] == "wrong")
        for row in complete
    ]
    exact = Counter(profiles)
    bins = Counter(map(len, profiles))
    any_pair = Counter(
        pair for profile in profiles for pair in PAIRS if set(pair).issubset(profile)
    )
    assert sum(bins.values()) == len(complete)
    assert sum(exact[pair] for pair in PAIRS) == bins[2]
    assert all(any_pair[pair] >= exact[pair] for pair in PAIRS)
    for k in range(6):
        assert sum(exact[combo] for combo in itertools.combinations(FIELDS, k)) == bins[k]
    return {
        "name": name, "slug": slug, "total": len(rows), "excluded": len(rows) - len(complete),
        "n": len(complete), "doi_omitted": omissions, "bins": bins,
        "exact": exact, "any_pair": any_pair,
    }


def write_csv(path: Path, headers: tuple[str, ...], rows: list[tuple]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)


def write_results(data: list[dict]) -> None:
    distribution = []
    exact_two = []
    any_pairs = []
    extra = []
    for item in data:
        for k in range(6):
            count = item["bins"][k]
            distribution.append((item["name"], k, count, f"{percent(count, item['n']):.2f}"))
        for a, b in PAIRS:
            count = item["exact"][(a, b)]
            exact_two.append((item["name"], a, b, count,
                              f"{percent(count, item['bins'][2]):.2f}",
                              f"{percent(count, item['n']):.2f}"))
            both = item["any_pair"][(a, b)]
            any_pairs.append((item["name"], a, b, both,
                              f"{percent(both, item['n']):.2f}"))
        for k in (1, 3, 4, 5):
            for combo in itertools.combinations(FIELDS, k):
                count = item["exact"][combo]
                extra.append((item["name"], k, "+".join(combo), count,
                              f"{percent(count, item['bins'][k]):.2f}",
                              f"{percent(count, item['n']):.2f}"))

    write_csv(RESULTS / "error_count_distribution.csv",
              ("model", "n_wrong_fields", "count", "pct_complete_case"), distribution)
    write_csv(RESULTS / "exactly_two_field_pairs.csv",
              ("model", "field_1", "field_2", "count", "pct_exactly_two", "pct_complete_case"),
              exact_two)
    write_csv(RESULTS / "pairwise_cooccurrence_any.csv",
              ("model", "field_1", "field_2", "count_both_wrong", "pct_complete_case"),
              any_pairs)
    write_csv(EXTRA / "exact_error_profiles_1_3_4_5.csv",
              ("model", "n_wrong_fields", "wrong_fields", "count",
               "pct_within_error_count", "pct_complete_case"), extra)


def draw_text(pdf: canvas.Canvas, x: float, y: float, value: str,
              font: str = "Helvetica", size: float = 10, color=MUTED) -> None:
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    pdf.drawString(x, y, value)


def cell_text(pdf: canvas.Canvas, x: float, width: float, y: float,
              value: str, font="Helvetica", size=10, color=DARK) -> None:
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    text_width = stringWidth(value, font, size)
    pdf.drawString(x + (width - text_width) / 2, y, value)


def draw_table_page(pdf: canvas.Canvas, data: list[dict], k: int | None,
                    page_num: int) -> None:
    title = "Overview: number of wrong fields" if k is None else (
        f"Exactly {k} wrong field{'s' if k != 1 else ''}: field combinations"
    )
    draw_text(pdf, 54, 601, title, "Helvetica-Bold", 18, DARK)
    draw_text(pdf, 54, 579,
              "Qwen, Mistral, and Gemma | one observation per generated citation",
              "Helvetica", 10, MUTED)
    pdf.setStrokeColor(TEAL)
    pdf.setLineWidth(2.5)
    pdf.line(54, 561, 866, 561)

    if k is None:
        labels = [(str(i), None) for i in range(6)]
        explanation = "Each cell is the share of complete-case citations with that many wrong fields."
        left_header = "Wrong fields"
    else:
        labels = [(" + ".join(field.capitalize() if field != "doi" else "DOI"
                               for field in combo), combo)
                  for combo in itertools.combinations(FIELDS, k)]
        explanation = "Exact combination: listed fields are wrong; the other fields are not scored wrong."
        left_header = "Fields wrong"
    draw_text(pdf, 54, 540, explanation, "Helvetica", 9.5, MUTED)
    draw_text(pdf, 54, 524,
              "Values are percentages of all eligible citations for each model; counts are in parentheses.",
              "Helvetica", 9.5, MUTED)

    x0, top = 54, 503
    widths = (230, 194, 194, 194)
    xs = (x0, x0 + widths[0], x0 + widths[0] + widths[1],
          x0 + widths[0] + widths[1] + widths[2])
    header_h, row_h = 47, 30
    table_w = sum(widths)
    pdf.setFillColor(NAVY)
    pdf.rect(x0, top - header_h, table_w, header_h, fill=1, stroke=0)
    draw_text(pdf, x0 + 14, top - 28, left_header, "Helvetica-Bold", 10, colors.white)
    for i, item in enumerate(data):
        cell_text(pdf, xs[i+1], widths[i+1], top - 21, item["name"],
                  "Helvetica-Bold", 9, colors.white)
        cell_text(pdf, xs[i+1], widths[i+1], top - 36,
                  f"eligible n = {item['n']:,}", "Helvetica", 8.5, colors.white)

    for row_i, (label, combo) in enumerate(labels):
        y = top - header_h - (row_i + 1) * row_h
        pdf.setFillColor(colors.white if row_i % 2 == 0 else LIGHT)
        pdf.rect(x0, y, table_w, row_h, fill=1, stroke=0)
        draw_text(pdf, x0 + 14, y + 10, label, "Helvetica", 9.5, DARK)
        for model_i, item in enumerate(data):
            count = item["bins"][row_i] if k is None else item["exact"][combo]
            value = percent(count, item["n"])
            cell_text(pdf, xs[model_i+1], widths[model_i+1], y + 10,
                      f"{value:.2f}%  ({count:,})", "Helvetica-Bold", 9.5, DARK)
        pdf.setStrokeColor(GRID)
        pdf.setLineWidth(.5)
        pdf.line(x0, y, x0 + table_w, y)

    if k is not None and k < 5:
        y = top - header_h - (len(labels) + 1) * row_h
        pdf.setFillColor(colors.HexColor("#DCE9EE"))
        pdf.rect(x0, y, table_w, row_h, fill=1, stroke=0)
        draw_text(pdf, x0 + 14, y + 10, f"All exactly-{k} profiles",
                  "Helvetica-Bold", 9.5, DARK)
        for model_i, item in enumerate(data):
            count = item["bins"][k]
            cell_text(pdf, xs[model_i+1], widths[model_i+1], y + 10,
                      f"{percent(count, item['n']):.2f}%  ({count:,})",
                      "Helvetica-Bold", 9.5, DARK)
    elif k == 5:
        draw_text(pdf, 54, 388,
                  "There is only one five-field combination, so this row equals the 5-error row on page 1.",
                  "Helvetica", 9.5, MUTED)

    pdf.setStrokeColor(GRID)
    pdf.setLineWidth(.8)
    pdf.line(54, 94, 866, 94)
    draw_text(pdf, 54, 77, "Method: final labels only; uncertain or missing labels excluded.",
              "Helvetica", 8.5, MUTED)
    draw_text(pdf, 54, 63,
              "An omitted DOI is not a DOI error; 0 wrong fields may include an omitted DOI.",
              "Helvetica", 8.5, MUTED)
    draw_text(pdf, 54, 42,
              "Complete-case n: Qwen 5,840; Mistral 5,091; Gemma 5,811.",
              "Helvetica", 8.5, DARK)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8.5)
    pdf.drawRightString(866, 42, f"{page_num} / 6")
    pdf.showPage()


def draw_pdf(data: list[dict]) -> None:
    path = RESULTS / "field_error_cooccurrence.pdf"
    pdf = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    pdf.setTitle("Citation field-error combinations across three models")
    pdf.setAuthor("Field-error co-occurrence analysis")
    draw_table_page(pdf, data, None, 1)
    for page_num, k in enumerate(range(1, 6), start=2):
        draw_table_page(pdf, data, k, page_num)
    pdf.save()

    poppler = shutil.which("pdftoppm")
    if not poppler:
        raise RuntimeError("PDF created; pdftoppm is needed for the PNG preview")
    result = subprocess.run(
        [poppler, "-f", "1", "-l", "1", "-r", "180", "-png", "-singlefile",
         str(path), str(RESULTS / "field_error_cooccurrence")],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(f"PNG preview failed: {result.stderr[-2000:]}")


def draw_core_appendix_table(data: list[dict]) -> None:
    """One-page table containing just the two results requested in TASK.md."""
    path = RESULTS / "field_error_cooccurrence_task_only.pdf"
    pdf = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    pdf.setTitle("Field-error co-occurrence: task-only appendix table")
    pdf.setAuthor("Field-error co-occurrence analysis")
    draw_text(pdf, 54, 608, "Field-error co-occurrence: appendix table",
              "Helvetica-Bold", 17, DARK)
    draw_text(pdf, 54, 588, "Required overview and exactly-two-error combinations across three models",
              "Helvetica", 9.5, MUTED)
    pdf.setStrokeColor(TEAL)
    pdf.setLineWidth(2.5)
    pdf.line(54, 576, 866, 576)

    x0, widths = 54, (230, 194, 194, 194)
    xs = (x0, x0 + widths[0], x0 + widths[0] + widths[1],
          x0 + widths[0] + widths[1] + widths[2])
    model_colors = (NAVY, TEAL, colors.HexColor("#C86B45"))

    def header(top: float, left_label: str, exactly_two: bool = False) -> None:
        pdf.setFillColor(NAVY)
        pdf.rect(x0, top - 24, widths[0], 24, fill=1, stroke=0)
        draw_text(pdf, x0 + 10, top - 16, left_label,
                  "Helvetica-Bold", 9, colors.white)
        for i, item in enumerate(data):
            pdf.setFillColor(model_colors[i])
            pdf.rect(xs[i+1], top - 24, widths[i+1], 24, fill=1, stroke=0)
            denominator = item["bins"][2] if exactly_two else item["n"]
            cell_text(pdf, xs[i+1], widths[i+1], top - 16,
                      f"{item['name']} (n={denominator:,})",
                      "Helvetica-Bold", 8.5, colors.white)

    def body_row(y: float, index: int, label: str, values: list[str]) -> None:
        pdf.setFillColor(colors.white if index % 2 == 0 else LIGHT)
        pdf.rect(x0, y, sum(widths), 21, fill=1, stroke=0)
        draw_text(pdf, x0 + 10, y + 6, label, "Helvetica", 8.5, DARK)
        for i, value in enumerate(values):
            cell_text(pdf, xs[i+1], widths[i+1], y + 6,
                      value, "Helvetica-Bold", 8.5, DARK)
        pdf.setStrokeColor(GRID)
        pdf.setLineWidth(.4)
        pdf.line(x0, y, 866, y)

    draw_text(pdf, 54, 554, "A  Number of wrong fields per citation",
              "Helvetica-Bold", 10.5, DARK)
    draw_text(pdf, 54, 539, "% of each model's complete-case citations; count in parentheses",
              "Helvetica", 8.5, MUTED)
    top_a = 527
    header(top_a, "Wrong fields")
    for k in range(6):
        y = top_a - 24 - (k + 1) * 21
        values = [f"{percent(item['bins'][k], item['n']):.2f}% ({item['bins'][k]:,})"
                  for item in data]
        body_row(y, k, str(k), values)

    draw_text(pdf, 54, 356, "B  Exactly-two-error field combinations",
              "Helvetica-Bold", 10.5, DARK)
    draw_text(pdf, 54, 341, "% among that model's exactly-two-error citations; count in parentheses",
              "Helvetica", 8.5, MUTED)
    top_b = 329
    header(top_b, "Only these two fields wrong", exactly_two=True)
    for index, pair in enumerate(PAIRS):
        y = top_b - 24 - (index + 1) * 21
        label = " + ".join(field.capitalize() if field != "doi" else "DOI"
                           for field in pair)
        values = [
            f"{percent(item['exact'][pair], item['bins'][2]):.2f}% "
            f"({item['exact'][pair]:,})"
            for item in data
        ]
        body_row(y, index, label, values)

    pdf.setStrokeColor(GRID)
    pdf.setLineWidth(.8)
    pdf.line(54, 79, 866, 79)
    draw_text(pdf, 54, 65,
              "Complete-case n: Qwen 5,840; Mistral 5,091; Gemma 5,811. Exactly-two n: 628; 629; 761.",
              "Helvetica", 8, DARK)
    draw_text(pdf, 54, 51,
              "Uncertain or missing labels excluded; an omitted DOI is not counted as a DOI error.",
              "Helvetica", 8, MUTED)
    pdf.save()

    poppler = shutil.which("pdftoppm")
    if not poppler:
        raise RuntimeError("Core PDF created; pdftoppm is needed for the PNG preview")
    result = subprocess.run(
        [poppler, "-f", "1", "-l", "1", "-r", "180", "-png", "-singlefile",
         str(path), str(RESULTS / "field_error_cooccurrence_task_only")],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Core PNG preview failed: {result.stderr[-2000:]}")


def write_summary(data: list[dict]) -> None:
    qwen, mistral, gemma = data
    paragraph = (
        f"Five-field error profiles occurred in {percent(qwen['bins'][5], qwen['n']):.1f}% "
        f"of Qwen citations, {percent(mistral['bins'][5], mistral['n']):.1f}% of Mistral "
        f"citations, and {percent(gemma['bins'][5], gemma['n']):.1f}% of Gemma citations "
        "in the complete-case samples. "
        f"The 0-wrong-fields category comprised {percent(qwen['bins'][0], qwen['n']):.1f}%, "
        f"{percent(mistral['bins'][0], mistral['n']):.1f}%, and "
        f"{percent(gemma['bins'][0], gemma['n']):.1f}%, respectively; it can include "
        "citations with an omitted DOI. "
        "Authors plus DOI was the most frequent exactly-two-error combination in all three "
        f"models ({qwen['exact'][('authors', 'doi')]:,}, "
        f"{mistral['exact'][('authors', 'doi')]:,}, and "
        f"{gemma['exact'][('authors', 'doi')]:,} citations, respectively). "
        f"Excluded citations with uncertain or missing labels numbered {qwen['excluded']:,}, "
        f"{mistral['excluded']:,}, and {gemma['excluded']:,}; DOI omissions in the full files "
        f"numbered {qwen['doi_omitted']:,} ({percent(qwen['doi_omitted'], qwen['total']):.1f}%), "
        f"{mistral['doi_omitted']:,} ({percent(mistral['doi_omitted'], mistral['total']):.1f}%), "
        f"and {gemma['doi_omitted']:,} ({percent(gemma['doi_omitted'], gemma['total']):.1f}%), "
        "respectively."
    )
    caption = (
        "Field-error profiles across three models. Page 1 gives the distribution of 0-5 wrong "
        "fields. Pages 2-6 list every exact field combination for 1, 2, 3, 4, and 5 wrong fields, "
        "respectively. Each cell shows the percentage of that model's complete-case citations "
        "followed by the citation count in parentheses; combination totals reconcile "
        "with page 1. Complete-case n: Qwen 5,840, Mistral 5,091, Gemma 5,811. "
        "DOI omission is not scored as a DOI error."
    )
    core_caption = (
        "Field-error co-occurrence across three models. Table A shows the percentage of "
        "complete-case citations with exactly 0-5 wrong fields. Table B shows each pair's "
        "percentage among citations with exactly two wrong fields. Complete-case n: "
        "Qwen 5,840, Mistral 5,091, Gemma 5,811. DOI omission is not scored as a DOI error."
    )
    (RESULTS / "summary.md").write_text(
        "# Field-error co-occurrence\n\n## Results\n\n" + paragraph +
        "\n\n## Task-only appendix-table caption\n\n" + core_caption +
        "\n\n## Full six-page PDF caption\n\n" + caption + "\n", encoding="utf-8"
    )


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    EXTRA.mkdir(exist_ok=True)
    data = [load_model(name, slug) for name, slug in MODELS]
    write_results(data)
    draw_pdf(data)
    draw_core_appendix_table(data)
    write_summary(data)
    for item in data:
        print(f"{item['name']}: {item['n']:,} complete; "
              f"{item['excluded']:,} excluded; {item['doi_omitted']:,} DOI omitted")
    print(f"Wrote task-only table, six-page table PDF, and CSVs to {RESULTS}")


if __name__ == "__main__":
    main()
