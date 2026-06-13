import io
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from fpdf import FPDF


def sanitize_text(text: str) -> str:
    replacements = {
        "—": "-", "–": "-", "→": "->", "•": "*",
        "✓": "[ok]", "✗": "[x]", "η": "eta", "²": "2",
        "‘": "'", "’": "'", "“": '"', "”": '"',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", errors="replace").decode("latin-1")


PRFT_NAVY = (27, 54, 93)
PRFT_ORANGE = (232, 119, 34)
PRFT_DARK = (15, 30, 55)
PRFT_GRAY = (100, 110, 120)


class ReportPDF(FPDF):
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(12, 12, 12)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*PRFT_NAVY)
        self.cell(0, 5, "Perficient - Data Analysis Report", align="L")
        self.set_text_color(*PRFT_GRAY)
        self.cell(0, 5, sanitize_text(self.filename), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*PRFT_ORANGE)
        self.set_line_width(0.3)
        self.line(12, self.get_y(), 198, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*PRFT_GRAY)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}  |  Powered by Perficient AI", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*PRFT_NAVY)
        self.ln(2)
        self.cell(0, 8, sanitize_text(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*PRFT_ORANGE)
        self.set_line_width(0.6)
        self.line(12, self.get_y(), 70, self.get_y())
        self.ln(3)

    def subsection_title(self, title: str):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*PRFT_DARK)
        self.cell(0, 6, sanitize_text(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 4.5, sanitize_text(text))
        self.ln(1)

    def kpi_row(self, label: str, value: str):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 80, 80)
        self.cell(55, 5, label)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(30, 30, 30)
        self.cell(0, 5, str(value), new_x="LMARGIN", new_y="NEXT")

    def add_table(self, headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None):
        if col_widths is None:
            col_widths = [int(186 / len(headers))] * len(headers)

        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*PRFT_NAVY)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 6, sanitize_text(h), border=0, fill=True)
        self.ln()

        self.set_text_color(40, 40, 40)
        self.set_font("Helvetica", "", 7.5)
        for row_idx, row in enumerate(rows):
            if row_idx % 2 == 1:
                self.set_fill_color(240, 245, 250)
                fill = True
            else:
                self.set_fill_color(255, 255, 255)
                fill = True
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 5, sanitize_text(str(cell)[:30]), border=0, fill=fill)
            self.ln()
            self.set_draw_color(230, 230, 230)
            self.line(12, self.get_y(), 198, self.get_y())
        self.ln(2)

    def add_image_from_figure(self, fig, width: int = 165):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = tmp.name
        tmp.close()
        fig.savefig(tmp_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        self.image(tmp_path, w=width)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        self.ln(3)

    def check_space(self, needed: int = 40):
        if self.get_y() > (297 - 15 - needed):
            self.add_page()


def generate_correlation_heatmap(df: pd.DataFrame):
    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) < 2:
        return None
    fig, ax = plt.subplots(figsize=(7, 5))
    corr = numeric_df.corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(
        corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
        center=0, square=True, ax=ax, linewidths=0.5,
        cbar_kws={"shrink": 0.8}
    )
    ax.set_title("Correlation Matrix", fontsize=11, fontweight="bold", pad=10)
    plt.tight_layout()
    return fig


def generate_distribution_plots(df: pd.DataFrame):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return None
    n_cols = min(len(numeric_cols), 6)
    cols_to_plot = numeric_cols[:n_cols]
    n_rows = (n_cols + 2) // 3
    fig, axes = plt.subplots(n_rows, 3, figsize=(9, 2.5 * n_rows))
    axes = np.atleast_2d(axes).flatten()

    for i, col in enumerate(cols_to_plot):
        sns.histplot(df[col].dropna(), kde=True, ax=axes[i], color="#6366F1")
        axes[i].set_title(col, fontsize=8, fontweight="bold")
        axes[i].tick_params(labelsize=6)

    for i in range(n_cols, len(axes)):
        axes[i].set_visible(False)

    plt.tight_layout()
    return fig


def generate_missing_data_chart(df: pd.DataFrame):
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=True)
    if len(missing) == 0:
        return None
    fig, ax = plt.subplots(figsize=(7, max(2, len(missing) * 0.35)))
    bars = ax.barh(missing.index, missing.values, color="#EF4444", alpha=0.8)
    ax.set_xlabel("Missing Count", fontsize=8)
    ax.set_title("Missing Values by Column", fontsize=10, fontweight="bold")
    ax.tick_params(labelsize=7)
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.3, bar.get_y() + bar.get_height() / 2, f"{int(width)}", va="center", fontsize=7)
    plt.tight_layout()
    return fig


def generate_categorical_chart(df: pd.DataFrame):
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    good_cols = [c for c in cat_cols if 2 <= df[c].nunique() <= 10]
    if not good_cols:
        return None
    cols_to_plot = good_cols[:4]
    fig, axes = plt.subplots(1, len(cols_to_plot), figsize=(3.5 * len(cols_to_plot), 3.5))
    if len(cols_to_plot) == 1:
        axes = [axes]
    for i, col in enumerate(cols_to_plot):
        counts = df[col].value_counts().head(8)
        axes[i].pie(counts.values, labels=counts.index, autopct="%1.0f%%", textprops={"fontsize": 6})
        axes[i].set_title(col, fontsize=8, fontweight="bold")
    plt.tight_layout()
    return fig


def generate_pdf_report(analysis: dict, filename: str) -> bytes:
    pdf = ReportPDF(filename)
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- Title section with Perficient branding ---
    # Top line - orange accent
    pdf.set_fill_color(*PRFT_ORANGE)
    pdf.rect(0, 0, 210, 3, style="F")

    # Perficient name
    pdf.set_xy(12, 8)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*PRFT_NAVY)
    pdf.cell(0, 8, "PERFICIENT", new_x="LMARGIN", new_y="NEXT")

    # Thin separator
    pdf.set_draw_color(*PRFT_NAVY)
    pdf.set_line_width(0.3)
    pdf.line(12, pdf.get_y() + 1, 198, pdf.get_y() + 1)
    pdf.ln(6)

    # Report title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*PRFT_NAVY)
    pdf.cell(0, 10, "Data Analysis Report", align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*PRFT_GRAY)
    pdf.cell(0, 5, sanitize_text(f"File: {filename}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- Quick Summary Box ---
    raw = analysis["raw_kpis"]
    clean = analysis["clean_kpis"]
    y_start = pdf.get_y()
    pdf.set_fill_color(250, 250, 252)
    pdf.set_draw_color(230, 230, 235)
    pdf.rect(12, y_start, 186, 20, style="DF")
    # Orange left accent
    pdf.set_fill_color(*PRFT_ORANGE)
    pdf.rect(12, y_start, 2.5, 20, style="F")
    pdf.set_xy(18, y_start + 2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*PRFT_NAVY)
    pdf.cell(0, 5, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 4.5, sanitize_text(f"Rows: {raw['row_count']} -> {clean['row_count']}   |   Columns: {raw['column_count']} -> {clean['column_count']}   |   Issues Fixed: {len(analysis['cleaning_log'])}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.cell(0, 4.5, sanitize_text(f"Numeric: {clean['numeric_columns']}   |   Categorical: {clean['categorical_columns']}   |   Memory: {clean['memory_mb']} MB"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y_start + 22)

    # --- Section 1: Data Quality KPIs (same page) ---
    pdf.section_title("1. Data Quality")

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*PRFT_ORANGE)
    pdf.cell(93, 5, "Before Cleaning")
    pdf.cell(93, 5, "After Cleaning", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 50, 50)

    kpi_pairs = [
        ("Rows:", str(raw["row_count"]), str(clean["row_count"])),
        ("Columns:", str(raw["column_count"]), str(clean["column_count"])),
        ("Missing Cells:", f"{raw['missing_cells_total']} ({raw['missing_pct']}%)", f"{clean['missing_cells_total']} ({clean['missing_pct']}%)"),
        ("Duplicates:", str(raw["duplicate_rows"]), str(clean["duplicate_rows"])),
    ]
    for label, before, after in kpi_pairs:
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(30, 4.5, label)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(63, 4.5, before)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(30, 4.5, label)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(63, 4.5, after, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Cleaning log (compact)
    if analysis["cleaning_log"]:
        pdf.subsection_title("Cleaning Actions")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(50, 50, 50)
        for entry in analysis["cleaning_log"]:
            text = sanitize_text(f"  * [{entry['action']}] {entry['detail']}")
            pdf.cell(0, 4, text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # --- Section 2: Column Analysis ---
    pdf.check_space(50)
    pdf.section_title("2. Column Analysis")

    numeric_stats = [s for s in analysis["column_stats"] if "mean" in s]
    if numeric_stats:
        pdf.subsection_title("Numeric Columns")
        headers = ["Column", "Mean", "Median", "Std", "Min", "Max", "Outliers"]
        rows = [
            [s["name"][:15], f"{s['mean']:.2f}", f"{s['median']:.2f}", f"{s['std']:.2f}",
             f"{s['min']:.1f}", f"{s['max']:.1f}", str(s.get("outlier_count", 0))]
            for s in numeric_stats
        ]
        pdf.add_table(headers, rows[:15], [32, 24, 24, 24, 24, 24, 22])

    cat_stats = [s for s in analysis["column_stats"] if "top_values" in s]
    if cat_stats:
        pdf.check_space(40)
        pdf.subsection_title("Categorical Columns")
        headers = ["Column", "Unique", "Null%", "Top Value", "Freq"]
        rows = []
        for s in cat_stats[:10]:
            top = list(s["top_values"].items())
            top_val = top[0][0] if top else "-"
            top_freq = str(top[0][1]) if top else "-"
            rows.append([s["name"][:18], str(s["unique_count"]), f"{s['null_pct']:.1f}%", top_val[:18], top_freq])
        pdf.add_table(headers, rows, [40, 20, 20, 70, 22])

    # --- Section 3: Visualizations ---
    df_clean = analysis["cleaned_df"]

    figs = []
    fig = generate_missing_data_chart(analysis.get("raw_df", df_clean))
    if fig:
        figs.append(("Missing Values (Original Data)", fig))
    fig = generate_distribution_plots(df_clean)
    if fig:
        figs.append(("Numeric Distributions", fig))
    fig = generate_correlation_heatmap(df_clean)
    if fig:
        figs.append(("Correlation Heatmap", fig))
    fig = generate_categorical_chart(df_clean)
    if fig:
        figs.append(("Categorical Distributions", fig))

    if figs:
        pdf.check_space(50)
        pdf.section_title("3. Visualizations")
        for title, figure in figs:
            pdf.check_space(50)
            pdf.subsection_title(title)
            pdf.add_image_from_figure(figure, width=155)

    # --- Section 4: Relationships ---
    pdf.check_space(30)
    pdf.section_title("4. Column Relationships" if figs else "3. Column Relationships")

    rels = analysis["relationships"]
    has_rels = False

    if rels.get("strong_correlations"):
        has_rels = True
        pdf.subsection_title("Numeric Correlations")
        headers = ["Column 1", "Column 2", "Correlation", "Strength"]
        rows = [[r["column_1"][:18], r["column_2"][:18], f"{r['correlation']:.3f}", r["strength"]]
                for r in rels["strong_correlations"]]
        pdf.add_table(headers, rows, [48, 48, 38, 38])

    if rels.get("categorical_associations"):
        has_rels = True
        pdf.check_space(30)
        pdf.subsection_title("Categorical Associations (Cramer's V)")
        headers = ["Column 1", "Column 2", "Cramer's V", "Strength"]
        rows = [[r["column_1"][:18], r["column_2"][:18], f"{r['cramers_v']:.3f}", r["strength"]]
                for r in rels["categorical_associations"]]
        pdf.add_table(headers, rows, [48, 48, 38, 38])

    if rels.get("numeric_categorical"):
        has_rels = True
        pdf.check_space(30)
        pdf.subsection_title("Category -> Numeric Impact")
        headers = ["Category", "Numeric", "Effect (eta2)", "Significance"]
        rows = [[r["categorical"][:18], r["numeric"][:18], f"{r['eta_squared']:.3f}", r["effect"]]
                for r in rels["numeric_categorical"]]
        pdf.add_table(headers, rows, [48, 48, 38, 38])

    if not has_rels:
        pdf.body_text("No significant relationships detected between columns.")

    # --- Key Insights ---
    pdf.check_space(30)
    next_section = 5 if figs else 4
    pdf.section_title(f"{next_section}. Key Insights")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    for insight in analysis["insights"]:
        text = sanitize_text(f"  {insight}")
        pdf.multi_cell(0, 4.5, text)
        pdf.ln(1.5)

    return pdf.output()
