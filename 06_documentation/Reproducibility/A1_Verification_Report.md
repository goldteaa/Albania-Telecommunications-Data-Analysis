# A1 — Computational Reproducibility Verification

Verification date: 2026-11-07

## Environment
Python: 3.13.0
Environment: .venv
Dependencies: requirements.txt

## Execution
- Six operator-analysis scripts executed successfully.
- National relationships and forecasting script executed successfully.
- National EDA notebook executed successfully.
- Original inputs and historical outputs preserved.
- Regenerated outputs stored separately under:
  04_outputs/Reproduced_Results/

## Verification results
- Operator Excel workbooks: 6 numerically reproduced.
- Operator PNG figures: 8 pixel-identical.
- National descriptive Excel workbooks: 6 matched.
- National EDA PNG figures: 13 pixel-identical.
- National forecasting CSV files: 7 matched.
- National forecasting PNG figures: 10 pixel-identical.

Total: 50 historical output files verified.

## Qualifications
1. The historical subscriber workbook contains a duplicated
   table and blank rows. Corresponding numerical values match.
2. The 2022 fixed-revenue reconciliation discrepancy of
   36.03 million ALL exists in both historical and reproduced
   validation results.
3. Correlations are exploratory, with small sample sizes.
4. Forecasts are trend-based projections, not validated
   out-of-sample predictions.
5. Reproducibility of computational outputs does not independently
   establish the accuracy of the underlying source data.

## Conclusion
The computational workflow successfully reproduces the
historical analytical outputs under the documented environment,
subject to the qualifications above.
