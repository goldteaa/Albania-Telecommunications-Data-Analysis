
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

# Load data
mobile = pd.read_excel(INPUT, sheet_name="Mobile_Revenues")
fixed = pd.read_excel(INPUT, sheet_name="Fixed_Revenues")
sector = pd.read_excel(INPUT, sheet_name="Fixed_Sector_Totals")

for df in (mobile, fixed, sector):
    df["Year"] = pd.to_numeric(df["Year"]).astype(int)

# ---------------------------------------------
# 1. Sector-level revenue growth
# ---------------------------------------------

mobile_totals = (
    mobile.groupby("Year", as_index=False)["Revenue_Million_ALL"]
    .sum()
    .rename(columns={"Revenue_Million_ALL": "Mobile_Revenue"})
)

fixed_totals = sector[
    ["Year", "Total_Revenue_Million_ALL"]
].rename(columns={
    "Total_Revenue_Million_ALL": "Fixed_Revenue"
})

sector_growth = mobile_totals.merge(
    fixed_totals, on="Year", how="inner"
).sort_values("Year")

sector_growth["Mobile_YoY_Pct"] = (
    sector_growth["Mobile_Revenue"].pct_change() * 100
)

sector_growth["Fixed_YoY_Pct"] = (
    sector_growth["Fixed_Revenue"].pct_change() * 100
)

sector_growth["Combined_Revenue"] = (
    sector_growth["Mobile_Revenue"]
    + sector_growth["Fixed_Revenue"]
)

sector_growth["Combined_YoY_Pct"] = (
    sector_growth["Combined_Revenue"].pct_change() * 100
)

def cagr(start, end, periods):
    if periods <= 0 or start <= 0 or end < 0:
        return np.nan
    return ((end / start) ** (1 / periods) - 1) * 100

first = sector_growth.iloc[0]
last = sector_growth.iloc[-1]
periods = int(last["Year"] - first["Year"])

sector_cagr = pd.DataFrame([
    {
        "Segment": "Mobile",
        "Start_Year": int(first["Year"]),
        "End_Year": int(last["Year"]),
        "CAGR_Pct": cagr(
            first["Mobile_Revenue"],
            last["Mobile_Revenue"],
            periods
        )
    },
    {
        "Segment": "Fixed",
        "Start_Year": int(first["Year"]),
        "End_Year": int(last["Year"]),
        "CAGR_Pct": cagr(
            first["Fixed_Revenue"],
            last["Fixed_Revenue"],
            periods
        )
    },
    {
        "Segment": "Combined",
        "Start_Year": int(first["Year"]),
        "End_Year": int(last["Year"]),
        "CAGR_Pct": cagr(
            first["Combined_Revenue"],
            last["Combined_Revenue"],
            periods
        )
    }
])

# ---------------------------------------------
# 2. Operator-level revenue growth
# ---------------------------------------------

def operator_growth(df, segment):
    result = df[
        ["Year", "Operator", "Revenue_Million_ALL"]
    ].copy()

    result["Segment"] = segment

    result = result.sort_values(["Operator", "Year"])

    result["Previous_Year"] = (
        result.groupby("Operator")["Year"].shift(1)
    )

    result["Previous_Revenue"] = (
        result.groupby("Operator")["Revenue_Million_ALL"].shift(1)
    )

    result["YoY_Growth_Pct"] = (
        (result["Revenue_Million_ALL"]
         / result["Previous_Revenue"] - 1) * 100
    )

    # Do not interpret gaps as annual growth
    consecutive = (
        result["Year"] - result["Previous_Year"] == 1
    )
    result.loc[~consecutive, "YoY_Growth_Pct"] = np.nan

    # Merger and acquisition flags
    result["Comparability_Flag"] = "Review_Definitions"

    if segment == "Mobile":
        result.loc[
            (result["Operator"] == "ONE Albania")
            & (result["Year"] == 2023),
            "Comparability_Flag"
        ] = "Merger_Affected"

        result.loc[
            (result["Operator"] == "Albtelecom"),
            "Comparability_Flag"
        ] = "Pre_Merger_Entity"

    if segment == "Fixed":
        result.loc[
            (result["Operator"] == "ONE Albania")
            & (result["Year"] == 2023),
            "Comparability_Flag"
        ] = "Merger_Affected"

        result.loc[
            (result["Operator"] == "Vodafone Albania")
            & (result["Year"] == 2021),
            "Comparability_Flag"
        ] = "Acquisition_Affected"

        result.loc[
            result["Operator"] == "Other Operators",
            "Comparability_Flag"
        ] = "Aggregated_Category"

    result["Comparable_YoY_Pct"] = result["YoY_Growth_Pct"]

    result.loc[
        result["Comparability_Flag"].isin([
            "Merger_Affected",
            "Acquisition_Affected",
            "Aggregated_Category"
        ]),
        "Comparable_YoY_Pct"
    ] = np.nan

    return result

mobile_growth = operator_growth(mobile, "Mobile")
fixed_growth = operator_growth(fixed, "Fixed")

operator_results = pd.concat(
    [mobile_growth, fixed_growth],
    ignore_index=True
)


# ---------------------------------------------
# 3. Operator CAGR — comparable periods
# ---------------------------------------------

# Explicit analytical windows.
# The merger transition is never included in
# a like-for-like operator CAGR calculation.

CAGR_WINDOWS = [
    # Mobile operators
    ("Mobile", "ONE Albania", 2020, 2022,
     "Pre-merger ONE historical series"),

    ("Mobile", "ONE Albania", 2023, 2024,
     "Post-merger consolidated ONE"),

    ("Mobile", "Albtelecom", 2020, 2022,
     "Pre-merger Albtelecom"),

    ("Mobile", "Vodafone Albania", 2020, 2024,
     "Reported Vodafone series"),

    # Fixed-network operators
    ("Fixed", "Albtelecom", 2020, 2022,
     "Pre-merger Albtelecom"),

    ("Fixed", "ONE Albania", 2023, 2024,
     "Post-merger consolidated ONE"),

    ("Fixed", "Vodafone Albania", 2021, 2024,
     "Post-acquisition Vodafone series"),

    ("Fixed", "ASC", 2020, 2024,
     "Reported continuous series"),

    ("Fixed", "Abissnet", 2020, 2024,
     "Reported continuous series"),

    ("Fixed", "Digicom", 2020, 2024,
     "Reported continuous series"),

    ("Fixed", "Nisatel", 2020, 2024,
     "Reported continuous series"),
]

cagr_rows = []

for segment, operator, start_year, end_year, note in CAGR_WINDOWS:

    group = operator_results.loc[
        (operator_results["Segment"] == segment)
        & (operator_results["Operator"] == operator)
        & (operator_results["Year"].between(
            start_year, end_year
        ))
    ].sort_values("Year")

    expected_years = list(
        range(start_year, end_year + 1)
    )

    actual_years = group["Year"].tolist()

    if actual_years != expected_years:
        print(
            f"WARNING: Skipping {segment} / {operator} "
            f"({start_year}-{end_year}): "
            f"expected {expected_years}, got {actual_years}"
        )
        continue

    start_revenue = float(
        group.iloc[0]["Revenue_Million_ALL"]
    )

    end_revenue = float(
        group.iloc[-1]["Revenue_Million_ALL"]
    )

    growth = cagr(
        start_revenue,
        end_revenue,
        end_year - start_year
    )

    cagr_rows.append({
        "Segment": segment,
        "Operator": operator,
        "Start_Year": start_year,
        "End_Year": end_year,
        "Start_Revenue_Million_ALL": start_revenue,
        "End_Revenue_Million_ALL": end_revenue,
        "CAGR_Pct": growth,
        "Comparability_Note": note,
    })

operator_cagr = pd.DataFrame(
    cagr_rows,
    columns=[
        "Segment",
        "Operator",
        "Start_Year",
        "End_Year",
        "Start_Revenue_Million_ALL",
        "End_Revenue_Million_ALL",
        "CAGR_Pct",
        "Comparability_Note",
    ]
)

# Exclude merger-affected annual comparisons
# from the like-for-like growth measure.
operator_results.loc[
    (operator_results["Segment"] == "Mobile")
    & (operator_results["Operator"] == "ONE Albania")
    & (operator_results["Year"] == 2023),
    "Comparable_YoY_Pct"
] = np.nan

operator_results.loc[
    (operator_results["Segment"] == "Fixed")
    & (operator_results["Operator"] == "ONE Albania")
    & (operator_results["Year"] == 2023),
    "Comparable_YoY_Pct"
] = np.nan


# ---------------------------------------------
# 4. Export Excel results
# ---------------------------------------------

with pd.ExcelWriter(
    TABLES / "revenue_growth_results.xlsx",
    engine="openpyxl"
) as writer:
    sector_growth.to_excel(
        writer, sheet_name="Sector_Growth", index=False
    )
    sector_cagr.to_excel(
        writer, sheet_name="Sector_CAGR", index=False
    )
    operator_results.to_excel(
        writer, sheet_name="Operator_Growth", index=False
    )
    operator_cagr.to_excel(
        writer, sheet_name="Operator_CAGR", index=False
    )

# ---------------------------------------------
# 5. Figure: sector revenue trends
# ---------------------------------------------

plt.figure(figsize=(10, 6))

plt.plot(
    sector_growth["Year"],
    sector_growth["Mobile_Revenue"],
    marker="o",
    label="Mobile"
)
plt.plot(
    sector_growth["Year"],
    sector_growth["Fixed_Revenue"],
    marker="s",
    label="Fixed-network"
)

plt.title("Albania Telecommunications Revenue, 2020–2024")
plt.xlabel("Year")
plt.ylabel("Revenue (million ALL)")
plt.xticks(sector_growth["Year"])
plt.legend()
plt.grid(alpha=0.25)
plt.tight_layout()

plt.savefig(
    FIGURES / "sector_revenue_trends.png",
    dpi=300
)
plt.close()

# ---------------------------------------------
# 6. Figure: annual sector revenue growth
# ---------------------------------------------

growth_plot = sector_growth.dropna(
    subset=["Mobile_YoY_Pct", "Fixed_YoY_Pct"]
)

x = np.arange(len(growth_plot))
width = 0.35

plt.figure(figsize=(10, 6))
plt.bar(
    x - width / 2,
    growth_plot["Mobile_YoY_Pct"],
    width,
    label="Mobile"
)
plt.bar(
    x + width / 2,
    growth_plot["Fixed_YoY_Pct"],
    width,
    label="Fixed-network"
)

plt.axhline(0, linewidth=0.8)
plt.xticks(x, growth_plot["Year"])
plt.title("Annual Telecommunications Revenue Growth")
plt.xlabel("Year")
plt.ylabel("Year-over-year growth (%)")
plt.legend()
plt.tight_layout()

plt.savefig(
    FIGURES / "sector_revenue_yoy_growth.png",
    dpi=300
)
plt.close()

# ---------------------------------------------
# 7. Print results
# ---------------------------------------------

print("\nSECTOR REVENUE GROWTH")
print(sector_growth.round(2).to_string(index=False))

print("\nSECTOR CAGR")
print(sector_cagr.round(2).to_string(index=False))

print("\nOPERATOR GROWTH — LAST OBSERVATIONS")
print(
    operator_results[
        ["Segment", "Year", "Operator",
         "Revenue_Million_ALL", "YoY_Growth_Pct",
         "Comparability_Flag"]
    ].tail(15).round(2).to_string(index=False)
)

print("\nOPERATOR CAGR")
print(operator_cagr.round(2).to_string(index=False))

print("\nSaved:")
print(TABLES / "revenue_growth_results.xlsx")
print(FIGURES / "sector_revenue_trends.png")
print(FIGURES / "sector_revenue_yoy_growth.png")

print("\nREVENUE ANALYSIS COMPLETED")
