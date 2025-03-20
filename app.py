import streamlit as st
import os
os.environ["OPENAI_API_KEY"] = st.secrets["openai"]["api_key"]
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import geopandas as gpd
import json
import pydeck as pdk
import folium
from streamlit_folium import st_folium
from openai import OpenAI
from agent import run_agent

client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Burkina Faso Rainfall", layout="wide", initial_sidebar_state="expanded")

if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Introduction"

# --- SIDEBAR MENU ---
st.sidebar.title("📊 Navigation Menu")

pages = ["Introduction","Rainfall Analysis", "Seasonal Analysis", "Geographical Distribution", "Land Use", "Raw Data", "Credits"]
page = st.sidebar.radio("Select an analysis:", pages, index=pages.index(st.session_state["selected_page"]))

st.sidebar.title("📱 WebApp settings")
use_same_slider = st.sidebar.checkbox("Use the same slider for all analyses", value=True)

# --- DATA LOADING AND PREPARATION ---
@st.cache_data
def load_data():
    df = pd.read_csv("bfa-rainfall-adm2-full.csv", parse_dates=["date"], low_memory=False)
    df = df.iloc[1:]  # Remove the first row if not needed
    df["date"] = pd.to_datetime(df["date"], errors="coerce")  # Convert the 'date' column to datetime
    df["rfh"] = pd.to_numeric(df["rfh"], errors="coerce")  # Convert rainfall values to numeric
    return df

df = load_data()

# --- HANDLE SLIDERS ACROSS PAGES ---
if use_same_slider:
    min_date = df["date"].min()
    max_date = df["date"].max()
    start_date, end_date = st.sidebar.slider(
        "Select the analysis period:",
        min_value=min_date.date(),
        max_value=max_date.date(),
        value=(pd.to_datetime("2010-01-01").date(), pd.to_datetime("2020-12-31").date()),
        format="YYYY-MM-DD"
    )

# --- RAINFALL ANALYSIS ---
if page == "Introduction":
    st.title("Sahel Region")

    st.image("7.jpeg", caption="Displayed Image")

    st.write("""
### Project Overview

The **Sahel Region Analysis** project aims to provide data-driven insights into climate trends, land use changes, and population dynamics in Burkina Faso. By leveraging historical climate data, geospatial mapping, and machine learning techniques, this analysis serves as a decision-making tool for policymakers and stakeholders.

### Objectives:
1. **Climate Risk Assessment:** Identify rainfall patterns, seasonal variations, and extreme weather events that impact water resources, agriculture, and infrastructure.
2. **Land Use Monitoring:** Analyze how agricultural expansion, deforestation, and arable land dynamics correlate with changing environmental conditions.
3. **Urbanization Trends:** Understand the relationship between Gross Primary Productivity (GPP) and urban population growth to guide sustainable development policies.
4. **Policy Support:** Provide evidence-based recommendations to mitigate climate risks, optimize land management, and promote resilience in urban and rural areas.

### Importance for Policymakers:
- **Resilience Planning:** Data-driven insights help design climate adaptation strategies for food security, water resource management, and disaster preparedness.
- **Sustainable Development:** Understanding land use shifts enables more effective rural development policies and conservation efforts.
- **Infrastructure Investment:** By identifying regions at risk of extreme weather, governments can prioritize infrastructure projects to enhance resilience.

This analysis is intended to support policymakers in making informed decisions that enhance economic stability, environmental sustainability, and social resilience in the Sahel region.

## Undestanding the past is the key to predict the future


""")

    col1, col2 , col3= st.columns([1, 2, 1])

    with col1:
        if st.button("← Previous page"):
            next_page_index = (pages.index(page) - 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()
    with col2:
        st.write("")

    with col3:
        if st.button("Next page →"):
            next_page_index = (pages.index(page) + 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()


elif page == "Rainfall Analysis":
    st.title("📊 Rainfall Analysis in Burkina Faso")

    if not use_same_slider:
        min_date = df["date"].min()
        max_date = df["date"].max()
        start_date, end_date = st.slider(
            "Select the analysis period:",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(pd.to_datetime("2021-06-01").date(), pd.to_datetime("2022-06-01").date()),
            format="YYYY-MM-DD"
        )

    df_filtered = df[
        (df["date"] >= pd.to_datetime(start_date, format="%Y-%m-%d")) &
        (df["date"] <= pd.to_datetime(end_date, format="%Y-%m-%d"))
    ]

    # Aggregate data: daily rainfall sum
    df_daily_sum = df_filtered.groupby("date")["rfh"].sum().reset_index()
    df_daily_sum = df_daily_sum.sort_values(by="date").reset_index(drop=True)

    # --- PLOT ---
    fig, ax = plt.subplots(figsize=(12, 6))
    # Main line showing daily rainfall
    ax.plot(df_daily_sum["date"], df_daily_sum["rfh"], marker='o', linestyle='-', color='b', linewidth=2, markersize=6, label='Rainfall')

    # Highlight minimum and maximum values if data exists
    if not df_daily_sum.empty:
        min_value = df_daily_sum["rfh"].min()
        max_value = df_daily_sum["rfh"].max()
        min_date_point = df_daily_sum.loc[df_daily_sum["rfh"].idxmin(), "date"]
        max_date_point = df_daily_sum.loc[df_daily_sum["rfh"].idxmax(), "date"]

        ax.scatter(min_date_point, min_value, color='red', s=100, label="Min Rainfall")
        ax.scatter(max_date_point, max_value, color='green', s=100, label="Max Rainfall")
        ax.text(min_date_point, min_value, f"Min: {min_value:.2f} mm", fontsize=10, verticalalignment='bottom', horizontalalignment='right', color='red', fontweight='bold')
        ax.text(max_date_point, max_value, f"Max: {max_value:.2f} mm", fontsize=10, verticalalignment='top', horizontalalignment='left', color='green', fontweight='bold')

        # --- REGRESSION LINES FOR EXTREME RAINFALL ---
    # Define thresholds for high and low rainfall using quantiles
    high_threshold = df_daily_sum["rfh"].quantile(0.9)
    low_threshold = df_daily_sum["rfh"].quantile(0.1)

    # Filter the data for high rainfall (extreme high) and low rainfall (extreme low)
    df_high = df_daily_sum[df_daily_sum["rfh"] >= high_threshold]
    df_low = df_daily_sum[df_daily_sum["rfh"] <= low_threshold]

    # Regression for high rainfall days
    if not df_high.empty and len(df_high) >= 2:
        x_high = df_high["date"].map(lambda d: d.toordinal())
        y_high = df_high["rfh"]
        coeffs_high = np.polyfit(x_high, y_high, 1)
        poly_high = np.poly1d(coeffs_high)
        x_vals_high = np.linspace(x_high.min(), x_high.max(), 100)
        x_dates_high = [pd.Timestamp.fromordinal(int(x)) for x in x_vals_high]
        y_vals_high = poly_high(x_vals_high)
        ax.plot(x_dates_high, y_vals_high, color="darkgreen", linestyle="--", linewidth=2, label="Regression (High Rainfall)")

    # Regression for low rainfall days
    if not df_low.empty and len(df_low) >= 2:
        x_low = df_low["date"].map(lambda d: d.toordinal())
        y_low = df_low["rfh"]
        coeffs_low = np.polyfit(x_low, y_low, 1)
        poly_low = np.poly1d(coeffs_low)
        x_vals_low = np.linspace(x_low.min(), x_low.max(), 100)
        x_dates_low = [pd.Timestamp.fromordinal(int(x)) for x in x_vals_low]
        y_vals_low = poly_low(x_vals_low)
        ax.plot(x_dates_low, y_vals_low, color="darkred", linestyle="--", linewidth=2, label="Regression (Low Rainfall)")

    # --- DYNAMIC X-AXIS LABELS MANAGEMENT ---
    date_range_days = (end_date - start_date).days  # Number of days selected
    if date_range_days > 14600:  # > 40 years → every 10 years
        locator = mdates.YearLocator(10)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 7300:  # > 20 years → every 5 years
        locator = mdates.YearLocator(5)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 3650:  # > 10 years → every 2 years
        locator = mdates.YearLocator(2)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 1825:  # > 5 years → every year
        locator = mdates.YearLocator(1)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 730:  # > 2 years → every 6 months
        locator = mdates.MonthLocator(interval=6)
        formatter = mdates.DateFormatter("%Y-%m")
    elif date_range_days > 365:  # > 1 year → every 3 months
        locator = mdates.MonthLocator(interval=3)
        formatter = mdates.DateFormatter("%Y-%m")
    elif date_range_days > 180:  # > 6 months → every month
        locator = mdates.MonthLocator(interval=1)
        formatter = mdates.DateFormatter("%Y-%m")
    elif date_range_days > 90:  # > 3 months → every 15 days
        locator = mdates.DayLocator(interval=15)
        formatter = mdates.DateFormatter("%Y-%m-%d")
    elif date_range_days > 30:  # > 1 month → every week
        locator = mdates.DayLocator(interval=7)
        formatter = mdates.DateFormatter("%Y-%m-%d")
    else:  # Less than a month → every 3 days
        locator = mdates.DayLocator(interval=3)
        formatter = mdates.DateFormatter("%Y-%m-%d")

    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)



    plt.xticks(rotation=45)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_title(f"Daily Rainfall from {start_date} to {end_date}", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Rainfall (mm)", fontsize=12)
    ax.legend()

    st.pyplot(fig)

    # --- COMMENTS ON THE ANALYSIS ---
    st.write("**Comments on Rainfall Analysis:**")
    st.write("""
    This graph displays the daily total rainfall over the selected period.
    The marked points indicate the days with the lowest and highest rainfall.
    Understanding these extremes is crucial:
    - A prolonged period of low rainfall might signal drought conditions, potentially affecting water availability and crop yields.
    - Conversely, extremely high rainfall events can lead to flooding, causing damage to infrastructure and agricultural land.
    """)


        # --- SEASONAL EXTREME AMPLITUDE ANALYSIS ---
    st.subheader("Seasonal Extreme Amplitude Analysis")
    # Filter daily data for the selected period (using df_filtered from Seasonal Analysis)
    df_seasonal_daily = df_filtered.copy()

    # Define rainy season months and dry season months
    rainy_months = [5, 6, 7, 8, 9, 10]
    dry_months = [11, 12, 1, 2, 3, 4]

    # For rainy season: filter data and compute daily extremes by year
    rainy_df = df_seasonal_daily[df_seasonal_daily["date"].dt.month.isin(rainy_months)]
    rainy_extremes = rainy_df.groupby(rainy_df["date"].dt.year)["rfh"].agg(min_rain="min", max_rain="max").reset_index()
    rainy_extremes.columns = ["year", "min_rain", "max_rain"]

    # For dry season: filter data and compute daily extremes by year
    dry_df = df_seasonal_daily[df_seasonal_daily["date"].dt.month.isin(dry_months)]
    dry_extremes = dry_df.groupby(dry_df["date"].dt.year)["rfh"].agg(min_rain="min", max_rain="max").reset_index()
    dry_extremes.columns = ["year", "min_rain", "max_rain"]

    # Create a plot with two subplots: one for rainy season and one for dry season
    fig_ext, (ax_rainy, ax_dry) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    # Plot for rainy season extremes
    ax_rainy.plot(rainy_extremes["year"], rainy_extremes["max_rain"], marker="o", label="Max Rainfall (Rainy Season)", color="blue")
    ax_rainy.plot(rainy_extremes["year"], rainy_extremes["min_rain"], marker="o", label="Min Rainfall (Rainy Season)", color="orange")
    ax_rainy.set_title("Rainy Season Extreme Amplitudes by Year")
    ax_rainy.set_ylabel("Rainfall (mm)")
    ax_rainy.legend()
    ax_rainy.grid(True)

    # Plot for dry season extremes
    ax_dry.plot(dry_extremes["year"], dry_extremes["max_rain"], marker="o", label="Max Rainfall (Dry Season)", color="green")
    ax_dry.plot(dry_extremes["year"], dry_extremes["min_rain"], marker="o", label="Min Rainfall (Dry Season)", color="red")
    ax_dry.set_title("Dry Season Extreme Amplitudes by Year")
    ax_dry.set_xlabel("Year")
    ax_dry.set_ylabel("Rainfall (mm)")
    ax_dry.legend()
    ax_dry.grid(True)

    st.pyplot(fig_ext)

    st.write("""
    **Comments on Seasonal Extreme Amplitude Analysis:**
    The charts above display, for each year, the maximum and minimum daily rainfall values during the rainy and dry seasons.
    - In the rainy season, an increasing trend in maximum values might indicate a higher risk of intense rainfall events and potential flooding.
    - In the dry season, particularly low minimum values could signal worsening drought conditions.
    These trends are essential for understanding seasonal climate variability and for planning in agriculture and water management.
    """)


    st.title("📈 Annual Rainfall Trends")

    if not use_same_slider:
        min_date = df["date"].min()
        max_date = df["date"].max()
        start_date, end_date = st.slider(
            "Select the analysis period:",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(pd.to_datetime("2010-01-01").date(), pd.to_datetime("2020-12-31").date()),
            format="YYYY-MM-DD"
        )

    df_filtered = df[
        (df["date"] >= pd.to_datetime(start_date, format="%Y-%m-%d")) &
        (df["date"] <= pd.to_datetime(end_date, format="%Y-%m-%d"))
    ]
    df_filtered["year"] = df_filtered["date"].dt.year
    df_annual_filtered = df_filtered.groupby("year")["rfh"].sum().reset_index()

    # Perform linear regression to detect trend
    if not df_annual_filtered.empty:
        coeffs = np.polyfit(df_annual_filtered["year"], df_annual_filtered["rfh"], 1)
        trend_line = np.poly1d(coeffs)
        df_annual_filtered["trend"] = trend_line(df_annual_filtered["year"])

        # Determine minimum and maximum annual rainfall
        min_year = df_annual_filtered.loc[df_annual_filtered["rfh"].idxmin(), "year"]
        min_value = df_annual_filtered["rfh"].min()
        max_year = df_annual_filtered.loc[df_annual_filtered["rfh"].idxmax(), "year"]
        max_value = df_annual_filtered["rfh"].max()

        # Create a bar chart with trend line
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(df_annual_filtered["year"], df_annual_filtered["rfh"], color="b", alpha=0.7, label="Total Rainfall")
        ax.plot(df_annual_filtered["year"], df_annual_filtered["trend"], color="r", linestyle="--", linewidth=2, label="Trend Line")
        ax.scatter(min_year, min_value, color="green", s=100, label="Minimum")
        ax.scatter(max_year, max_value, color="red", s=100, label="Maximum")
        ax.text(min_year, min_value, f"Min: {min_value:.2f} mm", fontsize=10, verticalalignment="bottom", horizontalalignment="right", color="green", fontweight="bold")
        ax.text(max_year, max_value, f"Max: {max_value:.2f} mm", fontsize=10, verticalalignment="top", horizontalalignment="left", color="red", fontweight="bold")
        ax.set_xlabel("Year", fontsize=12)
        ax.set_ylabel("Total Rainfall (mm)", fontsize=12)
        ax.set_title(f"Annual Rainfall Trends ({start_date} - {end_date})", fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.7)

        st.pyplot(fig)

        # --- COMMENTS ON THE ANALYSIS ---
        st.write("**Comments on Annual Rainfall Trends:**")
        st.write("""
        This chart shows the total annual rainfall along with a linear trend.
        Significant year-to-year fluctuations can reflect changes in climate patterns.
        An upward trend might indicate an increased risk of flooding, whereas a downward trend may suggest a move toward drier conditions,
        which could impact water resources and agricultural productivity.
        """)

    col1, col2 , col3= st.columns([1, 2, 1])

    with col1:
        if st.button("← Previous page"):
            next_page_index = (pages.index(page) - 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()
    with col2:
        st.write("")

    with col3:
        if st.button("Next page →"):
            next_page_index = (pages.index(page) + 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()



# --- SEASONAL ANALYSIS ---
if page == "Seasonal Analysis":
    st.title("🌦️ Seasonal Rainfall Analysis")

    if not use_same_slider:
        min_date = df["date"].min()
        max_date = df["date"].max()
        start_date, end_date = st.slider(
            "Select the analysis period:",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(pd.to_datetime("2021-06-01").date(), pd.to_datetime("2022-06-01").date()),
            format="YYYY-MM-DD"
        )

    df_filtered = df[
        (df["date"] >= pd.to_datetime(start_date, format="%Y-%m-%d")) &
        (df["date"] <= pd.to_datetime(end_date, format="%Y-%m-%d"))
    ]

    # Aggregate data: daily rainfall sum
    df_daily_sum = df_filtered.groupby("date")["rfh"].sum().reset_index()
    df_daily_sum = df_daily_sum.sort_values(by="date").reset_index(drop=True)

    # --- PLOT ---
    fig, ax = plt.subplots(figsize=(12, 6))
    # Main line showing daily rainfall
    ax.plot(df_daily_sum["date"], df_daily_sum["rfh"], marker='o', linestyle='-', color='b', linewidth=2, markersize=6, label='Rainfall')

    # Highlight minimum and maximum values if data exists
    if not df_daily_sum.empty:
        min_value = df_daily_sum["rfh"].min()
        max_value = df_daily_sum["rfh"].max()
        min_date_point = df_daily_sum.loc[df_daily_sum["rfh"].idxmin(), "date"]
        max_date_point = df_daily_sum.loc[df_daily_sum["rfh"].idxmax(), "date"]

        ax.scatter(min_date_point, min_value, color='red', s=100, label="Min Rainfall")
        ax.scatter(max_date_point, max_value, color='green', s=100, label="Max Rainfall")
        ax.text(min_date_point, min_value, f"Min: {min_value:.2f} mm", fontsize=10, verticalalignment='bottom', horizontalalignment='right', color='red', fontweight='bold')
        ax.text(max_date_point, max_value, f"Max: {max_value:.2f} mm", fontsize=10, verticalalignment='top', horizontalalignment='left', color='green', fontweight='bold')

        # --- REGRESSION LINES FOR EXTREME RAINFALL ---
    # Define thresholds for high and low rainfall using quantiles
    high_threshold = df_daily_sum["rfh"].quantile(0.9)
    low_threshold = df_daily_sum["rfh"].quantile(0.1)

    # Filter the data for high rainfall (extreme high) and low rainfall (extreme low)
    df_high = df_daily_sum[df_daily_sum["rfh"] >= high_threshold]
    df_low = df_daily_sum[df_daily_sum["rfh"] <= low_threshold]

    # Regression for high rainfall days
    if not df_high.empty and len(df_high) >= 2:
        x_high = df_high["date"].map(lambda d: d.toordinal())
        y_high = df_high["rfh"]
        coeffs_high = np.polyfit(x_high, y_high, 1)
        poly_high = np.poly1d(coeffs_high)
        x_vals_high = np.linspace(x_high.min(), x_high.max(), 100)
        x_dates_high = [pd.Timestamp.fromordinal(int(x)) for x in x_vals_high]
        y_vals_high = poly_high(x_vals_high)
        ax.plot(x_dates_high, y_vals_high, color="darkgreen", linestyle="--", linewidth=2, label="Regression (High Rainfall)")

    # Regression for low rainfall days
    if not df_low.empty and len(df_low) >= 2:
        x_low = df_low["date"].map(lambda d: d.toordinal())
        y_low = df_low["rfh"]
        coeffs_low = np.polyfit(x_low, y_low, 1)
        poly_low = np.poly1d(coeffs_low)
        x_vals_low = np.linspace(x_low.min(), x_low.max(), 100)
        x_dates_low = [pd.Timestamp.fromordinal(int(x)) for x in x_vals_low]
        y_vals_low = poly_low(x_vals_low)
        ax.plot(x_dates_low, y_vals_low, color="darkred", linestyle="--", linewidth=2, label="Regression (Low Rainfall)")

    # --- DYNAMIC X-AXIS LABELS MANAGEMENT ---
    date_range_days = (end_date - start_date).days  # Number of days selected
    if date_range_days > 14600:  # > 40 years → every 10 years
        locator = mdates.YearLocator(10)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 7300:  # > 20 years → every 5 years
        locator = mdates.YearLocator(5)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 3650:  # > 10 years → every 2 years
        locator = mdates.YearLocator(2)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 1825:  # > 5 years → every year
        locator = mdates.YearLocator(1)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 730:  # > 2 years → every 6 months
        locator = mdates.MonthLocator(interval=6)
        formatter = mdates.DateFormatter("%Y-%m")
    elif date_range_days > 365:  # > 1 year → every 3 months
        locator = mdates.MonthLocator(interval=3)
        formatter = mdates.DateFormatter("%Y-%m")
    elif date_range_days > 180:  # > 6 months → every month
        locator = mdates.MonthLocator(interval=1)
        formatter = mdates.DateFormatter("%Y-%m")
    elif date_range_days > 90:  # > 3 months → every 15 days
        locator = mdates.DayLocator(interval=15)
        formatter = mdates.DateFormatter("%Y-%m-%d")
    elif date_range_days > 30:  # > 1 month → every week
        locator = mdates.DayLocator(interval=7)
        formatter = mdates.DateFormatter("%Y-%m-%d")
    else:  # Less than a month → every 3 days
        locator = mdates.DayLocator(interval=3)
        formatter = mdates.DateFormatter("%Y-%m-%d")

    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)


        # --- COLORED BANDS FOR DRY AND WET MONTHS ---
    # We will loop over each month in the selected period and compute the total rainfall.
    # For rainy season months (May to October): if total > 300 mm then mark as wet, else as dry.
    # For dry season months (November to April): if total < 50 mm then mark as dry, else as wet.
    label_flags = {
        "Dry Month (Rainy Season)": False,
        "Wet Month (Rainy Season)": False,
        "Dry Month (Dry Season)": False,
        "Wet Month (Dry Season)": False
    }
    rainy_months = [5, 6, 7, 8, 9, 10]
    dry_months = [11, 12, 1, 2, 3, 4]
    # Create a date range of month starts between start_date and end_date
    month_starts = pd.date_range(start=pd.Timestamp(start_date), end=pd.Timestamp(end_date), freq='MS')
    for m in month_starts:
        # Get the end of the month
        month_end = m + pd.offsets.MonthEnd(0)
        # Calculate the total rainfall for the month using the daily sums
        monthly_total = df_daily_sum[(df_daily_sum["date"] >= m) & (df_daily_sum["date"] <= month_end)]["rfh"].sum()
        # Determine if the month belongs to the rainy or dry season and apply thresholds
        if m.month in rainy_months:
            # For rainy season, threshold: 300 mm
            if monthly_total > 3000:
                label = "Wet Month (Rainy Season)"
                color = "lightblue"
            else:
                label = "Dry Month (Rainy Season)"
                color = "salmon"
        else:
            # For dry season, threshold: 50 mm
            if monthly_total < 1000:
                label = "Dry Month (Dry Season)"
                color = "salmon"
            else:
                label = "Wet Month (Dry Season)"
                color = "lightblue"
        # Add the colored band for this month, ensuring each label appears only once in the legend
        if not label_flags[label]:
            ax.axvspan(m, month_end, color=color, alpha=0.3, label=label)
            label_flags[label] = True
        else:
            ax.axvspan(m, month_end, color=color, alpha=0.3)
    plt.xticks(rotation=45)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_title(f"Daily Rainfall from {start_date} to {end_date}", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Rainfall (mm)", fontsize=12)
    ax.legend()

    st.pyplot(fig)

    # --- COMMENTS ON THE ANALYSIS ---
    st.write("**Comments on Rainfall Analysis:**")
    st.write("""
    This graph displays the daily total rainfall over the selected period.
    The marked points indicate the days with the lowest and highest rainfall.
    Understanding these extremes is crucial:
    - A prolonged period of low rainfall might signal drought conditions, potentially affecting water availability and crop yields.
    - Conversely, extremely high rainfall events can lead to flooding, causing damage to infrastructure and agricultural land.
    """)

    if not use_same_slider:
        min_date = df["date"].min()
        max_date = df["date"].max()
        start_date, end_date = st.slider(
            "Select the analysis period:",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(pd.to_datetime("2010-01-01").date(), pd.to_datetime("2020-12-31").date()),
            format="YYYY-MM-DD"
        )

    df_filtered = df[
        (df["date"] >= pd.to_datetime(start_date, format="%Y-%m-%d")) &
        (df["date"] <= pd.to_datetime(end_date, format="%Y-%m-%d"))
    ]
    df_filtered["year"] = df_filtered["date"].dt.year
    df_filtered["month"] = df_filtered["date"].dt.month
    df_seasonal = df_filtered.groupby(["year", "month"])["rfh"].sum().reset_index()

    # Checkbox to filter by specific years
    filter_years = st.checkbox("Select specific years", value=False)
    selected_years = df_seasonal["year"].unique()
    if filter_years:
        selected_years = st.multiselect("Select the years to display:", df_seasonal["year"].unique(), default=df_seasonal["year"].unique())
    df_seasonal_filtered = df_seasonal[df_seasonal["year"].isin(selected_years)]

    # Create the seasonal average graph
    fig, ax = plt.subplots(figsize=(12, 6))
    df_monthly_avg = df_seasonal_filtered.groupby("month")["rfh"].mean().reset_index()
    ax.bar(df_monthly_avg["month"], df_monthly_avg["rfh"], color="b", alpha=0.7, label="Average Monthly Rainfall")
    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel("Average Rainfall (mm)", fontsize=12)
    ax.set_title(f"Average Monthly Rainfall ({start_date} - {end_date})", fontsize=14, fontweight="bold")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    st.pyplot(fig)

    # --- COMMENTS ON THE ANALYSIS ---
    st.write("**Comments on Seasonal Analysis:**")
    st.write("""
    The bar chart above presents the average monthly rainfall.
    This helps in identifying seasonal patterns: months with consistently low rainfall may indicate a dry season,
    whereas months with high rainfall are likely during the wet season.
    Such insights are vital for planning agricultural activities and managing water resources.
    """)

    # Plot seasonal trends per year
    fig, ax = plt.subplots(figsize=(12, 6))
    for year in df_seasonal_filtered["year"].unique():
        df_yearly = df_seasonal_filtered[df_seasonal_filtered["year"] == year]
        ax.plot(df_yearly["month"], df_yearly["rfh"], marker='o', linestyle='-', alpha=0.6, label=str(year))
    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel("Total Rainfall (mm)", fontsize=12)
    ax.set_title(f"Yearly Seasonal Trends ({start_date} - {end_date})", fontsize=14, fontweight="bold")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    st.pyplot(fig)

    col1, col2 , col3= st.columns([1, 2, 1])

    with col1:
        if st.button("← Previous page"):
            next_page_index = (pages.index(page) - 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()
    with col2:
        st.write("")

    with col3:
        if st.button("Next page →"):
            next_page_index = (pages.index(page) + 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()

# --- GEOGRAPHICAL DISTRIBUTION ---
elif page == "Geographical Distribution":
    st.title("🗺️ Geographical Distribution")
    st.write("Coming soon: Visualization of rainfall by region.")


    col1, col2 , col3= st.columns([1, 2, 1])

    with col1:
        if st.button("← Previous page"):
            next_page_index = (pages.index(page) - 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()
    with col2:
        st.write("")

    with col3:
        if st.button("Next page →"):
            next_page_index = (pages.index(page) + 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()

# --- RAW DATA ---
elif page == "Raw Data":
    st.title("📜 Raw Data")
    st.write("Preview of the rainfall dataset:")
    st.dataframe(df)

    st.write("Preview of the climate change dataset dataset:")
    file_path = "climate-change_bfa.csv"
    df_land = pd.read_csv(file_path)
    df_burkina = df_land[df_land["Country Name"] == "Burkina Faso"]
    st.dataframe(df_burkina)


    col1, col2 , col3= st.columns([1, 2, 1])

    with col1:
        if st.button("← Previous page"):
            next_page_index = (pages.index(page) - 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()
    with col2:
        st.write("")

    with col3:
        if st.button("Next page →"):
            next_page_index = (pages.index(page) + 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()

# --- LAND USE ---
if page == "Land Use":
    st.title("🌍 Land Use in Burkina Faso")

    # Load the dataset for land use
    file_path = "climate-change_bfa.csv"
    df_land = pd.read_csv(file_path)
    df_burkina = df_land[df_land["Country Name"] == "Burkina Faso"]

    # Filter the three main indicators
    agriculture = df_burkina[df_burkina["Indicator Name"] == "Agricultural land (% of land area)"]
    forest = df_burkina[df_burkina["Indicator Name"] == "Forest area (% of land area)"]
    arable = df_burkina[df_burkina["Indicator Name"] == "Arable land (% of land area)"]

    # Merge the three datasets by year
    df_selected = pd.merge(agriculture[['Year', 'Value']], forest[['Year', 'Value']], on="Year", suffixes=('_agriculture', '_forest'))
    df_selected = pd.merge(df_selected, arable[['Year', 'Value']], on="Year")
    df_selected.rename(columns={"Value": "Value_arable"}, inplace=True)

    # Convert values to numeric
    df_selected['Value_agriculture'] = pd.to_numeric(df_selected['Value_agriculture'], errors='coerce')
    df_selected['Value_forest'] = pd.to_numeric(df_selected['Value_forest'], errors='coerce')
    df_selected['Value_arable'] = pd.to_numeric(df_selected['Value_arable'], errors='coerce')

    # Convert 'Year' to datetime and sort
    df_selected['Year'] = pd.to_datetime(df_selected['Year'], format='%Y')
    df_selected = df_selected.sort_values(by="Year", ascending=True)

    # Add interactive slider for Land Use analysis
    if use_same_slider:
        start_year = start_date.year
        end_year = end_date.year
    else:
        min_year_land = int(df_selected['Year'].min().year)
        max_year_land = int(df_selected['Year'].max().year)
        start_year, end_year = st.slider(
            "Select the analysis period for Land Use:",
            min_value=min_year_land,
            max_value=max_year_land,
            value=(min_year_land, max_year_land),
            step=1
        )

    # Filter the land use data based on the selected year range
    df_selected = df_selected[(df_selected['Year'].dt.year >= start_year) & (df_selected['Year'].dt.year <= end_year)]

    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df_selected['Year'], df_selected['Value_agriculture'], label="Agricultural Land (%)", color="green", linewidth=2)
    ax.plot(df_selected['Year'], df_selected['Value_forest'], label="Forest Area (%)", color="brown", linewidth=2, linestyle="dashed")
    ax.plot(df_selected['Year'], df_selected['Value_arable'], label="Arable Land (%)", color="blue", linewidth=2, linestyle="dotted")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percentage of Total Area")
    ax.set_title(f"Agricultural, Forest, and Arable Land in Burkina Faso ({start_year} - {end_year})", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True)
    ax.ticklabel_format(style='plain', axis='y')
    st.pyplot(fig)

    # --- CORRELATION BETWEEN ANNUAL RAINFALL AND LAND USE INDICATORS ---
    # Aggregate annual rainfall from the rainfall dataset
    df_rainfall = df.copy()
    df_rainfall["year"] = df_rainfall["date"].dt.year
    df_annual_rainfall = df_rainfall.groupby("year")["rfh"].sum().reset_index()
    df_annual_rainfall.rename(columns={"rfh": "Total_Rainfall"}, inplace=True)

    # Ensure df_selected has an integer 'year' column for merging
    df_selected["year"] = df_selected["Year"].dt.year

    # Merge the land use data with the annual rainfall data on the year column
    df_merged = pd.merge(df_selected, df_annual_rainfall, left_on="year", right_on="year", how="inner")

    # Compute the correlation matrix including Total_Rainfall and land use indicators
    corr_cols = ["Value_agriculture", "Value_forest", "Value_arable", "Total_Rainfall"]
    corr_matrix = df_merged[corr_cols].corr()

    st.write("### Correlation Matrix between Annual Rainfall and Land Use Indicators:")
    st.dataframe(corr_matrix)



    # --- COMMENTS ON THE ANALYSIS ---
    st.write("**Comments on Land Use Analysis:**")
    st.write("""
    The above line charts illustrate the trends in land use over time.
    Notably, if agricultural land is expanding while forest area declines, it might suggest deforestation to make way for farming,
    which could have negative consequences on biodiversity, carbon sequestration, and climate regulation.
    The correlation matrix helps quantify these relationships and indicates how changes in one type of land use may be associated with changes in another.
    """)

    # --- CORRELATION BETWEEN ANNUAL RAINFALL AND LAND USE INDICATORS ---
    # Aggregate annual rainfall from the rainfall dataset
    df_rainfall = df.copy()
    df_rainfall["year"] = df_rainfall["date"].dt.year
    df_annual_rainfall = df_rainfall.groupby("year")["rfh"].sum().reset_index()
    df_annual_rainfall.rename(columns={"rfh": "Total_Rainfall"}, inplace=True)

    # Ensure df_selected has an integer 'year' column for merging
    df_selected["year"] = df_selected["Year"].dt.year

    # Merge the land use data with the annual rainfall data on the year column
    df_merged = pd.merge(df_selected, df_annual_rainfall, left_on="year", right_on="year", how="inner")

    # Compute the correlation matrix including Total_Rainfall and land use indicators
    corr_cols = ["Value_agriculture", "Value_forest", "Value_arable", "Total_Rainfall"]
    corr_matrix = df_merged[corr_cols].corr()

    st.write("### Correlation Matrix between Annual Rainfall and Land Use Indicators:")


    import seaborn as sns
    # Create a heatmap of the correlation matrix
    fig_corr, ax_corr = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", ax=ax_corr)
    ax_corr.set_title("Correlation Heatmap: Land Use & Annual Rainfall", fontsize=14, fontweight="bold")
    st.pyplot(fig_corr)
    #st.dataframe(corr_matrix)

    # Comments on the correlation analysis
    st.write("""
    **Comments on Rainfall and Land Use Correlation:**
    This merged analysis shows how annual total rainfall correlates with different land use indicators.
    For instance:
    - A negative correlation between Total Rainfall and Forest Area might suggest that drier conditions are associated with a decline in forest cover.
    - A positive correlation with Agricultural Land could indicate that higher rainfall supports more extensive farming areas.
    These insights are crucial for understanding how climatic factors can influence land use dynamics, potentially affecting biodiversity, water resources, and agricultural productivity.
    """)

    col1, col2 , col3= st.columns([1, 2, 1])

    with col1:
        if st.button("← Previous page"):
            next_page_index = (pages.index(page) - 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()
    with col2:
        st.write("")

    with col3:
        if st.button("Next page →"):
            next_page_index = (pages.index(page) + 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()

# --- CREDITS PAGE ---
if page == "Credits":
    st.title("👨‍💻 Credits")
    st.write("This project was developed by the following contributors:")

    developers = [
        {"name": "Tommaso Dognini", "link": "https://tommasodognini.com"},
        {"name": "Mattia D'Onghia", "link": "https://github.com/mattiadonghia"},
        {"name": "Nicholas Penne", "link": "https://github.com/nicholaspenne"},
        {"name": "Giovanni Dal Lago", "link": "https://github.com/giovannidallago"}
    ]

    for dev in developers:
        st.markdown(f"- [{dev['name']}]({dev['link']})")

    st.write("Thank you for using our application!")


    col1, col2 , col3= st.columns([1, 2, 1])

    with col1:
        if st.button("← Previous page"):
            next_page_index = (pages.index(page) - 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()
    with col2:
        st.write("")

    with col3:
        if st.button("Next page →"):
            next_page_index = (pages.index(page) + 1) % len(pages)
            st.session_state["selected_page"] = pages[next_page_index]
            st.rerun()