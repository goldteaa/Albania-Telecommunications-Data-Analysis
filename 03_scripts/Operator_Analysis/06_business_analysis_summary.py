
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

TABLES = (
    ROOT / "04_outputs" / "Reproduced_Results"
    / "Operator_Analysis" / "Tables"
)

TABLES.mkdir(parents=True, exist_ok=True)

OUTPUT = TABLES / "business_analysis_summary.xlsx"

SOURCES = {
    "revenue": TABLES / "revenue_growth_results.xlsx",
    "subscribers": TABLES / "subscriber_growth_results.xlsx",
    "concentration": TABLES / "market_concentration_results.xlsx",
    "relationships": TABLES / "revenue_subscriber_relationships.xlsx",
}

for name, path in SOURCES.items():
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {name} analysis workbook: {path}"
        )

# ---------------------------------------------
# 1. Load previous analytical results
# ---------------------------------------------

revenue_growth = pd.read_excel(
    SOURCES["revenue"], sheet_name="Sector_Growth"
)
revenue_cagr = pd.read_excel(
    SOURCES["revenue"], sheet_name="Sector_CAGR"
)

mobile_subscribers = pd.read_excel(
    SOURCES["subscribers"], sheet_name="Mobile_Totals"
)
fixed_subscribers = pd.read_excel(
    SOURCES["subscribers"], sheet_name="Fixed_Totals"
)
subscriber_cagr = pd.read_excel(
    SOURCES["subscribers"], sheet_name="Subscriber_CAGR"
)

mobile_concentration = pd.read_excel(
    SOURCES["concentration"],
    sheet_name="Mobile_Concentration"
)
mobile_revenue_hhi = pd.read_excel(
    SOURCES["concentration"],
    sheet_name="Mobile_Revenue_HHI"
)
fixed_concentration = pd.read_excel(
    SOURCES["concentration"],
    sheet_name="Fixed_Concentration"
)

correlations = pd.read_excel(
    SOURCES["relationships"], sheet_name="Correlations"
)

# ---------------------------------------------
# 2. Combine subscriber annual totals
# ---------------------------------------------

subscriber_growth = mobile_subscribers.merge(
    fixed_subscribers,
    on="Year",
    suffixes=("_Mobile", "_Fixed"),
    validate="one_to_one"
)

# ---------------------------------------------
# 3. Generate key findings from actual results
# ---------------------------------------------

findings = []

def add_finding(category, indicator, period, value,
                unit, interpretation, qualification):
    findings.append({
        "Category": category,
        "Indicator": indicator,
        "Period": period,
        "Value": value,
        "Unit": unit,
        "Interpretation": interpretation,
        "Qualification": qualification,
    })

for _, row in revenue_cagr.iterrows():
    add_finding(
        "Revenue",
        f"{row['Segment']} revenue CAGR",
        f"{int(row['Start_Year'])}-{int(row['End_Year'])}",
        row["CAGR_Pct"],
        "Percent per year",
        "Annualized change in reported revenue",
        "Revenue definitions and segment overlap require review"
    )

for _, row in subscriber_cagr.iterrows():
    add_finding(
        "Subscriptions",
        f"{row['Segment']} subscription CAGR",
        f"{int(row['Start_Year'])}-{int(row['End_Year'])}",
        row["CAGR_Pct"],
        "Percent per year",
        "Annualized change in reported subscriptions",
        "Mobile active broadband and fixed broadband differ in scope"
    )

mobile_2024 = mobile_revenue_hhi.loc[
    mobile_revenue_hhi["Year"] == 2024
].iloc[0]

mobile_2022 = mobile_revenue_hhi.loc[
    mobile_revenue_hhi["Year"] == 2022
].iloc[0]

add_finding(
    "Concentration",
    "Mobile revenue HHI",
    "2024",
    mobile_2024["HHI_Calculated"],
    "HHI points",
    "Revenue-based mobile market concentration",
    "Calculated from reported operator revenues"
)

add_finding(
    "Concentration",
    "Mobile revenue HHI change",
    "2022-2023",
    (
        mobile_revenue_hhi.loc[
            mobile_revenue_hhi["Year"] == 2023,
            "HHI_Calculated"
        ].iloc[0]
        - mobile_2022["HHI_Calculated"]
    ),
    "HHI points",
    "Change coinciding with the ONE-Albtelecom merger",
    "Association with merger timing is not a causal estimate"
)

fixed_2024 = fixed_concentration.loc[
    fixed_concentration["Year"] == 2024
].iloc[0]

for bound in ["Lower", "Upper"]:
    add_finding(
        "Concentration",
        f"Fixed broadband HHI {bound.lower()} bound",
        "2024",
        fixed_2024[f"HHI_{bound}_Bound"],
        "HHI points",
        "Bound for fixed broadband market concentration",
        "Other Operators is an aggregated residual category"
    )

sector_corr = correlations.loc[
    correlations["Level"] == "Sector"
]

for _, row in sector_corr.iterrows():
    add_finding(
        "Relationships",
        f"{row['Segment']} revenue-subscriber correlation",
        row["Period"],
        row["Pearson_r"],
        "Pearson r",
        "Exploratory correlation between reported annual levels",
        "Five observations; differing indicator scopes; no causal inference"
    )

key_findings = pd.DataFrame(findings)

# ---------------------------------------------
# 4. Methodological notes
# ---------------------------------------------

notes = pd.DataFrame([
    {
        "Topic": "Data provenance",
        "Qualification": (
            "Administrative telecommunications statistics "
            "reported by AKEP for 2020-2024."
        )
    },
    {
        "Topic": "Mobile merger",
        "Qualification": (
            "ONE and Albtelecom were reported separately "
            "before consolidation. The 2022-2023 "
            "transition is not a like-for-like operator comparison."
        )
    },
    {
        "Topic": "Fixed historical categories",
        "Qualification": (
            "Historical fixed broadband ONE categories "
            "may not correspond directly to historical "
            "fixed-network revenue entities."
        )
    },
    {
        "Topic": "Other Operators",
        "Qualification": (
            "An aggregated category, not a single company. "
            "Exact fixed broadband HHI cannot be recovered "
            "without operator-level disaggregation."
        )
    },
    {
        "Topic": "Rounding",
        "Qualification": (
            "Published market shares and revenue figures "
            "are rounded. Small reconciliation differences "
            "are retained rather than artificially corrected."
        )
    },
    {
        "Topic": "2022 fixed revenues",
        "Qualification": (
            "The sum of reported operator revenues differs "
            "from the published sector total by "
            "36.03 million ALL. Both values are preserved."
        )
    },
    {
        "Topic": "Correlations",
        "Qualification": (
            "Pearson correlations are exploratory. "
            "Five annual observations do not support "
            "strong statistical or causal inference."
        )
    },
    {
        "Topic": "Revenue and subscriptions",
        "Qualification": (
            "Revenue and subscriber indicators do not "
            "necessarily cover identical services. "
            "Their ratio should not be labeled ARPU."
        )
    },
    {
        "Topic": "Combined revenue",
        "Qualification": (
            "Mobile plus fixed-network revenue is an "
            "arithmetic sum, not verified consolidated "
            "industry revenue."
        )
    },
])

# ---------------------------------------------
# 5. Export consolidated workbook
# ---------------------------------------------

with pd.ExcelWriter(
    OUTPUT, engine="openpyxl"
) as writer:

    key_findings.to_excel(
        writer, sheet_name="Key_Findings", index=False
    )

    revenue_growth.to_excel(
        writer, sheet_name="Revenue_Growth", index=False
    )

    revenue_cagr.to_excel(
        writer, sheet_name="Revenue_CAGR", index=False
    )

    subscriber_growth.to_excel(
        writer, sheet_name="Subscriber_Growth", index=False
    )

    subscriber_cagr.to_excel(
        writer, sheet_name="Subscriber_CAGR", index=False
    )

    mobile_concentration.to_excel(
        writer, sheet_name="Mobile_Concentration", index=False
    )

    mobile_revenue_hhi.to_excel(
        writer, sheet_name="Mobile_Revenue_HHI", index=False
    )

    fixed_concentration.to_excel(
        writer, sheet_name="Fixed_Concentration", index=False
    )

    correlations.to_excel(
        writer, sheet_name="Correlations", index=False
    )

    notes.to_excel(
        writer, sheet_name="Methodological_Notes", index=False
    )

# ---------------------------------------------
# 6. Print summary
# ---------------------------------------------

print("\nCONSOLIDATED KEY FINDINGS")
print(key_findings.round(3).to_string(index=False))

print("\nWORKBOOK SUMMARY")
print(f"Key findings: {len(key_findings)}")
print(f"Methodological notes: {len(notes)}")
print("Worksheets exported: 10")

print(f"\nSaved: {OUTPUT}")
print("\nBUSINESS ANALYSIS SUMMARY COMPLETED")
