# geodash/ui/charts.py - Updated for farm-based time series

from typing import Optional, Dict, List

import altair as alt
import pandas as pd
import streamlit as st


def chart_farm_survival_analytics(farm_time_series: pd.DataFrame, selected_region: Optional[str]) -> None:
    """
    Display time series charts for farm/region survival analysis.
    
    Args:
        farm_time_series: DataFrame with farm time series data
        selected_region: Selected region/farm to display, None shows all
    """
    if farm_time_series is None or farm_time_series.empty:
        st.info("No farm time series data available.")
        return
    
    if selected_region is None:
        st.info("Select a region to view detailed time series analysis.")
        
        # Show overview of all regions
        if not farm_time_series.empty:
            st.subheader("📊 All Regions Overview")
            
            # Average survival rate by region
            region_avg = (
                farm_time_series.groupby("region")["survival_rate"]
                .mean()
                .reset_index()
                .sort_values("survival_rate", ascending=False)
            )
            
            if not region_avg.empty:
                bars = (
                    alt.Chart(region_avg)
                    .mark_bar(color='#4CAF50')
                    .encode(
                        x=alt.X('region:N', title='Region', sort='-y'),
                        y=alt.Y('survival_rate:Q', title='Average Survival Rate', axis=alt.Axis(format='.0%'))
                    )
                    .properties(height=300, title="Average Survival Rate by Region")
                )
                st.altair_chart(bars, use_container_width=True)
        return
    
    # Filter data for selected region
    df = farm_time_series[farm_time_series["region"] == selected_region].copy()
    
    if df.empty:
        st.warning(f"No data available for region: {selected_region}")
        return
    
    st.subheader(f"📈 Time Series Analysis: {selected_region}")
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    latest_data = df.iloc[-1] if not df.empty else None
    if latest_data is not None:
        with col1:
            st.metric("Current Survival Rate", f"{latest_data['survival_rate']:.1%}")
        with col2:
            st.metric("Total Wells", int(latest_data['total_wells']))
        with col3:
            st.metric("Successful Wells", int(latest_data['successful_wells']))
        with col4:
            avg_water_level = df['water_level_avg_m'].mean()
            st.metric("Avg Water Level", f"{avg_water_level:.1f}m")
    
    # Survival rate time series chart
    line_survival = (
        alt.Chart(df)
        .mark_line(point=True, color='#2E7D32')
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("survival_rate:Q", title="Survival Rate", axis=alt.Axis(format='.0%')),
            tooltip=['date:T', 'survival_rate:Q', 'total_wells:Q', 'successful_wells:Q']
        )
        .properties(height=250, title=f"Survival Rate Over Time - {selected_region}")
    )
    st.altair_chart(line_survival, use_container_width=True)
    
    # Water level time series chart
    line_water = (
        alt.Chart(df)
        .mark_line(point=True, color='#1976D2')
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("water_level_avg_m:Q", title="Average Water Level (m)"),
            tooltip=['date:T', 'water_level_avg_m:Q']
        )
        .properties(height=250, title=f"Average Water Level Over Time - {selected_region}")
    )
    st.altair_chart(line_water, use_container_width=True)
    
    # Rainfall correlation chart (if available)
    if 'rainfall_mm' in df.columns:
        # Create dual-axis chart showing survival rate vs rainfall
        base = alt.Chart(df).add_selection(
            alt.selection_interval(bind='scales')
        )
        
        rainfall_bars = base.mark_bar(opacity=0.6, color='#FF9800').encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("rainfall_mm:Q", title="Rainfall (mm)", scale=alt.Scale(domain=[0, df['rainfall_mm'].max() * 1.1]))
        )
        
        survival_line = base.mark_line(point=True, color='#4CAF50', strokeWidth=3).encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("survival_rate:Q", title="Survival Rate", 
                   scale=alt.Scale(domain=[0, 1]), 
                   axis=alt.Axis(format='.0%'))
        )
        
        # Combine charts
        combined_chart = alt.layer(rainfall_bars, survival_line).resolve_scale(
            y='independent'
        ).properties(
            height=300, 
            title=f"Survival Rate vs Rainfall Correlation - {selected_region}"
        )
        
        st.altair_chart(combined_chart, use_container_width=True)


def chart_ground_water_analytics(farm_time_series: pd.DataFrame, selected_region: Optional[str]) -> None:
    """
    Legacy function name maintained for backward compatibility.
    Now redirects to farm survival analytics.
    """
    chart_farm_survival_analytics(farm_time_series, selected_region)


def chart_survival_rate(wells_df: pd.DataFrame) -> None:
    """
    Display overall survival rate pie chart from wells data.
    """
    if wells_df is None or wells_df.empty:
        st.info("No wells data available for survival rate analysis.")
        return
        
    counts = wells_df["survived"].value_counts().rename(index={True: "Success", False: "Failure"}).reset_index()
    counts.columns = ["status", "count"]
    
    pie = (
        alt.Chart(counts)
        .mark_arc(innerRadius=40)
        .encode(
            theta="count:Q",
            color=alt.Color("status:N", 
                          scale=alt.Scale(range=['#4CAF50', '#F44336']),
                          legend=alt.Legend(title="Well Status"))
        )
        .properties(height=200, title="Overall Well Success Rate")
    )
    st.altair_chart(pie, use_container_width=True)


def chart_region_comparison(farm_time_series: pd.DataFrame) -> None:
    """
    Compare survival rates across different regions/farms.
    
    Args:
        farm_time_series: DataFrame with farm time series data
    """
    if farm_time_series is None or farm_time_series.empty:
        st.info("No farm time series data available for region comparison.")
        return
    
    # Calculate average survival rate by region
    region_stats = (
        farm_time_series.groupby("region")
        .agg({
            "survival_rate": ["mean", "std"],
            "total_wells": "first",
            "water_level_avg_m": "mean"
        })
        .round(3)
    )
    
    # Flatten column names
    region_stats.columns = ['avg_survival_rate', 'std_survival_rate', 'total_wells', 'avg_water_level']
    region_stats = region_stats.reset_index()
    
    # Create comparison chart
    bars = (
        alt.Chart(region_stats)
        .mark_bar()
        .encode(
            x=alt.X('region:N', title='Region', sort='-y'),
            y=alt.Y('avg_survival_rate:Q', title='Average Survival Rate', axis=alt.Axis(format='.0%')),
            color=alt.Color('avg_survival_rate:Q', scale=alt.Scale(scheme='greens')),
            tooltip=['region:N', 'avg_survival_rate:Q', 'total_wells:Q', 'avg_water_level:Q']
        )
        .properties(height=300, title="Average Survival Rate by Region")
    )
    
    st.altair_chart(bars, use_container_width=True)
    
    # Show detailed statistics table
    with st.expander("📊 Detailed Region Statistics"):
        # Format the dataframe for display
        display_df = region_stats.copy()
        display_df['avg_survival_rate'] = display_df['avg_survival_rate'].apply(lambda x: f"{x:.1%}")
        display_df['std_survival_rate'] = display_df['std_survival_rate'].apply(lambda x: f"±{x:.1%}")
        display_df['avg_water_level'] = display_df['avg_water_level'].apply(lambda x: f"{x:.1f}m")
        display_df.columns = ['Region', 'Avg Survival Rate', 'Std Deviation', 'Total Wells', 'Avg Water Level']
        
        st.dataframe(display_df, use_container_width=True)


def chart_probability_by_depth(prob_df: pd.DataFrame) -> None:
    """
    Display probability by depth chart.
    """
    if prob_df is None or prob_df.empty:
        st.info("No probability data available.")
        return
        
    bars = (
        alt.Chart(prob_df)
        .mark_bar(color='#2196F3')
        .encode(
            x=alt.X("depth_m:O", title="Depth (m)"),
            y=alt.Y("probability:Q", title="Success Probability", axis=alt.Axis(format=".0%"))
        )
        .properties(height=300, title="Well Success Probability by Depth")
    )
    st.altair_chart(bars, use_container_width=True)


def chart_cost_estimation(cost_df: pd.DataFrame) -> None:
    """
    Display cost estimation chart.
    """
    if cost_df is None or cost_df.empty:
        st.info("No cost estimation data available.")
        return
        
    bars = (
        alt.Chart(cost_df)
        .mark_bar(color='#FF9800')
        .encode(
            x=alt.X("depth_m:O", title="Depth (m)"),
            y=alt.Y("estimated_cost_thb:Q", title="Estimated Cost (THB)")
        )
        .properties(height=300, title="Estimated Drilling Cost by Depth")
    )
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


def chart_seasonal_analysis(farm_time_series: pd.DataFrame) -> None:
    """
    Display seasonal analysis of farm performance.
    
    Args:
        farm_time_series: DataFrame with farm time series data
    """
    if farm_time_series is None or farm_time_series.empty:
        st.info("No farm time series data available for seasonal analysis.")
        return
    
    # Add month column for seasonal analysis
    df_seasonal = farm_time_series.copy()
    df_seasonal['month'] = df_seasonal['date'].dt.month
    df_seasonal['season'] = df_seasonal['month'].apply(lambda x: 
        'Dry Season (Nov-Apr)' if x in [11, 12, 1, 2, 3, 4] else 'Rainy Season (May-Oct)')
    
    # Calculate seasonal averages
    seasonal_avg = (
        df_seasonal.groupby(['season', 'region'])['survival_rate']
        .mean()
        .reset_index()
    )
    
    if not seasonal_avg.empty:
        # Create grouped bar chart
        bars = (
            alt.Chart(seasonal_avg)
            .mark_bar()
            .encode(
                x=alt.X('region:N', title='Region'),
                y=alt.Y('survival_rate:Q', title='Average Survival Rate', axis=alt.Axis(format='.0%')),
                color=alt.Color('season:N', 
                              scale=alt.Scale(range=['#FFC107', '#4CAF50']),
                              legend=alt.Legend(title="Season")),
                column='season:N'
            )
            .properties(width=200, height=300, title="Seasonal Survival Rate Comparison")
        )
        
        st.subheader("🌿 Seasonal Analysis")
        st.altair_chart(bars, use_container_width=False)
        
        # Statistical insights
        overall_dry = seasonal_avg[seasonal_avg['season'].str.contains('Dry')]['survival_rate'].mean()
        overall_rainy = seasonal_avg[seasonal_avg['season'].str.contains('Rainy')]['survival_rate'].mean()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Dry Season Avg", f"{overall_dry:.1%}")
        with col2:
            st.metric("Rainy Season Avg", f"{overall_rainy:.1%}")
        
        if overall_rainy > overall_dry:
            st.success("🌧️ Wells perform better during rainy season")
        else:
            st.info("☀️ Wells perform better during dry season")
            
def chart_water_requirements(water_req_df: pd.DataFrame, stats: Dict[str, float], farm_name: str) -> None:
    """
    Display water requirements charts for sugarcane farming.
    
    Args:
        water_req_df: DataFrame with water requirements data
        stats: Dictionary with water requirement statistics
        farm_name: Name of the farm
    """
    if water_req_df is None or water_req_df.empty:
        st.info("No water requirements data available for the selected farm.")
        return
    
    st.subheader(f"💧 Water Requirements - {farm_name}")
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Water Need", f"{stats.get('total_water_requirement_cubic_m', 0):,.0f} m³")
    with col2:
        st.metric("Avg Monthly", f"{stats.get('avg_monthly_water_requirement_cubic_m', 0):,.0f} m³")
    with col3:
        st.metric("Max Monthly", f"{stats.get('max_monthly_water_requirement_cubic_m', 0):,.0f} m³")
    with col4:
        st.metric("Deficit Months", f"{stats.get('months_with_water_deficit', 0)}/12")
    
    # Monthly water requirements chart
    if not water_req_df.empty:
        # Create chart data with month abbreviations
        chart_data = water_req_df.copy()
        chart_data['month_abbr'] = chart_data['month_name'].str[:3]
        
        # Water requirements bar chart
        water_chart = (
            alt.Chart(chart_data)
            .mark_bar(color='#2196F3')
            .encode(
                x=alt.X('month_abbr:O', title='Month', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                y=alt.Y('water_requirement_cubic_m:Q', title='Water Requirement (m³)')
            )
            .properties(height=300, title="Monthly Water Requirements")
        )
        
        st.altair_chart(water_chart, use_container_width=True)
        
        # Water deficit vs crop need comparison
        comparison_data = []
        for _, row in water_req_df.iterrows():
            comparison_data.extend([
                {'month': row['month_abbr'], 'type': 'Crop Water Need', 'value': row['crop_water_need_mm']},
                {'month': row['month_abbr'], 'type': 'Actual Rain', 'value': row['rain_mm']},
                {'month': row['month_abbr'], 'type': 'Water Deficit', 'value': row['water_deficit_mm']}
            ])
        
        comparison_df = pd.DataFrame(comparison_data)
        
        comparison_chart = (
            alt.Chart(comparison_df)
            .mark_bar()
            .encode(
                x=alt.X('month:O', title='Month', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                y=alt.Y('value:Q', title='Water (mm)'),
                color=alt.Color('type:N', scale=alt.Scale(range=['#4CAF50', '#FF9800', '#F44336']))
            )
            .properties(height=300, title="Water Need vs Rainfall vs Deficit")
        )
        
        st.altair_chart(comparison_chart, use_container_width=True)
        
        # Summary table
        st.subheader("📋 Monthly Water Analysis")
        display_df = water_req_df[['month_name', 'crop_water_need_mm', 'rain_mm', 
                                  'water_deficit_mm', 'water_requirement_cubic_m']].copy()
        display_df.columns = ['Month', 'Crop Need (mm)', 'Rain (mm)', 'Deficit (mm)', 'Water Need (m³)']
        display_df['Water Need (m³)'] = display_df['Water Need (m³)'].round(0)
        
        st.dataframe(display_df, use_container_width=True)



