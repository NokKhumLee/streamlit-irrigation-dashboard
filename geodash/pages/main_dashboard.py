"""
Main Dashboard page - Overview of wells, fields, and costs.
"""
from typing import Dict, Optional
import pandas as pd
import streamlit as st

from geodash.ui import (
    build_map_with_controls,
    chart_cost_estimation,
    metadata_panel,
    download_button,
)


def render_main_dashboard(
    data: Dict,
    filtered_wells: pd.DataFrame,
    map_state: Dict,
    selected_row: Optional[pd.Series]
) -> None:
    """
    Render the main dashboard page.
    
    Args:
        data: Complete dashboard data
        filtered_wells: Filtered wells DataFrame
        map_state: Current map state
        selected_row: Selected well row (if any)
    """
    
    # Dashboard title is in main app.py
    
    # Metrics
    col1, col2 = st.columns(2)
    
    with col1:
        avg_depth = int(filtered_wells["depth_m"].mean()) if not filtered_wells.empty else 0
        st.metric("Average Depth", f"{avg_depth}m")
    
    with col2:
        if data.get("farm_polygons"):
            st.metric("Total Farms", len(data["farm_polygons"]))
    
    st.markdown("---")
    
    # Metadata panel
    st.markdown("**📋 Well Metadata**")
    metadata_panel(selected_row)
    
    st.markdown("---")
    
    # Cost estimation chart
    st.markdown("**💰 Cost Estimation (by depth)**")
    chart_cost_estimation(data["cost_df"])
    
    st.markdown("---")
    
    # Download button
    download_button(filtered_wells)
    
    # Info panel
    with st.expander("ℹ️ How to Use This Dashboard"):
        st.markdown("""
        **Main Dashboard Features:**
        
        1. **Map Controls**: Use checkboxes above the map to toggle layers
        2. **Well Selection**: Click on wells or enter Well ID
        3. **Filters**: Use sidebar to filter by region and depth
        4. **Cost Analysis**: View drilling costs by depth
        5. **Export Data**: Download filtered well data as CSV
        
        **Tips:**
        - 🟢 Green dots = Successful wells
        - 🔴 Red dots = Failed wells
        - Click on wells for detailed information
        """)

