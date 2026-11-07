
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILE = (
    BASE_DIR / "02_data" / "National_ICT"
    / "Albania_Telecom_Master_2020_2024_V1_FINAL.xlsx"
)

DAY3_OUTPUT_DIR = (
    BASE_DIR / "04_outputs" / "Reproduced_Results"
    / "National_Analysis"
)

FIGURES_DIR = DAY3_OUTPUT_DIR / "Forecast_Figures"
TABLES_DIR = DAY3_OUTPUT_DIR / "Forecast_Tables"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 2. LOAD DATA
# ------------------------------------------------------------

master = pd.read_excel(DATA_FILE, sheet_name="Master_Data")
kpi_selection = pd.read_excel(DATA_FILE, sheet_name="KPI_Selection")
dictionary = pd.read_excel(DATA_FILE, sheet_name="Data_Dictionary")


print("\nDAY 3 RELATIONSHIPS AND FORECASTING")
print("=" * 55)

print("\nWorkbook loaded successfully.")

print(f"\nMaster_Data:     {master.shape[0]} rows x {master.shape[1]} columns")
print(
    f"KPI_Selection:   "
    f"{kpi_selection.shape[0]} rows x {kpi_selection.shape[1]} columns"
)

print(
    f"Data_Dictionary: "
    f"{dictionary.shape[0]} rows x {dictionary.shape[1]} columns"
)


# ------------------------------------------------------------
# 3. DEFINE DAY 3 KPIs
# ------------------------------------------------------------

DAY3_KPIS = {
    "i4213tfbbb": "Fixed-broadband subscriptions",
    "i4213ftth/b": "FTTH/B subscriptions",
    "i4213_G100": "100+ Mbit/s broadband subscriptions",
    "i271mw": "Active mobile-broadband subscriptions",
    "i135tfb": "Fixed-broadband Internet traffic",
    "i136mwi": "Mobile-broadband Internet traffic",
    "i133mm": "Outgoing mobile voice traffic",
    "i75": "Telecommunications revenue",
    "i81": "Telecommunications investment",
}


# ------------------------------------------------------------
# 4. EXTRACT DAY 3 DATA
# ------------------------------------------------------------

analysis_data = master[
    master["IndicatorCode"].isin(DAY3_KPIS.keys())
].copy()

analysis_data["ShortName"] = analysis_data["IndicatorCode"].map(DAY3_KPIS)

analysis_data = analysis_data.sort_values(
    ["IndicatorCode", "Year"]
).reset_index(drop=True)


# ------------------------------------------------------------
# 5. CHECK DATA AVAILABILITY
# ------------------------------------------------------------

availability = (
    analysis_data
    .pivot_table(
        index=["IndicatorCode", "ShortName"],
        columns="Year",
        values="Value",
        aggfunc="first"
    )
    .reset_index()
)

print("\nDAY 3 KPI DATA AVAILABILITY")
print("=" * 55)

print(availability.to_string(index=False))


print("\nDay 3 setup completed successfully.")
print(f"\nTables will be saved to:\n{TABLES_DIR}")
print(f"\nFigures will be saved to:\n{FIGURES_DIR}")







# ============================================================
# RQ3 - EXPLORATORY RELATIONSHIP ANALYSIS
# ============================================================

print("\n")
print("=" * 70)
print("RQ3 - EXPLORATORY RELATIONSHIP ANALYSIS")
print("=" * 70)


# ------------------------------------------------------------
# 6. DEFINE RELATIONSHIPS
# ------------------------------------------------------------

RELATIONSHIPS = [
    {
        "name": "Investment vs Fixed Broadband",
        "x_code": "i81",
        "y_code": "i4213tfbbb",
        "x_label": "Telecommunications investment (ALL)",
        "y_label": "Fixed-broadband subscriptions",
        "status": "Primary"
    },
    {
        "name": "Revenue vs Fixed Broadband",
        "x_code": "i75",
        "y_code": "i4213tfbbb",
        "x_label": "Telecommunications revenue (ALL)",
        "y_label": "Fixed-broadband subscriptions",
        "status": "Primary"
    },
    {
        "name": "Fixed Data Traffic vs Fixed Broadband",
        "x_code": "i135tfb",
        "y_code": "i4213tfbbb",
        "x_label": "Fixed-broadband Internet traffic (EB)",
        "y_label": "Fixed-broadband subscriptions",
        "status": "Primary"
    },
    {
        "name": "FTTH/B vs 100+ Mbps Broadband",
        "x_code": "i4213ftth/b",
        "y_code": "i4213_G100",
        "x_label": "FTTH/B subscriptions",
        "y_label": "100+ Mbit/s broadband subscriptions",
        "status": "Supplementary"
    },
    {
        "name": "Mobile Voice vs Mobile Data Traffic",
        "x_code": "i133mm",
        "y_code": "i136mwi",
        "x_label": "Outgoing mobile voice traffic (minutes)",
        "y_label": "Mobile-broadband Internet traffic (EB)",
        "status": "Supplementary"
    }
]


# ------------------------------------------------------------
# 7. HELPER FUNCTION TO EXTRACT A KPI SERIES
# ------------------------------------------------------------

def get_kpi_series(code):
    """Return Year and Value for one indicator code."""

    df = master.loc[
        master["IndicatorCode"] == code,
        ["Year", "Value"]
    ].copy()

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

    return df.dropna(subset=["Year", "Value"])


# ------------------------------------------------------------
# 8. INTERPRET CORRELATION MAGNITUDE
# ------------------------------------------------------------

def correlation_strength(r):
    """Return a descriptive interpretation of Pearson r."""

    abs_r = abs(r)

    if abs_r < 0.20:
        strength = "Very weak"
    elif abs_r < 0.40:
        strength = "Weak"
    elif abs_r < 0.60:
        strength = "Moderate"
    elif abs_r < 0.80:
        strength = "Strong"
    else:
        strength = "Very strong"

    direction = "positive" if r > 0 else "negative"

    return f"{strength} {direction}"


# ------------------------------------------------------------
# 9. CALCULATE PEARSON CORRELATIONS
# ------------------------------------------------------------

correlation_results = []

for relationship in RELATIONSHIPS:

    x_df = get_kpi_series(relationship["x_code"]).rename(
        columns={"Value": "X"}
    )

    y_df = get_kpi_series(relationship["y_code"]).rename(
        columns={"Value": "Y"}
    )

    paired = pd.merge(
        x_df,
        y_df,
        on="Year",
        how="inner"
    ).dropna()

    n = len(paired)

    if n >= 3:

        r, p_value = pearsonr(paired["X"], paired["Y"])

        interpretation = correlation_strength(r)

        if n < 5:
            reliability_note = (
                "Very limited sample - descriptive only"
            )
        else:
            reliability_note = (
                "Exploratory - interpret cautiously"
            )

        correlation_results.append({
            "Relationship": relationship["name"],
            "Status": relationship["status"],
            "Period": (
                f"{int(paired['Year'].min())}-"
                f"{int(paired['Year'].max())}"
            ),
            "N": n,
            "Pearson_r": r,
            "P_value": p_value,
            "Interpretation": interpretation,
            "Reliability_Note": reliability_note
        })

        print(f"\n{relationship['name']}")
        print("-" * 60)
        print(
            f"Period: "
            f"{int(paired['Year'].min())}-"
            f"{int(paired['Year'].max())}"
        )
        print(f"N = {n}")
        print(f"Pearson r = {r:.4f}")
        print(f"p-value = {p_value:.4f}")
        print(f"Interpretation = {interpretation}")
        print(f"Note = {reliability_note}")

    else:

        print(f"\n{relationship['name']}")
        print("-" * 60)
        print("Insufficient paired observations.")


# ------------------------------------------------------------
# 10. CREATE CORRELATION RESULTS TABLE
# ------------------------------------------------------------

correlation_table = pd.DataFrame(correlation_results)

correlation_table["Pearson_r"] = (
    correlation_table["Pearson_r"].round(4)
)

correlation_table["P_value"] = (
    correlation_table["P_value"].round(4)
)

correlation_output_file = (
    TABLES_DIR / "RQ3_correlation_results.csv"
)

correlation_table.to_csv(
    correlation_output_file,
    index=False
)


print("\n")
print("=" * 70)
print("RQ3 CORRELATION SUMMARY")
print("=" * 70)

print(
    correlation_table.to_string(
        index=False
    )
)

print(
    f"\nCorrelation table saved to:\n"
    f"{correlation_output_file}"
)


# ------------------------------------------------------------
# 11. CREATE SCATTER PLOTS
# ------------------------------------------------------------

for i, relationship in enumerate(RELATIONSHIPS, start=1):

    x_df = get_kpi_series(relationship["x_code"]).rename(
        columns={"Value": "X"}
    )

    y_df = get_kpi_series(relationship["y_code"]).rename(
        columns={"Value": "Y"}
    )

    paired = pd.merge(
        x_df,
        y_df,
        on="Year",
        how="inner"
    ).dropna()

    if len(paired) < 3:
        continue

    r, _ = pearsonr(
        paired["X"],
        paired["Y"]
    )

    fig, ax = plt.subplots(figsize=(8, 5.5))

    ax.scatter(
        paired["X"],
        paired["Y"],
        s=70
    )

    # Add year labels beside observations
    for _, row in paired.iterrows():

        ax.annotate(
            str(int(row["Year"])),
            (row["X"], row["Y"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9
        )

    # Add simple fitted line for visual interpretation
    if len(paired) >= 3:

        coefficients = np.polyfit(
            paired["X"],
            paired["Y"],
            1
        )

        line_function = np.poly1d(coefficients)

        x_line = np.linspace(
            paired["X"].min(),
            paired["X"].max(),
            100
        )

        ax.plot(
            x_line,
            line_function(x_line),
            linewidth=1.5
        )

    ax.set_xlabel(
        relationship["x_label"]
    )

    ax.set_ylabel(
        relationship["y_label"]
    )

    ax.set_title(
        f"{relationship['name']}\n"
        f"Pearson r = {r:.3f}, "
        f"n = {len(paired)}"
    )

    ax.grid(
        alpha=0.25
    )

    fig.tight_layout()

    safe_name = (
        relationship["name"]
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("+", "plus")
    )

    figure_file = (
        FIGURES_DIR /
        f"RQ3_{i:02d}_{safe_name}.png"
    )

    fig.savefig(
        figure_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)


print(
    f"\nRQ3 scatter plots saved to:\n"
    f"{FIGURES_DIR}"
)


# ------------------------------------------------------------
# 12. RQ3 METHODOLOGICAL REMINDER
# ------------------------------------------------------------

print("\n")
print("=" * 70)
print("RQ3 INTERPRETATION REMINDER")
print("=" * 70)

print(
    "These correlations are exploratory and descriptive."
)

print(
    "Correlation does not establish causality."
)

print(
    "Results based on only three observations must be treated "
    "as highly tentative."
)

print("\nRQ3 analysis completed successfully.")





# ============================================================
# RQ4 - TREND-BASED PROJECTIONS
# ============================================================

print("\n")
print("=" * 70)
print("RQ4 - TREND-BASED PROJECTIONS")
print("=" * 70)


# ------------------------------------------------------------
# 13. DEFINE FORECAST KPIs
# ------------------------------------------------------------

FORECAST_KPIS = {
    "i4213tfbbb": {
        "name": "Fixed-broadband subscriptions",
        "unit": "subscriptions"
    },
    "i4213_G100": {
        "name": "100+ Mbit/s broadband subscriptions",
        "unit": "subscriptions"
    },
    "i135tfb": {
        "name": "Fixed-broadband Internet traffic",
        "unit": "EB"
    },
    "i75": {
        "name": "Telecommunications revenue",
        "unit": "ALL"
    },
    "i81": {
        "name": "Telecommunications investment",
        "unit": "ALL"
    }
}


FORECAST_YEARS = pd.DataFrame({
    "Year": [2025, 2026, 2027]
})


# ------------------------------------------------------------
# 14. FIT LINEAR TREND MODELS
# ------------------------------------------------------------

forecast_results = []
model_results = []

for code, info in FORECAST_KPIS.items():

    df = get_kpi_series(code).sort_values("Year")

    # Restrict estimation to the thesis study period
    df = df[
        (df["Year"] >= 2020) &
        (df["Year"] <= 2024)
    ].copy()

    X = df[["Year"]]
    y = df["Value"]

    model = LinearRegression()

    model.fit(X, y)

    fitted_values = model.predict(X)

    r_squared = r2_score(
        y,
        fitted_values
    )

    projections = model.predict(
        FORECAST_YEARS
    )

    slope = model.coef_[0]
    intercept = model.intercept_

    model_results.append({
        "IndicatorCode": code,
        "KPI": info["name"],
        "Unit": info["unit"],
        "N_Historical": len(df),
        "Slope_per_Year": slope,
        "Intercept": intercept,
        "R_squared": r_squared
    })

    print(f"\n{info['name']}")
    print("-" * 60)

    print(
        f"Historical observations = {len(df)}"
    )

    print(
        f"Annual linear trend = {slope:,.4f}"
    )

    print(
        f"R-squared = {r_squared:.4f}"
    )

    for year, projection in zip(
    FORECAST_YEARS["Year"],
    projections
):

        forecast_results.append({
            "IndicatorCode": code,
            "KPI": info["name"],
            "Unit": info["unit"],
            "Year": int(year),
            "Projected_Value": projection,
            "Method": "Linear trend"
        })

        print(
            f"{year} projection = "
            f"{projection:,.4f}"
        )


# ------------------------------------------------------------
# 15. SAVE MODEL DIAGNOSTICS
# ------------------------------------------------------------

model_table = pd.DataFrame(
    model_results
)

model_table["R_squared"] = (
    model_table["R_squared"].round(4)
)

model_output_file = (
    TABLES_DIR /
    "RQ4_linear_trend_model_diagnostics.csv"
)

model_table.to_csv(
    model_output_file,
    index=False
)


# ------------------------------------------------------------
# 16. SAVE PROJECTION TABLE
# ------------------------------------------------------------

forecast_table = pd.DataFrame(
    forecast_results
)

forecast_output_file = (
    TABLES_DIR /
    "RQ4_linear_trend_projections_2025_2027.csv"
)

forecast_table.to_csv(
    forecast_output_file,
    index=False
)


print("\n")
print("=" * 70)
print("RQ4 MODEL DIAGNOSTICS")
print("=" * 70)

print(
    model_table.to_string(
        index=False
    )
)


print("\n")
print("=" * 70)
print("RQ4 PROJECTIONS: 2025-2027")
print("=" * 70)

display_forecast = forecast_table.copy()

display_forecast["Projected_Value"] = (
    display_forecast["Projected_Value"].map(
        lambda x: f"{x:,.4f}"
    )
)

print(
    display_forecast.to_string(
        index=False
    )
)


# ------------------------------------------------------------
# 17. CREATE HISTORICAL + PROJECTED TREND FIGURES
# ------------------------------------------------------------

for code, info in FORECAST_KPIS.items():

    historical = (
        get_kpi_series(code)
        .sort_values("Year")
    )

    historical = historical[
        (historical["Year"] >= 2020) &
        (historical["Year"] <= 2024)
    ].copy()

    projection = forecast_table[
        forecast_table["IndicatorCode"] == code
    ].copy()

    model_info = model_table[
        model_table["IndicatorCode"] == code
    ].iloc[0]

    # Refit model for continuous trend line
    model = LinearRegression()

    model.fit(
        historical[["Year"]],
        historical["Value"]
    )

    all_years = pd.DataFrame({
    "Year": np.arange(2020, 2028)
})

    trend_line = model.predict(
    all_years
)

    fig, ax = plt.subplots(
        figsize=(9, 5.5)
    )

    # Historical observations
    ax.plot(
        historical["Year"],
        historical["Value"],
        marker="o",
        linewidth=2,
        label="Historical"
    )

    # Projected observations
    projection_years = np.concatenate(
        (
            np.array([2024]),
            projection["Year"].to_numpy()
        )
    )

    projection_values = np.concatenate(
        (
            np.array(
                [historical.loc[
                    historical["Year"] == 2024,
                    "Value"
                ].iloc[0]]
            ),
            projection["Projected_Value"].to_numpy()
        )
    )

    ax.plot(
        projection_years,
        projection_values,
        marker="o",
        linestyle="--",
        linewidth=2,
        label="Trend-based projection"
    )

    # Linear fitted trend
    ax.plot(
        all_years["Year"],
        trend_line,
        linestyle=":",
        linewidth=1.5,
        label="Linear trend"
    )

    ax.axvline(
        x=2024.5,
        linestyle="--",
        linewidth=1
    )

    ax.set_title(
        f"{info['name']}\n"
        f"Linear trend projection, "
        f"R-squared = {model_info['R_squared']:.3f}"
    )

    ax.set_xlabel(
        "Year"
    )

    ax.set_ylabel(
        info["unit"]
    )

    ax.set_xticks(
        range(2020, 2028)
    )

    ax.grid(
        alpha=0.25
    )

    ax.legend()

    fig.tight_layout()

    safe_name = (
        info["name"]
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("+", "plus")
    )

    figure_file = (
        FIGURES_DIR /
        f"RQ4_{safe_name}_projection.png"
    )

    fig.savefig(
        figure_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)


print(
    f"\nRQ4 projection figures saved to:\n"
    f"{FIGURES_DIR}"
)

print(
    f"\nModel diagnostics saved to:\n"
    f"{model_output_file}"
)

print(
    f"\nProjection table saved to:\n"
    f"{forecast_output_file}"
)


# ------------------------------------------------------------
# 18. RQ4 METHODOLOGICAL REMINDER
# ------------------------------------------------------------

print("\n")
print("=" * 70)
print("RQ4 INTERPRETATION REMINDER")
print("=" * 70)

print(
    "The 2025-2027 values are trend-based projections, "
    "not precise forecasts."
)

print(
    "Models are estimated from only five annual observations "
    "(2020-2024)."
)

print(
    "R-squared describes in-sample trend fit and should not "
    "be interpreted as evidence of out-of-sample forecast accuracy."
)

print(
    "Future structural, regulatory, technological, and economic "
    "changes are not incorporated into these simple trend models."
)

print("\nRQ4 linear trend analysis completed successfully.")







# ============================================================
# RQ4 - SIMPLE MODEL COMPARISON
# Linear Trend vs CAGR vs Exponential Trend
# ============================================================

print("\n")
print("=" * 70)
print("RQ4 - SIMPLE MODEL COMPARISON")
print("=" * 70)


comparison_results = []
alternative_projection_results = []


for code, info in FORECAST_KPIS.items():

    df = (
        get_kpi_series(code)
        .sort_values("Year")
    )

    df = df[
        (df["Year"] >= 2020) &
        (df["Year"] <= 2024)
    ].copy()

    years = df["Year"].to_numpy()
    values = df["Value"].to_numpy()

    n = len(df)

    print(f"\n{info['name']}")
    print("-" * 60)

    # --------------------------------------------------------
    # CAGR
    # --------------------------------------------------------

    first_value = values[0]
    last_value = values[-1]

    number_of_periods = years[-1] - years[0]

    if (
        first_value > 0 and
        last_value > 0 and
        number_of_periods > 0
    ):

        cagr = (
            (last_value / first_value) **
            (1 / number_of_periods)
        ) - 1

        cagr_2025 = last_value * (1 + cagr)
        cagr_2026 = last_value * (1 + cagr) ** 2
        cagr_2027 = last_value * (1 + cagr) ** 3

    else:

        cagr = np.nan
        cagr_2025 = np.nan
        cagr_2026 = np.nan
        cagr_2027 = np.nan


    # --------------------------------------------------------
    # EXPONENTIAL TREND
    # ln(Y) = alpha + beta * t
    # --------------------------------------------------------

    if np.all(values > 0):

        t = np.arange(n).reshape(-1, 1)

        log_values = np.log(values)

        exp_model = LinearRegression()

        exp_model.fit(
            t,
            log_values
        )

        fitted_log = exp_model.predict(t)

        fitted_exp = np.exp(fitted_log)

        # R-squared calculated on original scale
        exp_r_squared = r2_score(
            values,
            fitted_exp
        )

        future_t = np.arange(
            n,
            n + 3
        ).reshape(-1, 1)

        exp_projections = np.exp(
            exp_model.predict(future_t)
        )

    else:

        exp_r_squared = np.nan

        exp_projections = np.array(
            [np.nan, np.nan, np.nan]
        )


    # --------------------------------------------------------
    # RETRIEVE LINEAR MODEL RESULTS
    # --------------------------------------------------------

    linear_info = model_table[
        model_table["IndicatorCode"] == code
    ].iloc[0]

    linear_r_squared = (
        linear_info["R_squared"]
    )


    # --------------------------------------------------------
    # STORE MODEL COMPARISON
    # --------------------------------------------------------

    comparison_results.append({
        "IndicatorCode": code,
        "KPI": info["name"],
        "N": n,
        "Linear_R_squared": linear_r_squared,
        "Exponential_R_squared": exp_r_squared,
        "CAGR": cagr
    })


    # --------------------------------------------------------
    # STORE ALTERNATIVE PROJECTIONS
    # --------------------------------------------------------

    for i, year in enumerate(
        [2025, 2026, 2027]
    ):

        alternative_projection_results.append({
            "IndicatorCode": code,
            "KPI": info["name"],
            "Year": year,
            "CAGR_Projection": [
                cagr_2025,
                cagr_2026,
                cagr_2027
            ][i],
            "Exponential_Projection":
                exp_projections[i]
        })


    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    print(
        f"Linear R-squared      = "
        f"{linear_r_squared:.4f}"
    )

    print(
        f"Exponential R-squared = "
        f"{exp_r_squared:.4f}"
    )

    print(
        f"CAGR 2020-2024        = "
        f"{cagr * 100:.2f}%"
    )

    print("\nAlternative projections:")

    print(
        f"2025 CAGR = {cagr_2025:,.4f} | "
        f"Exponential = {exp_projections[0]:,.4f}"
    )

    print(
        f"2026 CAGR = {cagr_2026:,.4f} | "
        f"Exponential = {exp_projections[1]:,.4f}"
    )

    print(
        f"2027 CAGR = {cagr_2027:,.4f} | "
        f"Exponential = {exp_projections[2]:,.4f}"
    )


# ------------------------------------------------------------
# CREATE MODEL COMPARISON TABLE
# ------------------------------------------------------------

comparison_table = pd.DataFrame(
    comparison_results
)

comparison_table["Linear_R_squared"] = (
    comparison_table["Linear_R_squared"]
    .round(4)
)

comparison_table["Exponential_R_squared"] = (
    comparison_table["Exponential_R_squared"]
    .round(4)
)

comparison_table["CAGR_percent"] = (
    comparison_table["CAGR"] * 100
).round(2)

comparison_table = comparison_table.drop(
    columns=["CAGR"]
)


comparison_output_file = (
    TABLES_DIR /
    "RQ4_model_comparison.csv"
)

comparison_table.to_csv(
    comparison_output_file,
    index=False
)


# ------------------------------------------------------------
# CREATE ALTERNATIVE PROJECTION TABLE
# ------------------------------------------------------------

alternative_projection_table = pd.DataFrame(
    alternative_projection_results
)

alternative_output_file = (
    TABLES_DIR /
    "RQ4_alternative_projections.csv"
)

alternative_projection_table.to_csv(
    alternative_output_file,
    index=False
)


# ------------------------------------------------------------
# PRINT FINAL COMPARISON
# ------------------------------------------------------------

print("\n")
print("=" * 70)
print("RQ4 MODEL COMPARISON SUMMARY")
print("=" * 70)

print(
    comparison_table.to_string(
        index=False
    )
)

print(
    f"\nModel comparison saved to:\n"
    f"{comparison_output_file}"
)

print(
    f"\nAlternative projections saved to:\n"
    f"{alternative_output_file}"
)

print("\nRQ4 model comparison completed successfully.")







# ============================================================
# RQ4 - FINAL THESIS PROJECTIONS
# ============================================================

print("\n")
print("=" * 70)
print("RQ4 - FINAL THESIS PROJECTIONS")
print("=" * 70)


# ------------------------------------------------------------
# 19. FINAL MODEL SELECTION
# ------------------------------------------------------------

FINAL_FORECAST_CODES = [
    "i4213tfbbb",
    "i4213_G100",
    "i135tfb",
    "i75"
]


final_forecast_table = forecast_table[
    forecast_table["IndicatorCode"].isin(
        FINAL_FORECAST_CODES
    )
].copy()


# ------------------------------------------------------------
# 20. ADD MODEL FIT
# ------------------------------------------------------------

final_forecast_table = final_forecast_table.merge(
    model_table[
        [
            "IndicatorCode",
            "R_squared"
        ]
    ],
    on="IndicatorCode",
    how="left"
)


# ------------------------------------------------------------
# 21. ROUND VALUES FOR THESIS PRESENTATION
# ------------------------------------------------------------

def thesis_round(row):

    if row["Unit"] == "subscriptions":
        return round(row["Projected_Value"])

    elif row["Unit"] == "EB":
        return round(row["Projected_Value"], 3)

    elif row["Unit"] == "ALL":
        return round(row["Projected_Value"])

    return row["Projected_Value"]


final_forecast_table[
    "Projected_Value_Thesis"
] = final_forecast_table.apply(
    thesis_round,
    axis=1
)


# ------------------------------------------------------------
# 22. SAVE FINAL THESIS TABLE
# ------------------------------------------------------------

final_output_file = (
    TABLES_DIR /
    "RQ4_FINAL_thesis_projections_2025_2027.csv"
)

final_forecast_table.to_csv(
    final_output_file,
    index=False
)


# ------------------------------------------------------------
# 23. CREATE WIDE PRESENTATION TABLE
# ------------------------------------------------------------

final_wide_table = (
    final_forecast_table
    .pivot(
        index=[
            "KPI",
            "Unit",
            "R_squared"
        ],
        columns="Year",
        values="Projected_Value_Thesis"
    )
    .reset_index()
)


final_wide_output_file = (
    TABLES_DIR /
    "RQ4_FINAL_thesis_table_wide.csv"
)

final_wide_table.to_csv(
    final_wide_output_file,
    index=False
)


print("\nFINAL PROJECTION TABLE")
print("-" * 70)

print(
    final_wide_table.to_string(
        index=False
    )
)


print(
    f"\nFinal projection data saved to:\n"
    f"{final_output_file}"
)

print(
    f"\nFinal thesis-ready wide table saved to:\n"
    f"{final_wide_output_file}"
)


print("\nInvestment forecasting decision:")
print(
    "Telecommunications investment is excluded from the final "
    "numerical projections because its 2020-2024 trajectory is "
    "non-monotonic and simple models produce materially different "
    "future values."
)


print("\nFINAL RQ4 analysis completed successfully.")