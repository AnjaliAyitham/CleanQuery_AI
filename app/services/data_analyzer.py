import numpy as np
import pandas as pd
from scipy import stats


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Clean the dataframe and return cleaned df + log of changes."""
    changes = []
    df_clean = df.copy()

    # Remove exact duplicate rows
    dup_count = df_clean.duplicated().sum()
    if dup_count > 0:
        df_clean = df_clean.drop_duplicates().reset_index(drop=True)
        changes.append({"action": "Removed duplicates", "detail": f"{dup_count} duplicate rows removed"})

    # Handle missing values
    for col in df_clean.columns:
        null_count = df_clean[col].isna().sum()
        if null_count == 0:
            continue

        null_pct = null_count / len(df_clean)
        if null_pct > 0.6:
            df_clean = df_clean.drop(columns=[col])
            changes.append({"action": "Dropped column", "detail": f"'{col}' had {null_pct:.0%} missing — removed"})
        elif df_clean[col].dtype in (np.float64, np.int64, float, int):
            median_val = df_clean[col].median()
            df_clean[col] = df_clean[col].fillna(median_val)
            changes.append({"action": "Filled missing", "detail": f"'{col}': {null_count} nulls filled with median ({median_val:.2f})"})
        else:
            mode_val = df_clean[col].mode()
            if len(mode_val) > 0:
                df_clean[col] = df_clean[col].fillna(mode_val.iloc[0])
                changes.append({"action": "Filled missing", "detail": f"'{col}': {null_count} nulls filled with mode ('{mode_val.iloc[0]}')"})

    # Standardize text columns
    for col in df_clean.select_dtypes(include=["object"]).columns:
        original = df_clean[col].copy()
        df_clean[col] = df_clean[col].str.strip()
        stripped = (original != df_clean[col]).sum()
        if stripped > 0:
            changes.append({"action": "Trimmed whitespace", "detail": f"'{col}': {stripped} values trimmed"})

    return df_clean, changes


def compute_kpis(df: pd.DataFrame) -> dict:
    """Compute key performance indicators for the dataset."""
    kpis = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
        "categorical_columns": len(df.select_dtypes(include=["object", "category"]).columns),
        "missing_cells_total": int(df.isna().sum().sum()),
        "missing_pct": round(df.isna().sum().sum() / (len(df) * len(df.columns)) * 100, 2),
        "duplicate_rows": int(df.duplicated().sum()),
    }
    return kpis


def analyze_columns(df: pd.DataFrame) -> list[dict]:
    """Generate per-column statistics."""
    column_stats = []
    for col in df.columns:
        stat = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].notna().sum()),
            "null_count": int(df[col].isna().sum()),
            "null_pct": round(df[col].isna().sum() / len(df) * 100, 1),
            "unique_count": int(df[col].nunique()),
            "unique_pct": round(df[col].nunique() / len(df) * 100, 1),
        }

        if df[col].dtype in (np.float64, np.int64, float, int):
            stat["mean"] = round(float(df[col].mean()), 2)
            stat["median"] = round(float(df[col].median()), 2)
            stat["std"] = round(float(df[col].std()), 2)
            stat["min"] = float(df[col].min())
            stat["max"] = float(df[col].max())
            stat["skewness"] = round(float(df[col].skew()), 2)
            stat["kurtosis"] = round(float(df[col].kurtosis()), 2)

            # Outlier count using IQR
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            outliers = ((df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)).sum()
            stat["outlier_count"] = int(outliers)
        else:
            top = df[col].value_counts().head(5)
            stat["top_values"] = {str(k): int(v) for k, v in top.items()}

        column_stats.append(stat)
    return column_stats


def find_relationships(df: pd.DataFrame) -> dict:
    """Find correlations and relationships between columns."""
    relationships = {
        "numeric_correlations": [],
        "strong_correlations": [],
        "categorical_associations": [],
    }

    # Numeric correlations
    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) >= 2:
        corr_matrix = numeric_df.corr()
        relationships["correlation_matrix"] = corr_matrix.round(3).to_dict()

        # Find strong correlations (|r| > 0.5, excluding self)
        for i, col1 in enumerate(corr_matrix.columns):
            for j, col2 in enumerate(corr_matrix.columns):
                if i >= j:
                    continue
                r = corr_matrix.iloc[i, j]
                if abs(r) > 0.5 and not np.isnan(r):
                    relationships["strong_correlations"].append({
                        "column_1": col1,
                        "column_2": col2,
                        "correlation": round(float(r), 3),
                        "strength": "strong" if abs(r) > 0.7 else "moderate",
                        "direction": "positive" if r > 0 else "negative",
                    })

    # Categorical associations (Cramér's V)
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    for i, col1 in enumerate(cat_cols):
        for j, col2 in enumerate(cat_cols):
            if i >= j:
                continue
            if df[col1].nunique() > 20 or df[col2].nunique() > 20:
                continue
            try:
                contingency = pd.crosstab(df[col1], df[col2])
                chi2, p_value, _, _ = stats.chi2_contingency(contingency)
                n = contingency.sum().sum()
                min_dim = min(contingency.shape) - 1
                if min_dim > 0:
                    cramers_v = round(float(np.sqrt(chi2 / (n * min_dim))), 3)
                    if cramers_v > 0.3:
                        relationships["categorical_associations"].append({
                            "column_1": col1,
                            "column_2": col2,
                            "cramers_v": cramers_v,
                            "p_value": round(float(p_value), 4),
                            "strength": "strong" if cramers_v > 0.5 else "moderate",
                        })
            except Exception:
                continue

    # Numeric-categorical relationships (ANOVA / eta-squared)
    relationships["numeric_categorical"] = []
    for cat_col in cat_cols:
        if df[cat_col].nunique() > 15 or df[cat_col].nunique() < 2:
            continue
        for num_col in numeric_df.columns:
            groups = [g.dropna().values for _, g in df.groupby(cat_col)[num_col] if len(g.dropna()) > 1]
            if len(groups) < 2:
                continue
            try:
                f_stat, p_value = stats.f_oneway(*groups)
                if p_value < 0.05 and not np.isnan(f_stat):
                    # Calculate eta-squared
                    grand_mean = df[num_col].mean()
                    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
                    ss_total = ((df[num_col] - grand_mean) ** 2).sum()
                    eta_sq = round(float(ss_between / ss_total), 3) if ss_total > 0 else 0
                    if eta_sq > 0.1:
                        relationships["numeric_categorical"].append({
                            "categorical": cat_col,
                            "numeric": num_col,
                            "f_statistic": round(float(f_stat), 2),
                            "p_value": round(float(p_value), 4),
                            "eta_squared": eta_sq,
                            "effect": "large" if eta_sq > 0.25 else "medium",
                        })
            except Exception:
                continue

    return relationships


def generate_insights(kpis: dict, column_stats: list[dict], relationships: dict) -> list[str]:
    """Generate human-readable insights from the analysis."""
    insights = []

    # Data quality insights
    if kpis["missing_pct"] > 10:
        insights.append(f"⚠️ High missing data rate ({kpis['missing_pct']}%) — check data collection process.")
    elif kpis["missing_pct"] == 0:
        insights.append("✓ Dataset is complete — no missing values detected.")

    if kpis["duplicate_rows"] > 0:
        insights.append(f"⚠️ {kpis['duplicate_rows']} duplicate rows found and removed during cleaning.")

    # Column insights
    for stat in column_stats:
        if stat.get("skewness") and abs(stat["skewness"]) > 2:
            direction = "right" if stat["skewness"] > 0 else "left"
            insights.append(f"📊 '{stat['name']}' is heavily {direction}-skewed (skew={stat['skewness']}) — consider log transform.")
        if stat.get("outlier_count") and stat["outlier_count"] > len(column_stats) * 0.1:
            insights.append(f"🔍 '{stat['name']}' has {stat['outlier_count']} outliers — investigate extreme values.")

    # Relationship insights
    for corr in relationships.get("strong_correlations", []):
        insights.append(
            f"🔗 Strong {corr['direction']} correlation between '{corr['column_1']}' and '{corr['column_2']}' (r={corr['correlation']})."
        )

    for assoc in relationships.get("categorical_associations", []):
        insights.append(
            f"🔗 Significant association between '{assoc['column_1']}' and '{assoc['column_2']}' (Cramér's V={assoc['cramers_v']})."
        )

    for nc in relationships.get("numeric_categorical", []):
        insights.append(
            f"📈 '{nc['categorical']}' significantly affects '{nc['numeric']}' (η²={nc['eta_squared']}, {nc['effect']} effect)."
        )

    if not insights:
        insights.append("✓ Data looks clean and well-structured. No major issues detected.")

    return insights


def run_full_analysis(df: pd.DataFrame) -> dict:
    """Run the complete analysis pipeline."""
    # Step 1: Compute KPIs on raw data
    raw_kpis = compute_kpis(df)

    # Step 2: Clean
    df_clean, cleaning_log = clean_dataframe(df)

    # Step 3: Compute KPIs on cleaned data
    clean_kpis = compute_kpis(df_clean)

    # Step 4: Column analysis
    column_stats = analyze_columns(df_clean)

    # Step 5: Relationships
    relationships = find_relationships(df_clean)

    # Step 6: Insights
    insights = generate_insights(clean_kpis, column_stats, relationships)

    return {
        "raw_kpis": raw_kpis,
        "clean_kpis": clean_kpis,
        "cleaning_log": cleaning_log,
        "column_stats": column_stats,
        "relationships": relationships,
        "insights": insights,
        "cleaned_df": df_clean,
    }
