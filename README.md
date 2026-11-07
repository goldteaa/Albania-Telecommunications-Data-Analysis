# Albania Telecommunications Sector: Data Analysis and Forecasting (2020–2024)

## Overview

This repository contains the datasets, Python scripts, analytical outputs, and supporting documentation for the MSc thesis:

**A Data-Driven Analysis of the Albanian Telecommunications Sector: Trends, Performance, and Forecasting Using National ICT Indicators (2020–2024)**

The research examines telecommunications development in Albania using national ICT indicators and operator-level regulatory statistics.

## Research Objectives

The analysis focuses on four areas:

1. Historical development of Albania's principal telecommunications indicators during 2020–2024.
2. Infrastructure development, service adoption, operator performance, and market concentration.
3. Statistical relationships between telecommunications investment, revenue, subscriptions, and data traffic.
4. Short-term trend-based projections for selected indicators during 2025–2027.

## Data Sources

The research uses national ICT datasets and published telecommunications statistics, including data from:

- Albania's Ministry of Infrastructure and Energy
- Electronic and Postal Communications Authority (AKEP)
- International Telecommunication Union (ITU) indicator definitions and methodological guidance

The prepared analytical datasets are provided in the `02_data` directory.

## Analytical Methods

The research uses Python for:

- Data preparation, validation, and descriptive analysis
- Year-on-year growth and compound annual growth rates (CAGR)
- Operator-level revenue and subscription comparisons
- Market concentration analysis using HHI and CR2
- Exploratory Pearson correlation analysis
- Linear and exponential trend modelling
- Short-term projections for 2025–2027

## Repository Structure

```text
01_sources/         Source reports and reference documents
02_data/            Prepared national ICT and operator datasets
03_scripts/         Python scripts and Jupyter notebooks
04_outputs/         Analytical tables and figures
05_thesis/          Thesis document
06_documentation/   Methodological and reproducibility documentation
requirements.txt    Python dependencies
README.md           Project overview
```

## Reproducibility

The analysis was conducted using Python and the dependencies listed in `requirements.txt`.

To prepare a Python environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

The scripts are organized into national ICT analysis and operator-level analysis workflows. Their input and output paths are relative to the project directory.

Refer to the documentation in `06_documentation` for the analytical workflow, data validation information, and supporting reproducibility records.

## Interpretation and Limitations

The national analysis covers five annual observations, with shorter series for some indicators.

Pearson correlations are exploratory and should not be interpreted as causal relationships. The 2025–2027 projections represent conditional historical trend extrapolations, not independently validated forecasts.

Operator consolidation, reporting differences, missing observations, and aggregated operator categories affect some comparisons and concentration measures.

## Academic Context

**Programme:** MSc in Data Science and Business Analytics  
**Institution:** University of New York Tirana  
**Research period:** 2020–2024  
**Forecast horizon:** 2025–2027

## Data and Reuse

The repository includes research materials derived from official statistical publications. The inclusion of third-party source documents does not imply ownership or unrestricted redistribution rights.

Reuse of source materials remains subject to the original publishers' terms.
