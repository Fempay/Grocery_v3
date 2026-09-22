
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="NRI Grocery Demand Forecast",
    page_icon="🛒",
    layout="wide"
)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
@st.cache_data
def load_data():
    sales = pd.read_csv("kirana_sales.csv")
    forecast = pd.read_csv("kirana_forecast_fy2027.csv")

    sales["month"] = pd.to_datetime(sales["month"])
    forecast["month"] = pd.to_datetime(forecast["month"])

    return sales, forecast


sales, forecast = load_data()


# --------------------------------------------------
# SIMPLE EXPLANATION FUNCTION
# --------------------------------------------------
def explain_prediction(product, target_month, predicted_units, lower=None, upper=None):
    """
    Creates a simple, data-based explanation for a forecast.

    IMPORTANT:
    These are historical signals used to explain the prediction in an
    understandable way. They are not SHAP/feature-contribution values.
    """

    product_data = sales[sales["product_series"] == product].copy()
    product_data = product_data.sort_values("month")

    target_month = pd.to_datetime(target_month)
    calendar_month = target_month.month
    month_name = target_month.strftime("%B")

    reasons = []

    # 1. SEASONALITY
    overall_avg = product_data["units_sold"].mean()

    same_month_data = product_data[
        product_data["month"].dt.month == calendar_month
    ]

    if len(same_month_data) > 0:
        same_month_avg = same_month_data["units_sold"].mean()
        seasonal_change = ((same_month_avg / overall_avg) - 1) * 100

        if seasonal_change >= 5:
            reasons.append(
                f"📅 **Seasonality:** Historically, {month_name} demand for "
                f"{product} is about **{seasonal_change:.1f}% above** its normal monthly average."
            )
        elif seasonal_change <= -5:
            reasons.append(
                f"📅 **Seasonality:** Historically, {month_name} demand for "
                f"{product} is about **{abs(seasonal_change):.1f}% below** its normal monthly average."
            )
        else:
            reasons.append(
                f"📅 **Seasonality:** {month_name} has historically been close to the "
                f"normal demand level for {product}."
            )

    # 2. RECENT TREND
    if len(product_data) >= 12:
        recent_6 = product_data.tail(6)["units_sold"].mean()
        previous_6 = product_data.iloc[-12:-6]["units_sold"].mean()

        if previous_6 > 0:
            trend_change = ((recent_6 / previous_6) - 1) * 100

            if trend_change >= 5:
                reasons.append(
                    f"📈 **Recent trend:** Average demand in the latest 6 months is "
                    f"**{trend_change:.1f}% higher** than the previous 6 months."
                )
            elif trend_change <= -5:
                reasons.append(
                    f"📉 **Recent trend:** Average demand in the latest 6 months is "
                    f"**{abs(trend_change):.1f}% lower** than the previous 6 months."
                )
            else:
                reasons.append(
                    "➡️ **Recent trend:** Demand has been relatively stable over the latest 12 months."
                )

    # 3. FESTIVAL / MONSOON / SCHOOL PATTERN FOR THIS CALENDAR MONTH
    flag_details = [
        ("festival_flag", "🎉", "festival"),
        ("monsoon_flag", "🌧️", "monsoon"),
        ("school_reopening_flag", "🏫", "school-reopening"),
    ]

    for column, icon, label in flag_details:
        if column in product_data.columns and len(same_month_data) > 0:
            month_flag_rate = same_month_data[column].mean()

            # Mention only when this calendar month was commonly associated with the event
            if month_flag_rate >= 0.5:
                event_rows = product_data[product_data[column] == 1]
                normal_rows = product_data[product_data[column] == 0]

                if len(event_rows) > 0 and len(normal_rows) > 0:
                    event_avg = event_rows["units_sold"].mean()
                    normal_avg = normal_rows["units_sold"].mean()

                    if normal_avg > 0:
                        event_change = ((event_avg / normal_avg) - 1) * 100

                        direction = "higher" if event_change >= 0 else "lower"

                        reasons.append(
                            f"{icon} **{label.title()} pattern:** {month_name} has frequently "
                            f"been a {label} month in the historical data. During such months, "
                            f"{product} demand was on average **{abs(event_change):.1f}% {direction}**."
                        )
                        break

    # 4. PROMOTION EFFECT
    if "promo_flag" in product_data.columns:
        promo = product_data[product_data["promo_flag"] == 1]["units_sold"]
        no_promo = product_data[product_data["promo_flag"] == 0]["units_sold"]

        if len(promo) > 0 and len(no_promo) > 0 and no_promo.mean() > 0:
            promo_change = ((promo.mean() / no_promo.mean()) - 1) * 100

            if abs(promo_change) >= 5:
                direction = "higher" if promo_change > 0 else "lower"
                reasons.append(
                    f"🏷️ **Promotion sensitivity:** Historically, promotional months for "
                    f"{product} recorded about **{abs(promo_change):.1f}% {direction} demand** "
                    f"than non-promotional months."
                )

    # 5. FORECAST LEVEL VS HISTORICAL NORMAL
    if overall_avg > 0:
        forecast_vs_avg = ((predicted_units / overall_avg) - 1) * 100

        if forecast_vs_avg >= 5:
            reasons.append(
                f"🔮 **Forecast level:** The predicted value is **{forecast_vs_avg:.1f}% above** "
                f"the historical monthly average of about **{overall_avg:,.0f} units**."
            )
        elif forecast_vs_avg <= -5:
            reasons.append(
                f"🔮 **Forecast level:** The predicted value is **{abs(forecast_vs_avg):.1f}% below** "
                f"the historical monthly average of about **{overall_avg:,.0f} units**."
            )
        else:
            reasons.append(
                f"🔮 **Forecast level:** The prediction is close to the historical monthly "
                f"average of about **{overall_avg:,.0f} units**."
            )

    # 6. UNCERTAINTY
    if lower is not None and upper is not None and predicted_units > 0:
        uncertainty = ((upper - lower) / predicted_units) * 100

        reasons.append(
            f"📊 **Uncertainty:** The model's 95% forecast range is "
            f"**{int(lower):,}–{int(upper):,} units**, showing the reasonable range around the estimate."
        )

    # Keep explanation short
    return reasons[:5]


def show_reasons(product, target_month, predicted_units, lower=None, upper=None):
    reasons = explain_prediction(
        product,
        target_month,
        predicted_units,
        lower,
        upper
    )

    st.markdown("### 💡 Why is this demand predicted?")

    for reason in reasons:
        st.markdown(f"- {reason}")

    st.caption(
        "These explanations summarize patterns found in the historical sales data. "
        "They are intended to make the forecast easier to interpret."
    )


# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.title("🛒 NRI Complex Grocery Demand Forecast")
st.caption("Historical sales dashboard + FY2027 demand forecast")


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("Filters")

products = sorted(sales["product_series"].unique())

selected_product = st.sidebar.selectbox(
    "Select product",
    products
)

show_all = st.sidebar.checkbox(
    "Show all products",
    value=False
)

sales_product = sales[
    sales["product_series"] == selected_product
].copy()

forecast_product = forecast[
    forecast["product_series"] == selected_product
].copy()


# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------
latest_sales = int(
    sales_product.sort_values("month")["units_sold"].iloc[-1]
)

avg_sales = int(
    sales_product["units_sold"].mean()
)

forecast_total = int(
    forecast_product["forecast_units"].sum()
)

forecast_avg = int(
    forecast_product["forecast_units"].mean()
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Latest Monthly Sales", f"{latest_sales:,}")
c2.metric("Historical Avg.", f"{avg_sales:,}")
c3.metric("FY2027 Forecast", f"{forecast_total:,}")
c4.metric("Avg. Forecast / Month", f"{forecast_avg:,}")

st.divider()


# --------------------------------------------------
# TABS
# --------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📈 Historical Sales",
        "🔮 Forecast",
        "🎯 Predict",
        "📊 Product Comparison"
    ]
)


# ==================================================
# TAB 1 — HISTORICAL SALES
# ==================================================
with tab1:

    st.subheader(
        f"Historical Sales — {selected_product}"
    )

    fig = px.line(
        sales_product,
        x="month",
        y="units_sold",
        markers=True,
        title=f"Monthly Units Sold: {selected_product}"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    col1, col2 = st.columns(2)

    with col1:

        monthly_avg = (
            sales_product
            .assign(
                month_name=sales_product["month"].dt.strftime("%b")
            )
            .groupby(
                "month_name",
                as_index=False
            )["units_sold"]
            .mean()
        )

        month_order = [
            "Jan", "Feb", "Mar", "Apr",
            "May", "Jun", "Jul", "Aug",
            "Sep", "Oct", "Nov", "Dec"
        ]

        monthly_avg["month_name"] = pd.Categorical(
            monthly_avg["month_name"],
            categories=month_order,
            ordered=True
        )

        monthly_avg = monthly_avg.sort_values(
            "month_name"
        )

        fig2 = px.bar(
            monthly_avg,
            x="month_name",
            y="units_sold",
            title="Average Demand by Month"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

    with col2:

        fig3 = px.scatter(
            sales_product,
            x="avg_price_inr",
            y="units_sold",
            color="promo_flag",
            title="Price vs Demand"
        )

        st.plotly_chart(
            fig3,
            use_container_width=True
        )


# ==================================================
# TAB 2 — FORECAST
# ==================================================
with tab2:

    st.subheader(
        f"FY2027 Forecast — {selected_product}"
    )

    fig4 = px.line(
        forecast_product,
        x="month",
        y="forecast_units",
        markers=True,
        title=f"Forecast Demand: {selected_product}"
    )

    fig4.add_scatter(
        x=forecast_product["month"],
        y=forecast_product["upper_95"],
        mode="lines",
        name="Upper 95%",
        line=dict(dash="dot")
    )

    fig4.add_scatter(
        x=forecast_product["month"],
        y=forecast_product["lower_95"],
        mode="lines",
        name="Lower 95%",
        line=dict(dash="dot")
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

    # ------------------------------
    # EXPLAIN ONE FORECAST MONTH
    # ------------------------------
    st.markdown("### 🔍 Explain a forecast month")

    forecast_product = forecast_product.sort_values("month").copy()
    forecast_product["month_label"] = (
        forecast_product["month"].dt.strftime("%B %Y")
    )

    explain_month = st.selectbox(
        "Select month to explain",
        forecast_product["month_label"].tolist(),
        key="forecast_explain_month"
    )

    explain_row = forecast_product[
        forecast_product["month_label"] == explain_month
    ].iloc[0]

    x1, x2, x3 = st.columns(3)

    x1.metric(
        "Forecast",
        f"{int(explain_row['forecast_units']):,} units"
    )

    x2.metric(
        "Lower 95%",
        f"{int(explain_row['lower_95']):,}"
    )

    x3.metric(
        "Upper 95%",
        f"{int(explain_row['upper_95']):,}"
    )

    show_reasons(
        selected_product,
        explain_row["month"],
        explain_row["forecast_units"],
        explain_row["lower_95"],
        explain_row["upper_95"]
    )

    st.divider()

    st.dataframe(
        forecast_product[
            [
                "month",
                "forecast_units",
                "lower_95",
                "upper_95"
            ]
        ].rename(
            columns={
                "month": "Month",
                "forecast_units": "Forecast Units",
                "lower_95": "Lower 95%",
                "upper_95": "Upper 95%"
            }
        ),
        use_container_width=True,
        hide_index=True
    )

    csv = forecast_product.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "⬇️ Download Forecast",
        data=csv,
        file_name=f"{selected_product}_forecast.csv",
        mime="text/csv"
    )


# ==================================================
# TAB 3 — PREDICT
# ==================================================
with tab3:

    st.subheader("🎯 Demand Prediction")

    st.write(
        "Choose a product and forecast month. "
        "The app returns the forecast and explains the historical "
        "patterns behind that prediction."
    )

    predict_product = st.selectbox(
        "Product",
        sorted(
            forecast["product_series"].unique()
        ),
        key="predict_product"
    )

    product_rows = forecast[
        forecast["product_series"] == predict_product
    ].copy()

    product_rows = product_rows.sort_values(
        "month"
    )

    product_rows["month_label"] = (
        product_rows["month"].dt.strftime("%B %Y")
    )

    predict_month = st.selectbox(
        "Forecast month",
        product_rows["month_label"].tolist()
    )

    if st.button(
        "🚀 Predict Demand",
        type="primary"
    ):

        result = product_rows[
            product_rows["month_label"] == predict_month
        ].iloc[0]

        st.success(
            f"Predicted demand for **{predict_product}** "
            f"in **{predict_month}** is "
            f"**{int(result['forecast_units']):,} units**."
        )

        a, b, c = st.columns(3)

        a.metric(
            "Prediction",
            f"{int(result['forecast_units']):,}"
        )

        b.metric(
            "Lower 95%",
            f"{int(result['lower_95']):,}"
        )

        c.metric(
            "Upper 95%",
            f"{int(result['upper_95']):,}"
        )

        show_reasons(
            predict_product,
            result["month"],
            result["forecast_units"],
            result["lower_95"],
            result["upper_95"]
        )


# ==================================================
# TAB 4 — PRODUCT COMPARISON
# ==================================================
with tab4:

    st.subheader(
        "Product Comparison"
    )

    total_forecast = (
        forecast
        .groupby(
            "product_series",
            as_index=False
        )["forecast_units"]
        .sum()
        .sort_values(
            "forecast_units",
            ascending=False
        )
    )

    fig5 = px.bar(
        total_forecast,
        x="product_series",
        y="forecast_units",
        title="Total FY2027 Forecast by Product"
    )

    st.plotly_chart(
        fig5,
        use_container_width=True
    )

    if show_all:

        all_monthly = (
            forecast
            .groupby(
                ["month", "product_series"],
                as_index=False
            )["forecast_units"]
            .sum()
        )

        fig6 = px.line(
            all_monthly,
            x="month",
            y="forecast_units",
            color="product_series",
            title="FY2027 Forecast — All Products"
        )

        st.plotly_chart(
            fig6,
            use_container_width=True
        )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.divider()

st.caption(
    "Fast version: uses the pre-generated FY2027 forecast "
    "instead of retraining LightGBM every time Streamlit refreshes."
)
