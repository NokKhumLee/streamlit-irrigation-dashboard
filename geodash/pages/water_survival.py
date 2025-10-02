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
    Render the water survival analysis page - now only shows rain statistics.
    
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
    
    # Title and instructions
    st.title("🌧️ Rain Data Analysis")
    st.markdown("### Click on the map to view rain data for any location")
    
    # Check if user clicked somewhere while on other pages and offer to load that data
    if rain_data is None and "last_clicked_coordinates" in st.session_state:
        clicked_lat, clicked_lng = st.session_state.last_clicked_coordinates
        if st.button(f"🌧️ Load rain data for last clicked location ({clicked_lat:.4f}, {clicked_lng:.4f})"):
            # This will trigger a rerun with rain data fetching
            rain_service = get_rain_service()
            if rain_service.client:
                with st.spinner("Fetching rain data..."):
                    rain_data = rain_service.get_rain_data(clicked_lat, clicked_lng, days_back=365)
                    if rain_data is not None:
                        rain_stats = rain_service.get_rain_statistics(rain_data)
                        st.session_state.last_rain_coordinates = (clicked_lat, clicked_lng)
                        st.rerun()
    
    # Show rain data if available
    if rain_data is not None:
        st.success(f"✅ Rain data loaded: {len(rain_data)} records")
        chart_rain_statistics(rain_data, rain_stats)
    else:
        st.info("ℹ️ Click anywhere on the map to get rain data for that location")
        st.markdown("""
        **💡 How to use:**
        - Click on any point on the map to fetch rainfall data for that location
        - The system will show rainfall statistics, trends, and seasonal patterns
        - Data covers the last 365 days from the selected point
        """)

