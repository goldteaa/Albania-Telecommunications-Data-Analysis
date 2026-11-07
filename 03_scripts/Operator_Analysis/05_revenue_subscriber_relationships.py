
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "02_data" / "Operator_Data"
    / "Albania_Telecom_Operator_Data_2020_2024.xlsx"
)

TABLES = (
    ROOT / "04_outputs" / "Reproduced_Results"
    / "Operator_Analysis" / "Tables"
)

FIGURES = (
    ROOT / "04_outputs" / "Reproduced_Results"
    / "Operator_Analysis" / "Figures"
)

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

mobile_revenue = pd.read_excel(
    INPUT, sheet_name="Mobile_Revenues"
)
mobile_subs = pd.read_excel(
    INPUT, sheet_name="Mobile_Subscribers"
)
fixed_revenue = pd.read_excel(
    INPUT, sheet_name="Fixed_Revenues"
)
fixed_subs = pd.read_excel(
    INPUT, sheet_name="Fixed_Broadband"
)
fixed_sector = pd.read_excel(
    INPUT, sheet_name="Fixed_Sector_Totals"
)

# ---------------------------------------------
# 1. Sector-level annual series
# ---------------------------------------------

mobile_rev_total = (
    mobile_revenue.groupby("Year")["Revenue_Million_ALL"]
    .sum()
)

mobile_sub_total = (
    mobile_subs.groupby("Year")[
        "Active_Broadband_Subscribers"
    ].sum()
)

fixed_rev_total = fixed_sector.set_index(
    "Year"
)["Total_Revenue_Million_ALL"]

fixed_sub_total = (
    fixed_subs.groupby("Year")[
        "Fixed_Broadband_Subscribers"
    ].sum()
)

sector = pd.DataFrame({
    "Mobile_Revenue_Million_ALL": mobile_rev_total,
    "Mobile_Active_Broadband_Subs": mobile_sub_total,
    "Fixed_Revenue_Million_ALL": fixed_rev_total,
    "Fixed_Broadband_Subs": fixed_sub_total,
}).sort_index()

sector.index.name = "Year"

if sector.isna().any().any():
    raise ValueError(
        "Sector series contain missing annual values."
    )

# ---------------------------------------------
# 2. Annual growth and indexed trends
# ---------------------------------------------

sector_growth = sector.pct_change() * 100
sector_growth.columns = [
    f"{col}_YoY_Pct" for col in sector_growth.columns
]

sector_index = sector.div(sector.iloc[0]) * 100
sector_index.columns = [
    f"{col}_Index_2020_100"
    for col in sector_index.columns
]

sector_results = pd.concat(
    [sector, sector_growth, sector_index],
    axis=1
).reset_index()

# ---------------------------------------------
# 3. Operator-year matched records
# ---------------------------------------------

def join_operator_data(
    revenue_df, subscriber_df,
    subscriber_column, segment
):
    joined = revenue_df[
        ["Year", "Operator", "Revenue_Million_ALL"]
    ].merge(
        subscriber_df[
            ["Year", "Operator", subscriber_column]
        ],
        on=["Year", "Operator"],
        how="outer",
        validate="one_to_one",
        indicator=True
    )

    joined = joined.rename(columns={
        subscriber_column: "Subscribers",
        "_merge": "Match_Status"
    })

    joined["Segment"] = segment

    return joined

mobile_join = join_operator_data(
    mobile_revenue,
    mobile_subs,
    "Active_Broadband_Subscribers",
    "Mobile"
)

fixed_join = join_operator_data(
    fixed_revenue,
    fixed_subs,
    "Fixed_Broadband_Subscribers",
    "Fixed"
)

all_matches = pd.concat(
    [mobile_join, fixed_join],
    ignore_index=True
)

# ---------------------------------------------
# 4. Explicit comparable operator periods
# ---------------------------------------------

PERIODS = [
    ("Mobile", "Vodafone Albania", 2020, 2024),
    ("Mobile", "ONE Albania", 2020, 2022),
    ("Mobile", "ONE Albania", 2023, 2024),
    ("Mobile", "Albtelecom", 2020, 2022),

    ("Fixed", "ASC", 2020, 2024),
    ("Fixed", "Abissnet", 2020, 2024),
    ("Fixed", "Digicom", 2020, 2024),
    ("Fixed", "Nisatel", 2020, 2024),
    ("Fixed", "Vodafone Albania", 2021, 2024),
    ("Fixed", "ONE Albania", 2023, 2024),
]

operator_rows = []
coverage_rows = []

for segment, operator, start_year, end_year in PERIODS:

    subset = all_matches.loc[
        (all_matches["Segment"] == segment)
        & (all_matches["Operator"] == operator)
        & (all_matches["Year"].between(
            start_year, end_year
        ))
        & (all_matches["Match_Status"] == "both")
    ].copy().sort_values("Year")

    expected_years = list(
        range(start_year, end_year + 1)
    )

    actual_years = subset["Year"].tolist()

    period_id = (
        f"{segment}_{operator}_{start_year}_{end_year}"
    )

    complete = actual_years == expected_years

    coverage_rows.append({
        "Period_ID": period_id,
        "Segment": segment,
        "Operator": operator,
        "Start_Year": start_year,
        "End_Year": end_year,
        "Expected_Observations": len(expected_years),
        "Matched_Observations": len(subset),
        "Complete_Period": complete,
    })

    if not complete:
        print(
            f"WARNING: Incomplete period: {period_id}"
        )
        continue

    subset["Period_ID"] = period_id

    subset["Revenue_YoY_Pct"] = (
        subset["Revenue_Million_ALL"].pct_change() * 100
    )

    subset["Subscribers_YoY_Pct"] = (
        subset["Subscribers"].pct_change() * 100
    )

    subset["Revenue_Index_100"] = (
        subset["Revenue_Million_ALL"]
        / subset["Revenue_Million_ALL"].iloc[0] * 100
    )

    subset["Subscribers_Index_100"] = (
        subset["Subscribers"]
        / subset["Subscribers"].iloc[0] * 100
    )

    operator_rows.append(subset)

if operator_rows:
    operator_panel = pd.concat(
        operator_rows, ignore_index=True
    )
else:
    raise ValueError(
        "No complete operator periods were found."
    )

coverage = pd.DataFrame(coverage_rows)

# ---------------------------------------------
# 5. Pearson correlations
# ---------------------------------------------

def safe_correlation(x, y, minimum_n=4):
    pair = pd.DataFrame({
        "x": x, "y": y
    }).dropna()

    if len(pair) < minimum_n:
        return np.nan

    if (
        pair["x"].nunique() < 2
        or pair["y"].nunique() < 2
    ):
        return np.nan

    return pair["x"].corr(pair["y"])

correlation_rows = []

# Sector correlations: descriptive only
for segment, revenue_col, subscriber_col in [
    (
        "Mobile",
        "Mobile_Revenue_Million_ALL",
        "Mobile_Active_Broadband_Subs"
    ),
    (
        "Fixed",
        "Fixed_Revenue_Million_ALL",
        "Fixed_Broadband_Subs"
    ),
]:
    correlation_rows.append({
        "Level": "Sector",
        "Segment": segment,
        "Operator": "All reported operators",
        "Period": "2020-2024",
        "N": len(sector),
        "Pearson_r": safe_correlation(
            sector[revenue_col],
            sector[subscriber_col]
        ),
        "Note": (
            "Exploratory levels correlation; "
            "different revenue/subscriber coverage; "
            "no causal inference"
        )
    })

# Operator correlations
for period_id, group in operator_panel.groupby("Period_ID"):
    group = group.sort_values("Year")

    correlation_rows.append({
        "Level": "Operator",
        "Segment": group["Segment"].iloc[0],
        "Operator": group["Operator"].iloc[0],
        "Period": (
            f"{group['Year'].min()}-"
            f"{group['Year'].max()}"
        ),
        "N": len(group),
        "Pearson_r": safe_correlation(
            group["Revenue_Million_ALL"],
            group["Subscribers"]
        ),
        "Note": (
            "Exploratory levels correlation; "
            "no causal inference; verify definitions"
        )
    })

correlations = pd.DataFrame(correlation_rows)

# ---------------------------------------------
# 6. Annual growth-rate relationships
# ---------------------------------------------

growth_pairs = []

for segment, revenue_col, subscriber_col in [
    (
        "Mobile",
        "Mobile_Revenue_Million_ALL",
        "Mobile_Active_Broadband_Subs"
    ),
    (
        "Fixed",
        "Fixed_Revenue_Million_ALL",
        "Fixed_Broadband_Subs"
    ),
]:
    temp = pd.DataFrame({
        "Year": sector.index,
        "Segment": segment,
        "Revenue_YoY_Pct": (
            sector[revenue_col].pct_change() * 100
        ),
        "Subscriber_YoY_Pct": (
            sector[subscriber_col].pct_change() * 100
        ),
    })

    growth_pairs.append(temp.dropna())

growth_comparison = pd.concat(
    growth_pairs, ignore_index=True
)

# ---------------------------------------------
# 7. Export analytical workbook
# ---------------------------------------------

OUTPUT = TABLES / "revenue_subscriber_relationships.xlsx"

with pd.ExcelWriter(
    OUTPUT, engine="openpyxl"
) as writer:

    sector_results.to_excel(
        writer, sheet_name="Sector_Trends", index=False
    )

    growth_comparison.to_excel(
        writer, sheet_name="Growth_Comparison", index=False
    )

    all_matches.to_excel(
        writer, sheet_name="Operator_Matches", index=False
    )

    operator_panel.to_excel(
        writer, sheet_name="Comparable_Periods", index=False
    )

    coverage.to_excel(
        writer, sheet_name="Coverage_Checks", index=False
    )

    correlations.to_excel(
        writer, sheet_name="Correlations", index=False
    )

# ---------------------------------------------
# 8. Figures: indexed sector comparisons
# ---------------------------------------------

def plot_indexed_comparison(
    revenue_col, subscriber_col,
    title, output_filename
):
    plt.figure(figsize=(10, 6))

    plt.plot(
        sector.index,
        sector[revenue_col] / sector[revenue_col].iloc[0] * 100,
        marker="o",
        label="Reported revenue"
    )

    plt.plot(
        sector.index,
        sector[subscriber_col]
        / sector[subscriber_col].iloc[0] * 100,
        marker="s",
        label="Reported subscriptions"
    )

    plt.axhline(
        100, linestyle="--", linewidth=0.8
    )

    plt.title(title)
    plt.xlabel("Year")
    plt.ylabel("Index (2020 = 100)")
    plt.xticks(sector.index)
    plt.legend()
    plt.grid(alpha=0.25)
    plt.tight_layout()

    plt.savefig(
        FIGURES / output_filename, dpi=300
    )
    plt.close()

plot_indexed_comparison(
    "Mobile_Revenue_Million_ALL",
    "Mobile_Active_Broadband_Subs",
    "Mobile Revenue and Active Broadband Subscriptions",
    "mobile_revenue_subscriber_index.png"
)

plot_indexed_comparison(
    "Fixed_Revenue_Million_ALL",
    "Fixed_Broadband_Subs",
    "Fixed-Network Revenue and Broadband Subscriptions",
    "fixed_revenue_subscriber_index.png"
)

# ---------------------------------------------
# 9. Print results
# ---------------------------------------------

print("\nSECTOR TRENDS")
print(
    sector_results[
        [
            "Year",
            "Mobile_Revenue_Million_ALL",
            "Mobile_Active_Broadband_Subs",
            "Fixed_Revenue_Million_ALL",
            "Fixed_Broadband_Subs"
        ]
    ].round(2).to_string(index=False)
)

print("\nGROWTH COMPARISON")
print(
    growth_comparison.round(2).to_string(index=False)
)

print("\nOPERATOR PERIOD COVERAGE")
print(
    coverage.to_string(index=False)
)

print("\nEXPLORATORY CORRELATIONS")
print(
    correlations.round(3).to_string(index=False)
)

print("\nMATCH STATUS SUMMARY")
print(
    all_matches.groupby(
        ["Segment", "Match_Status"],
        observed=True
    ).size().to_string()
)

print("\nSaved:")
print(OUTPUT)
print(FIGURES / "mobile_revenue_subscriber_index.png")
print(FIGURES / "fixed_revenue_subscriber_index.png")

print("\nRELATIONSHIP ANALYSIS COMPLETED")
