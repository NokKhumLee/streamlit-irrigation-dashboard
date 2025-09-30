"""
Underground Water Discovery page - Probability heatmaps and analysis.
"""
from typing import Dict, Optional
import pandas as pd
import streamlit as st

from geodash.ui import (
    build_map_with_controls,
    chart_probability_by_depth,
    metadata_panel,
)


def render_discovery(
    data: Dict,
    filtered_wells: pd.DataFrame,
    map_state: Dict,
    selected_row: Optional[pd.Series]
) -> None:
    """
    Render the underground water discovery page.
    
    Args:
        data: Complete dashboard data
        filtered_wells: Filtered wells DataFrame
        map_state: Current map state
        selected_row: Selected well row
    """
    
    st.markdown("**🔍 Ground Water Discovery Probability**")
    chart_probability_by_depth(data["prob_df"])
    
    st.markdown("---")
    
    st.markdown("**📋 Selected Well Metadata**")
    metadata_panel(selected_row)
    
    st.markdown("---")
    
    st.markdown("**💡 Discovery Tips & Map Legend**")
    st.info("""
    **🗺️ Map Controls:** Use the checkboxes above the map to toggle layers
    
    **Map Legend:**
    - 🟢 **Green dots**: Successful wells (high water yield)
    - 🔴 **Red dots**: Failed wells (low/no water)
    - 🔥 **Heatmap**: Probability zones (red=high probability, blue=low)
    - 🚜 **Colored areas**: Farm boundaries
    - 📐 **Blue areas**: Field boundaries
    
    **💧 Finding Optimal Drilling Locations:**
    
    1. **Look for clustering**: Bright red/orange heatmap areas with nearby successful wells
    2. **Avoid isolated failures**: Areas with many red dots indicate poor conditions
    3. **Check depth**: Most successful wells are 80-150m deep
    4. **Consider proximity**: Wells too close together compete for water
    5. **Seasonal timing**: Plan drilling for rainy season (May-October)
    
    **🎯 Best Discovery Zones:**
    - High heatmap intensity (red/orange)
    - Multiple successful wells nearby
    - Optimal depth range available
    - Good geological formation
    """)
    
    # Additional analysis
    with st.expander("📊 Success Rate Analysis"):
        if not filtered_wells.empty:
            success_rate = filtered_wells["survived"].mean()
            total_wells = len(filtered_wells)
            successful = filtered_wells["survived"].sum()
            failed = total_wells - successful
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Wells", total_wells)
            with col2:
                st.metric("Successful", successful)
            with col3:
                st.metric("Success Rate", f"{success_rate:.1%}")
            
            st.markdown(f"""
            **Analysis Summary:**
            - {successful} out of {total_wells} wells are successful
            - Success rate: {success_rate:.1%}
            - Failed wells: {failed}
            
            {'✅ Good success rate! This area shows promise.' if success_rate > 0.7 else '⚠️ Lower success rate. Consider careful site selection.'}
            """)
