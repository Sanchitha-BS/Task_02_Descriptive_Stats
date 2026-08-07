import csv
import ast
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime

CSV_PATH = "2024_fb_ads_president_scored_anon.csv"
MISSING_TOKENS = {"", "n/a", "na", "null", "none", "nan"}

LIST_COLUMNS = {"publisher_platforms", "illuminating_mentions"}
DATE_COLUMNS = {"ad_creation_time"}
NESTED_DICT_COLUMNS = {"delivery_by_region", "demographic_distribution"}
BINARY_FLAG_THRESHOLD = 2
FULL_FILE_GROUP_CAP = 200

maxInt = sys.maxsize
while True:
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt / 10)


def is_missing(v):
    return v is None or v.strip().lower() in MISSING_TOKENS


def parse_number(v):
    cleaned = str(v).strip().replace("$", "").replace(",", "")
    try:
        n = float(cleaned)
        return n if math.isfinite(n) else None
    except ValueError:
        return None


def parse_container(v, kind):
    try:
        parsed = ast.literal_eval(v.strip())
    except (ValueError, SyntaxError):
        return None
    return parsed if isinstance(parsed, kind) else None


def parse_date(v):
    try:
        return datetime.strptime(v.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def numeric_stats(values):
    nums = [n for n in (parse_number(v) for v in values) if n is not None]
    if not nums:
        return {"count": 0}
    return {
        "count": len(nums), "mean": sum(nums) / len(nums), "min": min(nums),
        "max": max(nums), "median": statistics.median(nums),
        "std": statistics.stdev(nums) if len(nums) >= 2 else None,
    }


def categorical_stats(values, top_n=5):
    if not values:
        return {"count": 0}
    counts = Counter(values)
    top = counts.most_common(top_n)
    return {"count": len(values), "unique": len(counts),
            "mode": top[0][0], "mode_freq": top[0][1], "top": top}


def date_stats(values):
    dates = [d for d in (parse_date(v) for v in values) if d]
    if not dates:
        return {"count": 0}
    return {"count": len(dates), "min": min(dates).date(), "max": max(dates).date(),
            "unique": len(set(dates))}


def nested_dict_row_and_key_stats(values):
    # parse each value once, get row totals and per-key totals together
    row_spend, row_impr = [], []
    spend_by_key, impr_by_key, rows_by_key = Counter(), Counter(), Counter()
    for v in values:
        parsed = parse_container(v, dict)
        if not parsed:
            continue
        total_spend, total_impr, found = 0.0, 0.0, False
        for key, sub in parsed.items():
            if isinstance(sub, dict):
                found = True
                s = parse_number(sub.get("spend", 0)) or 0
                i = parse_number(sub.get("impressions", 0)) or 0
                total_spend += s
                total_impr += i
                spend_by_key[key] += s
                impr_by_key[key] += i
                rows_by_key[key] += 1
        if found:
            row_spend.append(str(total_spend))
            row_impr.append(str(total_impr))
    return row_spend, row_impr, spend_by_key, impr_by_key, rows_by_key


def format_numeric_lines(num, is_binary):
    std_str = f"{num['std']:.4f}" if num["std"] is not None else "N/A (n<2)"
    lines = [f"count={num['count']} mean={num['mean']:.4f} min={num['min']} "
             f"max={num['max']} median={num['median']} std={std_str}"]
    if is_binary:
        flagged = int(round(num["mean"] * num["count"]))
        lines.append(f"flag rate: {flagged}/{num['count']} ({num['mean']*100:.2f}%) == 1")
    return lines


def column_stats_block(col, raw):
    missing = sum(1 for v in raw if is_missing(v))
    clean = [v for v in raw if not is_missing(v)]

    if col in NESTED_DICT_COLUMNS:
        spend_vals, impr_vals, spend_by_key, impr_by_key, rows_by_key = nested_dict_row_and_key_stats(clean)
        spend_stats, impr_stats = numeric_stats(spend_vals), numeric_stats(impr_vals)
        lines = []
        if spend_stats["count"]:
            lines.append(f"row-total spend: n={spend_stats['count']} mean={spend_stats['mean']:.2f} "
                          f"min={spend_stats['min']} max={spend_stats['max']} "
                          f"median={spend_stats['median']} std={(spend_stats['std'] or 0):.2f}")
        if impr_stats["count"]:
            lines.append(f"row-total impressions: n={impr_stats['count']} mean={impr_stats['mean']:.2f} "
                          f"min={impr_stats['min']} max={impr_stats['max']} "
                          f"median={impr_stats['median']} std={(impr_stats['std'] or 0):.2f}")
        lines.append("top 5 sub-keys by total spend:")
        for key, total in spend_by_key.most_common(5):
            lines.append(f"  {key}: spend={total:.2f} impressions={impr_by_key[key]:.2f} rows={rows_by_key[key]}")
        return "nested-dict (row totals + per-key breakdown)", missing, lines

    if col in LIST_COLUMNS:
        exploded = []
        for v in clean:
            items = parse_container(v, list)
            exploded.extend(items or [])
        s = categorical_stats(exploded)
        lines = ([f"count={s['count']} unique items={s['unique']}",
                  f"mode={s['mode']!r} (frequency={s['mode_freq']})", "top 5:"] +
                 [f"  {val}: {freq}" for val, freq in s["top"]]) if s["count"] else ["no data"]
        return "list-string (exploded per item)", missing, lines

    if col in DATE_COLUMNS:
        s = date_stats(clean)
        lines = [f"count={s['count']} min={s['min']} max={s['max']} unique={s['unique']}"] if s["count"] else ["no data"]
        return "date", missing, lines

    num = numeric_stats(clean)
    is_numeric = num["count"] > len(clean) / 2 if clean else False
    if is_numeric:
        distinct_vals = {v.strip() for v in clean}
        is_binary = len(distinct_vals) <= BINARY_FLAG_THRESHOLD
        lines = format_numeric_lines(num, is_binary)
        return "numeric" + (" (binary flag)" if is_binary else ""), missing, lines

    s = categorical_stats(clean)
    if s["count"]:
        lines = [f"count={s['count']} unique={s['unique']}",
                 f"mode={s['mode']!r} (frequency={s['mode_freq']})", "top 5:"] + \
                [f"  {val}: {freq}" for val, freq in s["top"]]
    else:
        lines = ["no data (all missing)"]
    return "categorical", missing, lines


def analyze_columns(rows, fieldnames, label="DATASET-LEVEL", out=None):
    out = out if out is not None else sys.stdout
    print(f"\n{label} COLUMN STATS", file=out)

    for col in fieldnames:
        raw = [row.get(col, "") for row in rows]
        col_type, missing, lines = column_stats_block(col, raw)
        print(f"\n{col}  (missing={missing}, type={col_type})", file=out)
        for line in lines:
            print(f"  {line}", file=out)


def grouped_analysis(rows, fieldnames, group_by_cols, full_report_path,
                      top_n_full_stats=5, degenerate_examples=2):
    label = "+".join(group_by_cols)
    print(f"\nGROUPED ANALYSIS BY {label}")

    groups = defaultdict(list)
    for row in rows:
        key = tuple(row.get(c, "") for c in group_by_cols)
        groups[key].append(row)

    print(f"total distinct groups: {len(groups)}")
    group_sizes = Counter({key: len(grp_rows) for key, grp_rows in groups.items()})
    all_singleton = all(size == 1 for size in group_sizes.values())

    print(f"\ntop 5 groups by number of ads:")
    for key, size in group_sizes.most_common(5):
        key_label = ", ".join(f"{c}={v}" for c, v in zip(group_by_cols, key))
        spend_vals = [r.get("estimated_spend", "") for r in groups[key]]
        spend_stats = numeric_stats(spend_vals)
        spend_desc = (f"total_spend~={spend_stats['mean']*spend_stats['count']:.2f} "
                      f"avg_spend={spend_stats['mean']:.2f}") if spend_stats["count"] else "no spend data"
        print(f"  [{key_label}]  n_ads={size}  {spend_desc}")

    if all_singleton:
        print(f"\nnote: all {len(groups)} groups have exactly 1 row, "
              f"{label} is already the dataset's atomic grain")
        for key in list(groups)[:degenerate_examples]:
            key_label = ", ".join(f"{c}={v}" for c, v in zip(group_by_cols, key))
            analyze_columns(groups[key], fieldnames, label=f"GROUP [{key_label}] (n=1)")
        return

    covered_rows = sum(size for _, size in group_sizes.most_common(FULL_FILE_GROUP_CAP))
    with open(full_report_path, "w", encoding="utf-8") as out:
        print(f"GROUPED ANALYSIS BY {label} -- full per-column stats for the "
              f"largest {min(FULL_FILE_GROUP_CAP, len(groups))} of {len(groups)} groups "
              f"(covering {covered_rows}/{len(rows)} rows, "
              f"{covered_rows/len(rows)*100:.1f}% of the dataset)", file=out)
        for key, size in group_sizes.most_common(FULL_FILE_GROUP_CAP):
            key_label = ", ".join(f"{c}={v}" for c, v in zip(group_by_cols, key))
            analyze_columns(groups[key], fieldnames, label=f"GROUP [{key_label}] (n={size})", out=out)

    print(f"\nfull per-column stats for the top {top_n_full_stats} groups by ad volume:")
    for key, size in group_sizes.most_common(top_n_full_stats):
        key_label = ", ".join(f"{c}={v}" for c, v in zip(group_by_cols, key))
        analyze_columns(groups[key], fieldnames, label=f"GROUP [{key_label}] (n={size})")

    print(f"\n(full per-column stats for the largest {min(FULL_FILE_GROUP_CAP, len(groups))} "
          f"of {len(groups)} groups -- {covered_rows/len(rows)*100:.1f}% of all rows -- "
          f"written to {full_report_path})")


def main():
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    print(f"Total rows: {len(rows)} | Total columns: {len(fieldnames)}")

    analyze_columns(rows, fieldnames)
    grouped_analysis(rows, fieldnames, ["page_id"], "grouped_stats_page_id.txt")
    grouped_analysis(rows, fieldnames, ["page_id", "ad_id"], "grouped_stats_page_id_ad_id.txt")


if __name__ == "__main__":
    main()
