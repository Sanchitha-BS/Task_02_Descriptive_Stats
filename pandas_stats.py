import ast
import pandas as pd
from pure_python_stats import numeric_stats, parse_container

CSV_PATH = "2024_fb_ads_president_scored_anon.csv"

LIST_COLUMNS = ["publisher_platforms", "illuminating_mentions"]
DATE_COLUMNS = ["ad_creation_time"]
NESTED_DICT_COLUMNS = ["delivery_by_region", "demographic_distribution"]
PLAIN_CATEGORICAL_COLUMNS = ["bylines", "currency", "illuminating_scored_message"]
BINARY_FLAG_THRESHOLD = 2


def load_data():
    return pd.read_csv(CSV_PATH)


def numeric_columns(df):
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def show_structure(df):
    print("BASIC STRUCTURE")
    print(f"shape: {df.shape}  (rows, columns)\n")
    print("dtypes:")
    print(df.dtypes)


def show_missing(df):
    print("\nMISSING VALUES PER COLUMN")
    missing = df.isna().sum()
    pct = (missing / len(df) * 100).round(2)
    print(pd.DataFrame({"missing": missing, "pct": pct}))


def show_describe(df):
    num_cols = numeric_columns(df)
    print("\nDataFrame.describe() -- NUMERIC COLUMNS")
    print(df[num_cols].describe())

    print("\nDataFrame.describe() -- NON-NUMERIC (STRING) COLUMNS")
    string_dtype = "str" if "str" in df.dtypes.astype(str).values else "object"
    print(df.describe(include=[string_dtype]))


def show_binary_flag_rates(df):
    print(f"\nBINARY FLAG COLUMNS (<= {BINARY_FLAG_THRESHOLD} distinct values) -- flag rate")
    for col in numeric_columns(df):
        if df[col].nunique(dropna=True) <= BINARY_FLAG_THRESHOLD:
            count = df[col].count()
            flagged = int(df[col].sum())
            rate = df[col].mean()
            print(f"{col}: {flagged}/{count} ({rate*100:.2f}%) == 1")


def show_categorical_value_counts(df):
    print("\nCATEGORICAL COLUMNS -- value_counts() / nunique()")
    for col in PLAIN_CATEGORICAL_COLUMNS + ["page_id", "ad_id"]:
        print(f"\n{col}  (nunique={df[col].nunique()})")
        print(df[col].value_counts().head(5))


def explode_list_columns(df):
    print("\nLIST COLUMNS -- exploded item value_counts()")
    exploded_counts = {}
    for col in LIST_COLUMNS:
        parsed = df[col].apply(lambda v: ast.literal_eval(v) if pd.notna(v) else [])
        exploded = parsed.explode()
        counts = exploded.value_counts()
        exploded_counts[col] = counts
        print(f"\n{col}  (unique items={counts.shape[0]})")
        print(counts.head(5))
    return exploded_counts


def parse_date_columns(df):
    for col in DATE_COLUMNS:
        parsed = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
        failure_rate = parsed.isna().mean()
        if failure_rate > 0.5:
            parsed = pd.to_datetime(df[col], errors="coerce")
            failure_rate = parsed.isna().mean()
        df[col] = parsed
        if failure_rate > 0:
            print(f"  note: {col} -- {parsed.isna().sum()} value(s) could not be parsed "
                  f"as dates ({failure_rate*100:.1f}%)")
    return df


def show_date_stats(df):
    print("\nDATE COLUMNS")
    print(df[DATE_COLUMNS].describe())


def process_nested_dict_columns(df):
    # parse each dict once, get row totals + per-key totals together
    # (keeping parsed dict objects on the df blows up memory on the full file)
    breakdowns = {}
    for col in NESTED_DICT_COLUMNS:
        row_spend, row_impr = [], []
        spend_by_key, impr_by_key, rows_by_key = {}, {}, {}
        for v in df[col]:
            if pd.isna(v):
                row_spend.append(None)
                row_impr.append(None)
                continue
            parsed = parse_container(v, dict)
            if not parsed:
                row_spend.append(None)
                row_impr.append(None)
                continue
            total_spend, total_impr, found = 0.0, 0.0, False
            for key, sub in parsed.items():
                if isinstance(sub, dict):
                    found = True
                    s = sub.get("spend") or 0
                    i = sub.get("impressions") or 0
                    total_spend += s
                    total_impr += i
                    spend_by_key[key] = spend_by_key.get(key, 0) + s
                    impr_by_key[key] = impr_by_key.get(key, 0) + i
                    rows_by_key[key] = rows_by_key.get(key, 0) + 1
            row_spend.append(total_spend if found else None)
            row_impr.append(total_impr if found else None)
        df[f"{col}_row_spend"] = row_spend
        df[f"{col}_row_impr"] = row_impr
        breakdowns[col] = (spend_by_key, impr_by_key, rows_by_key)
    return df, breakdowns


def show_nested_dict_stats(df, breakdowns):
    print("\nNESTED-DICT COLUMNS (row totals + per-key breakdown)")
    for col in NESTED_DICT_COLUMNS:
        print(f"\n{col} -- row-level totals:")
        print(df[[f"{col}_row_spend", f"{col}_row_impr"]].describe())

        spend_by_key, impr_by_key, rows_by_key = breakdowns[col]
        top5 = sorted(spend_by_key.items(), key=lambda kv: kv[1], reverse=True)[:5]
        print(f"\n{col} -- top 5 sub-keys by total spend:")
        for key, total in top5:
            print(f"  {key}: spend={total:.2f} impressions={impr_by_key[key]:.2f} rows={rows_by_key[key]}")


def grouped_analysis_page_id(df):
    print("\nGROUPED ANALYSIS BY page_id (Pandas)")

    group_sizes = df.groupby("page_id").size().sort_values(ascending=False)
    print(f"total distinct groups: {group_sizes.shape[0]}")
    print("\ntop 5 groups by number of ads:")
    print(group_sizes.head(5))

    num_cols = numeric_columns(df)
    numeric_group_stats = df.groupby("page_id")[num_cols].agg(["count", "mean", "min", "max", "std", "median"])
    numeric_group_stats.to_csv("grouped_pandas_page_id_numeric.csv")
    print(f"\nfull numeric stats for all {numeric_group_stats.shape[0]} page_id groups "
          f"written to grouped_pandas_page_id_numeric.csv")

    cat_cols = PLAIN_CATEGORICAL_COLUMNS
    cat_nunique = df.groupby("page_id")[cat_cols].nunique()
    cat_count = df.groupby("page_id")[cat_cols].count()
    cat_mode = df.groupby("page_id")[cat_cols].agg(lambda s: s.mode().iat[0] if not s.mode().empty else None)
    cat_group_stats = pd.concat({"nunique": cat_nunique, "count": cat_count, "mode": cat_mode}, axis=1)
    cat_group_stats.to_csv("grouped_pandas_page_id_categorical.csv")
    print(f"full categorical stats for all {cat_group_stats.shape[0]} page_id groups "
          f"written to grouped_pandas_page_id_categorical.csv")

    print(f"\nfull per-column stats (describe()) for the top 5 groups by ad volume:")
    for pid in group_sizes.head(5).index:
        sub = df[df["page_id"] == pid]
        print(f"\n--- GROUP page_id={pid} (n={len(sub)}) ---")
        print(sub[num_cols].describe())
        print(sub[cat_cols].describe())


def grouped_analysis_page_id_ad_id(df):
    print("\nGROUPED ANALYSIS BY page_id+ad_id (Pandas)")

    sizes = df.groupby(["page_id", "ad_id"]).size()
    print(f"total distinct groups: {sizes.shape[0]}")
    all_singleton = (sizes == 1).all()
    print(f"all groups have exactly 1 row: {all_singleton}")

    if all_singleton:
        print(f"\nnote: all {sizes.shape[0]} groups have exactly 1 row, "
              f"ad_id is already the dataset's atomic grain")
        example = df.groupby(["page_id", "ad_id"]).size().head(2)
        print("\nexample groups (confirming n=1):")
        print(example)
    else:
        num_cols = numeric_columns(df)
        combo_stats = df.groupby(["page_id", "ad_id"])[num_cols].agg(["count", "mean", "min", "max", "std", "median"])
        combo_stats.to_csv("grouped_pandas_page_id_ad_id_numeric.csv")
        print("full numeric stats per page_id+ad_id group written to "
              "grouped_pandas_page_id_ad_id_numeric.csv")


def verify_against_pure_python(df):
    print("\nVERIFICATION: PANDAS vs PURE PYTHON")

    check_cols = ["incivility_illuminating", "scam_illuminating", "estimated_spend",
                  "estimated_impressions", "estimated_audience_size",
                  "delivery_by_region_row_spend", "demographic_distribution_row_spend"]

    for col in check_cols:
        series = df[col].dropna()
        pandas_mean = series.mean()
        pandas_std = series.std()

        pure_values = [str(v) for v in series]
        pure = numeric_stats(pure_values)

        match = (
            abs(pandas_mean - pure["mean"]) < 1e-6
            and abs(pandas_std - (pure["std"] or 0)) < 1e-6
        )
        print(f"\n{col}")
        print(f"  pandas : mean={pandas_mean:.6f}  std={pandas_std:.6f}")
        print(f"  pure py: mean={pure['mean']:.6f}  std={(pure['std'] or 0):.6f}")
        print(f"  match  : {match}")


def main():
    df = load_data()
    show_structure(df)
    show_missing(df)
    show_describe(df)
    show_binary_flag_rates(df)
    show_categorical_value_counts(df)
    explode_list_columns(df)
    df = parse_date_columns(df)
    show_date_stats(df)
    df, breakdowns = process_nested_dict_columns(df)
    show_nested_dict_stats(df, breakdowns)

    grouped_analysis_page_id(df)
    grouped_analysis_page_id_ad_id(df)

    verify_against_pure_python(df)


if __name__ == "__main__":
    main()