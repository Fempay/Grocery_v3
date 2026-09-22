# Simple NRI Grocery Forecast Streamlit App

Files:
- app.py
- kirana_sales.csv
- kirana_forecast_fy2027.csv
- requirements.txt

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
streamlit run app.py
```

## What this version does

- Shows historical sales charts
- Shows FY2027 forecasts
- Provides 95% forecast intervals
- Predict button for product + month
- Explains WHY a demand value is predicted using:
  - historical seasonality
  - recent 6-month demand trend
  - festival / monsoon / school-reopening patterns
  - promotion sensitivity
  - comparison with the product's historical baseline

This remains a lightweight app: it does not retrain LightGBM during every Streamlit refresh.
