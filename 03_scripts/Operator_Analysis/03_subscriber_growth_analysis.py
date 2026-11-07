
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

mobile = pd.read_excel(INPUT, sheet_name="Mobile_Subscribers")
fixed = pd.read_excel(INPUT, sheet_name="Fixed_Broadband")

for df in (mobile, fixed):
    df["Year"] = pd.to_numeric(
        df["Year"], errors="raise"
    ).astype(int)

def calculate_cagr(start, end, years):
    if years <= 0 or start <= 0 or end < 0:
        return np.nan
    return ((end / start) ** (1 / years) - 1) * 100

# ---------------------------------------------
# 1. Confirm column names
# ---------------------------------------------

print("\nMOBILE SUBSCRIBER COLUMNS")
print(mobile.columns.tolist())

print("\nFIXED BROADBAND COLUMNS")
print(fixed.columns.tolist())

# Identify the relevant subscriber columns.
# Stop rather than silently choosing an
# incorrect subscription metric.

MOBILE_VALUE_COLUMN = "Active_Broadband_Subscribers"
FIXED_VALUE_COLUMN = "Fixed_Broadband_Subscribers"

for name, df, value_column in [
    ("Mobile_Subscribers", mobile, MOBILE_VALUE_COLUMN),
    ("Fixed_Broadband", fixed, FIXED_VALUE_COLUMN),
]:
    required = ["Year", "Operator", value_column]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{name}: Missing columns {missing}. "
            f"Available columns: {df.columns.tolist()}"
        )

    df[value_column] = pd.to_numeric(
        df[value_column], errors="raise"
    )

    if df[value_column].isna().any():
        raise ValueError(
            f"{name}: Missing subscriber values found."
        )

    if (df[value_column] < 0).any():
        raise ValueError(
            f"{name}: Negative subscriber values found."
        )

# ---------------------------------------------
# 2. Annual subscriber totals
# ---------------------------------------------

def annual_growth(df, value_column):
    result = (
        df.groupby("Year", as_index=False)[value_column]
        .sum()
        .rename(columns={value_column: "Subscribers"})
        .sort_values("Year")
    )

    result["YoY_Growth_Pct"] = (
        result["Subscribers"].pct_change() * 100
    )

    result["Annual_Change"] = (
        result["Subscribers"].diff()
    )

    return result

mobile_totals = annual_growth(
    mobile, MOBILE_VALUE_COLUMN
)

fixed_totals = annual_growth(
    fixed, FIXED_VALUE_COLUMN
)

# ---------------------------------------------
# 3. Sector CAGR
# ---------------------------------------------

cagr_rows = []

for segment, totals in [
    ("Mobile", mobile_totals),
    ("Fixed_Broadband", fixed_totals),
]:
    start = totals.iloc[0]
    end = totals.iloc[-1]

    cagr_rows.append({
        "Segment": segment,
        "Start_Year": int(start["Year"]),
        "End_Year": int(end["Year"]),
        "Start_Subscribers": start["Subscribers"],
        "End_Subscribers": end["Subscribers"],
        "CAGR_Pct": calculate_cagr(
            start["Subscribers"],
            end["Subscribers"],
            int(end["Year"] - start["Year"])
        )
    })

subscriber_cagr = pd.DataFrame(cagr_rows)

# ---------------------------------------------
# 4. Operator-level subscriber growth
# ---------------------------------------------

def operator_growth(df, value_column, segment):
    result = df[
        ["Year", "Operator", value_column]
    ].copy()

    result = result.rename(
        columns={value_column: "Subscribers"}
    )

    result["Segment"] = segment

    result = result.sort_values(
        ["Operator", "Year"]
    )

    result["Previous_Year"] = (
        result.groupby("Operator")["Year"].shift()
    )

    result["Previous_Subscribers"] = (
        result.groupby("Operator")["Subscribers"].shift()
    )

    result["YoY_Growth_Pct"] = (
        result["Subscribers"]
        / result["Previous_Subscribers"] - 1
    ) * 100

    consecutive = (
        result["Year"] - result["Previous_Year"] == 1
    )

    result.loc[
        ~consecutive, "YoY_Growth_Pct"
    ] = np.nan

    result["Comparability_Note"] = (
        "Reported series; verify definitions"
    )

    if segment == "Mobile":
        result.loc[
            (result["Operator"] == "ONE Albania")
            & (result["Year"] == 2023),
            "Comparability_Note"
        ] = "Merger transition; not like-for-like"

    if segment == "Fixed_Broadband":
        result.loc[
            result["Operator"] == "Other Operators",
            "Comparability_Note"
        ] = "Aggregated residual category"

        result.loc[
            (result["Operator"] == "ONE Albania")
            & (result["Year"] == 2023),
            "Comparability_Note"
        ] = "Potential structural break; review AKEP definition"

    result["Comparable_YoY_Pct"] = (
        result["YoY_Growth_Pct"]
    )

    result.loc[
        result["Comparability_Note"].isin([
            "Merger transition; not like-for-like",
            "Potential structural break; review AKEP definition",
            "Aggregated residual category"
        ]),
        "Comparable_YoY_Pct"
    ] = np.nan

    return result

mobile_operator = operator_growth(
    mobile, MOBILE_VALUE_COLUMN, "Mobile"
)

fixed_operator = operator_growth(
    fixed, FIXED_VALUE_COLUMN, "Fixed_Broadband"
)

operator_results = pd.concat(
    [mobile_operator, fixed_operator],
    ignore_index=True
)

# ---------------------------------------------
# 5. Fixed broadband net subscriber changes
# ---------------------------------------------

fixed_pivot = fixed.pivot(
    index="Operator",
    columns="Year",
    values=FIXED_VALUE_COLUMN
)

fixed_changes = pd.DataFrame({
    "Operator": fixed_pivot.index,
    "Subscribers_2020": fixed_pivot[2020],
    "Subscribers_2024": fixed_pivot[2024]
}).reset_index(drop=True)

fixed_changes["Net_Change"] = (
    fixed_changes["Subscribers_2024"]
    - fixed_changes["Subscribers_2020"]
)

total_net_change = fixed_changes["Net_Change"].sum()

fixed_changes["Contribution_To_Net_Growth_Pct"] = (
    fixed_changes["Net_Change"]
    / total_net_change * 100
    if total_net_change != 0 else np.nan
)

fixed_changes = fixed_changes.sort_values(
    "Net_Change", ascending=False
)

# ---------------------------------------------
# 6. Export Excel tables
# ---------------------------------------------

with pd.ExcelWriter(
    TABLES / "subscriber_growth_results.xlsx",
    engine="openpyxl"
) as writer:
    mobile_totals.to_excel(
        writer, sheet_name="Mobile_Totals", index=False
    )
    fixed_totals.to_excel(
        writer, sheet_name="Fixed_Totals", index=False
    )
    subscriber_cagr.to_excel(
        writer, sheet_name="Subscriber_CAGR", index=False
    )
    operator_results.to_excel(
        writer, sheet_name="Operator_Growth", index=False
    )
    fixed_changes.to_excel(
        writer, sheet_name="Fixed_Net_Changes", index=False
    )

# ---------------------------------------------
# 7. Figure: mobile subscriber trend
# ---------------------------------------------

plt.figure(figsize=(10, 6))

plt.plot(
    mobile_totals["Year"],
    mobile_totals["Subscribers"] / 1_000_000,
    marker="o"
)

plt.title(
    "Albania Active Mobile Broadband Subscriptions, 2020–2024"
)
plt.xlabel("Year")
plt.ylabel("Active mobile broadband subscriptions (millions)")
plt.xticks(mobile_totals["Year"])
plt.grid(alpha=0.25)
plt.tight_layout()

plt.savefig(
    FIGURES / "mobile_subscriber_trends.png",
    dpi=300
)
plt.close()


# ---------------------------------------------
# 8. Figure: fixed broadband subscriber trend
# ---------------------------------------------

plt.figure(figsize=(10, 6))

plt.plot(
    fixed_totals["Year"],
    fixed_totals["Subscribers"],
    marker="o"
)

plt.title("Albania Fixed Broadband Subscribers, 2020–2024")
plt.xlabel("Year")
plt.ylabel("Fixed broadband subscribers")
plt.xticks(fixed_totals["Year"])
plt.grid(alpha=0.25)
plt.tight_layout()

plt.savefig(
    FIGURES / "fixed_broadband_subscriber_trends.png",
    dpi=300
)
plt.close()

# ---------------------------------------------
# 9. Print results
# ---------------------------------------------

print("\nMOBILE SUBSCRIBER TOTALS")
print(mobile_totals.round(2).to_string(index=False))

print("\nFIXED BROADBAND TOTALS")
print(fixed_totals.round(2).to_string(index=False))

print("\nSUBSCRIBER CAGR")
print(subscriber_cagr.round(2).to_string(index=False))

print("\nFIXED BROADBAND NET CHANGES")
print(fixed_changes.round(2).to_string(index=False))

print("\nSaved:")
print(TABLES / "subscriber_growth_results.xlsx")
print(FIGURES / "mobile_subscriber_trends.png")
print(FIGURES / "fixed_broadband_subscriber_trends.png")

print("\nSUBSCRIBER ANALYSIS COMPLETED")
