"""
Water Survival Analysis page - Time series and rainfall data.
"""
from typing import Dict, Optional, List
import pandas as pd
import streamlit as st

from geodash.ui import (
    build_map_with_controls,
    chart_farm_survival_analytics,
    chart_region_comparison,
    chart_seasonal_analysis,
    chart_survival_rate,
    chart_rain_statistics,
    metadata_panel,
)
from geodash.data.rain_service import get_rain_service


def render_water_survival(
    data: Dict,
    filtered_wells: pd.DataFrame,
    map_state: Dict,
    selected_row: Optional[pd.Series],
    selected_farm_region: Optional[str],
    selected_farm_coordinates: Optional[List],
    rain_data: Optional[pd.DataFrame],
    rain_stats: Optional[Dict]
) -> None:
    """
    Render the water survival analysis page.
    
    Args:
        data: Complete dashboard data
        filtered_wells: Filtered wells DataFrame
        map_state: Current map state
        selected_row: Selected well row
        selected_farm_region: Selected farm/region for analysis
        selected_farm_coordinates: Coordinates of selected farm
        rain_data: Rain data if farm selected
        rain_stats: Rain statistics if farm selected
    """
    
    # Show rain data if available
    st.markdown("**🌧️ Rain Data Status**")
    if rain_data is not None:
        st.success(f"✅ Rain data loaded: {len(rain_data)} records")
        chart_rain_statistics(rain_data, rain_stats)
    else:
        st.info("ℹ️ No rain data available - click anywhere on the map to get rain data for that location")
    st.markdown("---")

    
    # Farm-based time series analysis
    st.markdown("**🚜 Farm Survival Analytics**")
    chart_farm_survival_analytics(data["farm_time_series"], selected_farm_region)
    
    # Show regional comparison if no specific region selected
    if selected_farm_region is None:
        st.markdown("**📊 Regional Comparison**")
        chart_region_comparison(data["farm_time_series"])
        
        st.markdown("**🌿 Seasonal Analysis**")
        chart_seasonal_analysis(data["farm_time_series"])
    
    st.markdown("---")
    
    # Overall well success rate
    st.markdown("**📈 Overall Well Success Rate**")
    chart_survival_rate(filtered_wells)
    
    st.markdown("---")
    
    # Metadata
    st.markdown("**📋 Selected Well Metadata**")
    metadata_panel(selected_row)
    
    # Instructions
    if selected_farm_coordinates is None:
        st.info("""
        **💡 Tips:**
        - Click on a farm polygon (colored areas) to view rain statistics
        - Select a specific region in the sidebar for detailed time series analysis
        - Use the map controls to show/hide different layers
        """)

