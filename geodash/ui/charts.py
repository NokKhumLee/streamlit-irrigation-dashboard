from typing import Optional, Dict, List

import altair as alt
import pandas as pd
import streamlit as st


def chart_ground_water_analytics(water_levels: pd.DataFrame, selected_well: Optional[str]) -> None:
    if selected_well is None:
        st.info("Select a well (via map click or search) to view time series.")
        return
    df = water_levels[water_levels["well_id"] == selected_well]
    line = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(x="date:T", y=alt.Y("water_level_m:Q", title="Water level (m)"))
        .properties(height=200)
    )
    st.altair_chart(line, use_container_width=True)


def chart_survival_rate(wells_df: pd.DataFrame) -> None:
    counts = wells_df["survived"].value_counts().rename(index={True: "Success", False: "Failure"}).reset_index()
    counts.columns = ["status", "count"]
    pie = alt.Chart(counts).mark_arc(innerRadius=40).encode(theta="count:Q", color="status:N")
    st.altair_chart(pie, use_container_width=True)


def chart_probability_by_depth(prob_df: pd.DataFrame) -> None:
    bars = alt.Chart(prob_df).mark_bar().encode(x="depth_m:O", y=alt.Y("probability:Q", axis=alt.Axis(format=".0%")))
    st.altair_chart(bars, use_container_width=True)


def chart_cost_estimation(cost_df: pd.DataFrame) -> None:
    bars = alt.Chart(cost_df).mark_bar().encode(x="depth_m:O", y=alt.Y("estimated_cost_thb:Q", title="Estimated cost (THB)"))
    st.altair_chart(bars, use_container_width=True)


def chart_rain_statistics(rain_df: pd.DataFrame, stats: Dict[str, float]) -> None:
    """
    Display rain statistics charts and metrics.
    
    Args:
        rain_df: DataFrame with rain data
        stats: Dictionary with rain statistics
    """
    if rain_df is None or rain_df.empty:
        st.info("No rain data available for the selected location.")
        return
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Rain", f"{stats.get('total_rain_mm', 0):.1f} mm")
    with col2:
        st.metric("Avg Daily", f"{stats.get('avg_daily_rain_mm', 0):.1f} mm")
    with col3:
        st.metric("Max Daily", f"{stats.get('max_daily_rain_mm', 0):.1f} mm")
    with col4:
        st.metric("Rainy Days", f"{stats.get('rainy_days', 0)}/{stats.get('total_days', 0)}")
    
    # Monthly rain chart
    if len(rain_df) > 0:
        # Create monthly summary
        monthly_data = rain_df.resample('M', on='date')['rain'].sum().reset_index()
        monthly_data['month'] = monthly_data['date'].dt.strftime('%Y-%m')
        monthly_data['rain_mm'] = monthly_data['rain']
        
        if not monthly_data.empty:
            st.subheader("📊 Monthly Rainfall")
            monthly_chart = (
                alt.Chart(monthly_data)
                .mark_bar(color='#4CAF50')
                .encode(
                    x=alt.X('month:O', title='Month'),
                    y=alt.Y('rain_mm:Q', title='Rainfall (mm)')
                )
                .properties(height=300)
            )
            st.altair_chart(monthly_chart, use_container_width=True)
        


def chart_rain_frequency(stats: Dict[str, float]) -> None:
    """
    Display rain frequency pie chart.
    
    Args:
        stats: Dictionary with rain statistics
    """
    if not stats:
        return
        
    rainy_days = stats.get('rainy_days', 0)
    total_days = stats.get('total_days', 1)
    dry_days = total_days - rainy_days
    
    if total_days > 0:
        frequency_data = pd.DataFrame({
            'condition': ['Rainy Days', 'Dry Days'],
            'count': [rainy_days, dry_days]
        })
        
        pie_chart = (
            alt.Chart(frequency_data)
            .mark_arc(innerRadius=40)
            .encode(
                theta='count:Q',
                color=alt.Color('condition:N', scale=alt.Scale(range=['#4CAF50', '#FFC107']))
            )
            .properties(height=200)
        )
        
        st.subheader("🌧️ Rain Frequency")
        st.altair_chart(pie_chart, use_container_width=True)



