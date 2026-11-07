
from pathlib import Path
import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "02_data" / "Operator_Data"
    / "Albania_Telecom_Operator_Data_2020_2024.xlsx"
)

OUTPUT = (
    ROOT / "04_outputs" / "Reproduced_Results"
    / "Operator_Analysis" / "Validation"
)

OUTPUT.mkdir(parents=True, exist_ok=True)

SHEETS = [
    "Mobile_Subscribers",
    "Mobile_Market_Shares",
    "Mobile_Revenues",
    "Fixed_Broadband",
    "Fixed_Revenues",
    "Fixed_Sector_Totals",
    "Source_Log",
    "Operator_Mapping",
]

EXPECTED_BROADBAND = {
    2020: 508937,
    2021: 559394,
    2022: 585285,
    2023: 632759,
    2024: 694635,
}

EXPECTED_MOBILE_REVENUE = {
    2020: 23898.73,
    2021: 24522.66,
    2022: 25434.75,
    2023: 25430.65,
    2024: 27928.45,
}

KEYS = {
    "Mobile_Subscribers": ["Year", "Operator"],
    "Mobile_Market_Shares": ["Year", "Operator", "Metric"],
    "Mobile_Revenues": ["Year", "Operator", "Revenue_Type"],
    "Fixed_Broadband": ["Year", "Operator"],
    "Fixed_Revenues": ["Year", "Operator"],
    "Fixed_Sector_Totals": ["Year"],
    "Operator_Mapping": [
        "Year", "Reported_Operator", "Market_Segment"
    ],
}

def main():
    print("\nALBANIA TELECOM — DATA VALIDATION")
    print("=" * 55)

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Workbook not found:\n{INPUT}"
        )

    data = pd.read_excel(INPUT, sheet_name=None)
    missing_sheets = set(SHEETS) - set(data)

    if missing_sheets:
        raise ValueError(
            f"Missing worksheets: {sorted(missing_sheets)}"
        )

    summary = []
    duplicates = []
    missing_records = []
    reconciliation = []
    mapping_issues = []

    # 1. Structural checks
    for name in SHEETS:
        df = data[name].dropna(how="all").copy()

        # Remove entirely empty extra columns
        df = df.dropna(axis=1, how="all")
        data[name] = df

        keys = KEYS.get(name, [])
        missing_columns = [c for c in keys if c not in df]

        if missing_columns:
            raise ValueError(
                f"{name}: Missing columns {missing_columns}"
            )

        if keys:
            dup = df[df.duplicated(keys, keep=False)]
            for _, row in dup.iterrows():
                duplicates.append({
                    "Sheet": name,
                    "Key": str(row[keys].to_dict())
                })

        for col in keys:
            for idx in df.index[df[col].isna()]:
                missing_records.append({
                    "Sheet": name,
                    "Excel_Row": int(idx) + 2,
                    "Column": col
                })

        summary.append({
            "Sheet": name,
            "Rows": len(df),
            "Columns": len(df.columns),
            "Duplicate_Rows": (
                int(df.duplicated(keys).sum()) if keys else 0
            ),
            "Missing_Key_Values": (
                int(df[keys].isna().sum().sum()) if keys else 0
            ),
        })

    # 2. Fixed broadband annual reconciliation
    fixed = data["Fixed_Broadband"]

    for year, expected in EXPECTED_BROADBAND.items():
        actual = fixed.loc[
            fixed["Year"] == year,
            "Fixed_Broadband_Subscribers"
        ].sum()

        reconciliation.append({
            "Dataset": "Fixed_Broadband",
            "Year": year,
            "Calculated": actual,
            "Expected": expected,
            "Difference": round(actual - expected, 2),
            "Status": (
                "MATCH" if abs(actual - expected) < 0.01
                else "REVIEW"
            )
        })

    # 3. Mobile revenue reconciliation
    mobile = data["Mobile_Revenues"]

    for year, expected in EXPECTED_MOBILE_REVENUE.items():
        actual = mobile.loc[
            mobile["Year"] == year,
            "Revenue_Million_ALL"
        ].sum()

        difference = round(actual - expected, 2)

        reconciliation.append({
            "Dataset": "Mobile_Revenues",
            "Year": year,
            "Calculated": actual,
            "Expected": expected,
            "Difference": difference,
            "Status": (
                "MATCH" if abs(difference) < 0.005
                else "ROUNDING" if abs(difference) <= 0.011
                else "REVIEW"
            )
        })

    # 4. Fixed-network revenue reconciliation
    fixed_revenue = data["Fixed_Revenues"]
    sector = data["Fixed_Sector_Totals"]

    for _, record in sector.iterrows():
        year = int(record["Year"])
        expected = record["Total_Revenue_Million_ALL"]

        actual = fixed_revenue.loc[
            fixed_revenue["Year"] == year,
            "Revenue_Million_ALL"
        ].sum()

        difference = round(actual - expected, 2)

        reconciliation.append({
            "Dataset": "Fixed_Revenues",
            "Year": year,
            "Calculated": actual,
            "Expected": expected,
            "Difference": difference,
            "Status": (
                "MATCH" if abs(difference) < 0.005
                else "ROUNDING" if abs(difference) <= 0.011
                else "SOURCE_DISCREPANCY"
            )
        })

    # 5. Mapping coverage
    mapping = data["Operator_Mapping"]

    source_segments = {
        "Mobile_Subscribers": "Mobile",
        "Mobile_Revenues": "Mobile",
        "Fixed_Broadband": "Fixed_Broadband",
        "Fixed_Revenues": "Fixed_Revenue",
    }

    for sheet, segment in source_segments.items():
        source = data[sheet][["Year", "Operator"]].drop_duplicates()

        relevant = mapping.loc[
            mapping["Market_Segment"] == segment,
            ["Year", "Reported_Operator"]
        ].drop_duplicates()

        joined = source.merge(
            relevant,
            left_on=["Year", "Operator"],
            right_on=["Year", "Reported_Operator"],
            how="left",
            indicator=True
        )

        for _, row in joined.loc[
            joined["_merge"] == "left_only"
        ].iterrows():
            mapping_issues.append({
                "Source_Sheet": sheet,
                "Year": row["Year"],
                "Operator": row["Operator"],
                "Issue": "Missing mapping"
            })

    # 6. Export reports
    report = OUTPUT / "business_data_validation.xlsx"

    with pd.ExcelWriter(report, engine="openpyxl") as writer:
        pd.DataFrame(summary).to_excel(
            writer, sheet_name="Sheet_Summary", index=False
        )
        pd.DataFrame(reconciliation).to_excel(
            writer, sheet_name="Reconciliation", index=False
        )
        pd.DataFrame(
            duplicates, columns=["Sheet", "Key"]
        ).to_excel(writer, sheet_name="Duplicates", index=False)
        pd.DataFrame(
            missing_records,
            columns=["Sheet", "Excel_Row", "Column"]
        ).to_excel(writer, sheet_name="Missing_Keys", index=False)
        pd.DataFrame(
            mapping_issues,
            columns=["Source_Sheet", "Year", "Operator", "Issue"]
        ).to_excel(writer, sheet_name="Mapping_Issues", index=False)

    print("\nWORKSHEET SUMMARY")
    print(pd.DataFrame(summary).to_string(index=False))

    print("\nFINANCIAL AND SUBSCRIBER RECONCILIATION")
    print(pd.DataFrame(reconciliation).to_string(index=False))

    print("\nQUALITY CHECKS")
    print(f"Duplicate records: {len(duplicates)}")
    print(f"Missing key values: {len(missing_records)}")
    print(f"Unmapped observations: {len(mapping_issues)}")

    print(f"\nValidation report saved:\n{report}")
    print("\nVALIDATION SCRIPT COMPLETED")


if __name__ == "__main__":
    main()
