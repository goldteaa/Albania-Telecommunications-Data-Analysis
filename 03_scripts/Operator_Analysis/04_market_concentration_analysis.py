
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

mobile_shares = pd.read_excel(
    INPUT, sheet_name="Mobile_Market_Shares"
)

mobile_revenues = pd.read_excel(
    INPUT, sheet_name="Mobile_Revenues"
)

fixed = pd.read_excel(
    INPUT, sheet_name="Fixed_Broadband"
)

# ---------------------------------------------
# 1. Concentration functions
# ---------------------------------------------

def calculate_cr2(shares):
    values = np.sort(np.asarray(shares, dtype=float))[::-1]
    return values[:2].sum()

def calculate_hhi(shares):
    values = np.asarray(shares, dtype=float)
    return np.sum(values ** 2)

# ---------------------------------------------
# 2. Mobile market concentration
# ---------------------------------------------

mobile_results = []
mobile_validation = []

for (metric, year), group in mobile_shares.groupby(
    ["Metric", "Year"]
):
    shares = group["Market_Share_Percent"].astype(float)

    share_total = shares.sum()

    mobile_validation.append({
        "Metric": metric,
        "Year": year,
        "Share_Total_Pct": share_total,
        "Difference_From_100": share_total - 100,
        "Status": (
            "MATCH" if abs(share_total - 100) < 0.01
            else "ROUNDING_REVIEW"
            if abs(share_total - 100) <= 1.01
            else "DATA_REVIEW"
        )
    })

    # Avoid interpreting materially incomplete shares
    if abs(share_total - 100) > 1.01:
        continue

    mobile_results.append({
        "Metric": metric,
        "Year": year,
        "Number_Of_Reported_Operators": len(group),
        "CR2_Pct": calculate_cr2(shares),
        "HHI_Reported": calculate_hhi(shares),
        "Share_Total_Pct": share_total,
        "Calculation_Note": (
            "Calculated from rounded reported shares; "
            "not renormalized"
        )
    })

mobile_concentration = pd.DataFrame(mobile_results)
mobile_share_validation = pd.DataFrame(mobile_validation)

# ---------------------------------------------
# 3. Mobile revenue concentration
# ---------------------------------------------

mobile_revenue_results = []

for year, group in mobile_revenues.groupby("Year"):
    total = group["Revenue_Million_ALL"].sum()

    shares = (
        group["Revenue_Million_ALL"] / total * 100
    )

    mobile_revenue_results.append({
        "Year": year,
        "Number_Of_Reported_Operators": len(group),
        "CR2_Pct": calculate_cr2(shares),
        "HHI_Calculated": calculate_hhi(shares),
        "Revenue_Total_Million_ALL": total,
        "Note": "Calculated from reported operator revenues"
    })

mobile_revenue_concentration = pd.DataFrame(
    mobile_revenue_results
)

# ---------------------------------------------
# 4. Fixed broadband market concentration
# ---------------------------------------------

fixed_results = []
fixed_operator_shares = []

for year, group in fixed.groupby("Year"):
    total = group["Fixed_Broadband_Subscribers"].sum()

    individual = group.loc[
        group["Operator"] != "Other Operators"
    ].copy()

    other = group.loc[
        group["Operator"] == "Other Operators"
    ]

    if len(other) != 1:
        raise ValueError(
            f"Year {year}: Expected one Other Operators row."
        )

    other_share = (
        other["Fixed_Broadband_Subscribers"].iloc[0]
        / total * 100
    )

    individual_shares = (
        individual["Fixed_Broadband_Subscribers"]
        / total * 100
    )

    for _, row in group.iterrows():
        fixed_operator_shares.append({
            "Year": year,
            "Operator": row["Operator"],
            "Subscribers": row["Fixed_Broadband_Subscribers"],
            "Market_Share_Pct": (
                row["Fixed_Broadband_Subscribers"]
                / total * 100
            )
        })

    # HHI lower bound: known individual contributions.
    # The residual category contains multiple operators.
    hhi_lower = calculate_hhi(individual_shares)

    # HHI upper bound: maximum possible contribution
    # if the entire residual were one operator.
    hhi_upper = hhi_lower + other_share ** 2

    # The two largest known individual operators
    # establish a lower bound for the actual CR2.
    cr2_lower = calculate_cr2(individual_shares)

    # Upper bound allowing residual operators to
    # contribute to the top two.
    cr2_upper = max(
        cr2_lower,
        other_share + individual_shares.max()
    )
    
    fixed_results.append({
        "Year": year,
        "Total_Subscribers": total,
        "Other_Operators_Share_Pct": other_share,
        "CR2_Lower_Bound_Pct": cr2_lower,
        "CR2_Upper_Bound_Pct": cr2_upper,
        "HHI_Lower_Bound": hhi_lower,
        "HHI_Upper_Bound": hhi_upper,
        "Note": (
            "Bounds reflect aggregated Other Operators; "
            "exact firm-level concentration unavailable"
        )
    })

fixed_concentration = pd.DataFrame(fixed_results)
fixed_shares = pd.DataFrame(fixed_operator_shares)

# ---------------------------------------------
# 5. Export tables
# ---------------------------------------------

with pd.ExcelWriter(
    TABLES / "market_concentration_results.xlsx",
    engine="openpyxl"
) as writer:

    mobile_concentration.to_excel(
        writer, sheet_name="Mobile_Concentration", index=False
    )

    mobile_share_validation.to_excel(
        writer, sheet_name="Mobile_Share_Checks", index=False
    )

    mobile_revenue_concentration.to_excel(
        writer, sheet_name="Mobile_Revenue_HHI", index=False
    )

    fixed_concentration.to_excel(
        writer, sheet_name="Fixed_Concentration", index=False
    )

    fixed_shares.to_excel(
        writer, sheet_name="Fixed_Operator_Shares", index=False
    )

# ---------------------------------------------
# 6. Figure: mobile HHI by metric
# ---------------------------------------------

plt.figure(figsize=(11, 6))

for metric, group in mobile_concentration.groupby("Metric"):
    group = group.sort_values("Year")
    plt.plot(
        group["Year"],
        group["HHI_Reported"],
        marker="o",
        label=metric.replace("_", " ")
    )

plt.title("Mobile Market Concentration by Indicator")
plt.xlabel("Year")
plt.ylabel("HHI (0–10,000)")
plt.xticks(sorted(mobile_shares["Year"].unique()))
plt.legend(fontsize=8)
plt.grid(alpha=0.25)
plt.tight_layout()

plt.savefig(
    FIGURES / "mobile_market_hhi.png",
    dpi=300
)
plt.close()

# ---------------------------------------------
# 7. Figure: fixed broadband HHI bounds
# ---------------------------------------------

plt.figure(figsize=(10, 6))

plt.plot(
    fixed_concentration["Year"],
    fixed_concentration["HHI_Lower_Bound"],
    marker="o",
    label="HHI lower bound"
)

plt.plot(
    fixed_concentration["Year"],
    fixed_concentration["HHI_Upper_Bound"],
    marker="s",
    label="HHI upper bound"
)

plt.fill_between(
    fixed_concentration["Year"],
    fixed_concentration["HHI_Lower_Bound"],
    fixed_concentration["HHI_Upper_Bound"],
    alpha=0.15
)

plt.title("Fixed Broadband Market Concentration Bounds")
plt.xlabel("Year")
plt.ylabel("HHI (0–10,000)")
plt.xticks(fixed_concentration["Year"])
plt.legend()
plt.grid(alpha=0.25)
plt.tight_layout()

plt.savefig(
    FIGURES / "fixed_broadband_hhi_bounds.png",
    dpi=300
)
plt.close()

# ---------------------------------------------
# 8. Print results
# ---------------------------------------------

print("\nMOBILE MARKET SHARE VALIDATION")
print(
    mobile_share_validation.round(2).to_string(index=False)
)

print("\nMOBILE MARKET CONCENTRATION")
print(
    mobile_concentration.round(2).to_string(index=False)
)

print("\nMOBILE REVENUE CONCENTRATION")
print(
    mobile_revenue_concentration.round(2).to_string(index=False)
)

print("\nFIXED BROADBAND CONCENTRATION")
print(
    fixed_concentration.round(2).to_string(index=False)
)

print("\nSaved:")
print(TABLES / "market_concentration_results.xlsx")
print(FIGURES / "mobile_market_hhi.png")
print(FIGURES / "fixed_broadband_hhi_bounds.png")

print("\nMARKET CONCENTRATION ANALYSIS COMPLETED")
