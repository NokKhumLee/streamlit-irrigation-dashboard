# app.py - Updated to use in-map filter controls
from typing import Optional

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

from geodash.data import load_dashboard_data, sidebar_filters, filter_wells
from geodash.ui import (
    # Choose one of these approaches:
    build_map_with_controls,     # Approach 1: Checkboxes above map
    # build_map_with_floating_controls,  # Approach 2: Floating expander
    # build_map_with_button_bar,  # Approach 3: Toggle buttons
    chart_ground_water_analytics,
    chart_survival_rate,
    chart_probability_by_depth,
    chart_cost_estimation,
    metadata_panel,
    download_button,
)
from geodash.plugins import PluginRegistry
from geodash.plugins.examples import NotesPlugin


def initialize_page_config() -> None:
    st.set_page_config(
        page_title="Badan (บาดาล)",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def main() -> None:
    initialize_page_config()
    
    # Sidebar with option menu
    with st.sidebar:
        selected = option_menu(
            menu_title="Badan (บาดาล)",
            options=[
                "Main",
                "Water Survival Analysis", 
                "Underground Water Discovery",
                "AI Assistant"
            ],
            icons=['house', 'droplet', 'search', 'robot'],
            menu_icon="globe",
            default_index=0,
        )
        
        st.markdown("---")
        
        # Load data
        data = load_dashboard_data()
        
        # SIMPLIFIED SIDEBAR - Remove map layer controls since they're now in the map
        st.sidebar.header("Data Filters")
        search_q = st.sidebar.text_input("Search Well/Polygon ID")
        region = st.sidebar.selectbox("Region", options=["All"] + sorted(data["wells_df"]["region"].unique().tolist()))
        min_depth, max_depth = int(data["wells_df"]["depth_m"].min()), int(data["wells_df"]["depth_m"].max())
        depth_range = st.sidebar.slider("Depth range (m)", min_value=min_depth, max_value=max_depth, value=(min_depth, max_depth), step=5)
        
        # Create filters dict
        filters = {
            "search_q": search_q, 
            "region": region, 
            "depth_range": depth_range,
        }
        
        st.markdown("---")
        st.markdown(
            """
            <div style="font-size: 0.8em; color: #6c757d; line-height: 1.5;">
                <span>🌍 <em>Geological Dashboard</em></span><br>
                📊 Interactive Well Analysis<br>
                💧 Water Resource Management<br>
                🎛️ Map controls moved to map area<br>
                🗓️ 2025<br>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.title(f"🔍 {selected}")

    col_map, col_dash = st.columns([2, 1])

    # Common filtered wells for all pages
    filtered_wells = filter_wells(data["wells_df"], filters)

    # State passed between columns
    selected_well_id: Optional[str] = None
    selected_row = None
    map_state = None

    with col_map:
        # Build map with in-map controls
        # Default layer settings based on current page
        if selected == "Main":
            default_layers = {"show_polygons": True, "show_farms": True, "show_wells": True, "show_heatmap": False}
        elif selected == "Water Survival Analysis":
            default_layers = {"show_polygons": False, "show_farms": True, "show_wells": True, "show_heatmap": False}
        elif selected == "Underground Water Discovery":
            default_layers = {"show_polygons": True, "show_farms": True, "show_wells": True, "show_heatmap": True}
        elif selected == "AI Assistant":
            default_layers = {"show_polygons": True, "show_farms": False, "show_wells": False, "show_heatmap": False}
        else:
            default_layers = {"show_polygons": True, "show_farms": True, "show_wells": True, "show_heatmap": False}
        
        # Use the new map function with in-map controls
        map_state = build_map_with_controls(
            data["polygons"],
            data["farm_polygons"],
            filtered_wells,
            data["heat_points"],
            current_filters=default_layers,
        )

    with col_dash:
        st.subheader("Dashboard")

        # Selection via text input
        if selected != "AI Assistant":
            manual_well_id = st.text_input("Well ID")
            if manual_well_id:
                if manual_well_id in data["wells_df"]["well_id"].values:
                    selected_well_id = manual_well_id
                else:
                    st.warning("Well ID not found.")

        # Nearest well to last map click as a fallback selection
        if selected_well_id is None and isinstance(map_state, dict):
            last_click = map_state.get("last_object_clicked")
            if isinstance(last_click, dict):
                lat = last_click.get("lat")
                lng = last_click.get("lng")
                if lat is not None and lng is not None and not data["wells_df"].empty:
                    df = data["wells_df"].copy()
                    df["dist"] = (
                        (df["lat"] - float(lat)) ** 2 + (df["lon"] - float(lng)) ** 2
                    )
                    nearest = df.nsmallest(1, "dist")
                    if not nearest.empty and nearest.iloc[0]["dist"] < 0.0005:
                        selected_well_id = str(nearest.iloc[0]["well_id"])

        # Selected row
        if selected_well_id is not None:
            match = data["wells_df"][data["wells_df"]["well_id"] == selected_well_id]
            if not match.empty:
                selected_row = match.iloc[0]

        # Show current layer status (optional)
        if isinstance(map_state, dict) and "layer_settings" in map_state:
            layers = map_state["layer_settings"]
            active_layers = sum(layers.values())
            st.caption(f"🗺️ Map: {active_layers}/4 layers active")

        # Per-page dashboards (unchanged)
        if selected == "Main":
            avg_depth = int(filtered_wells["depth_m"].mean()) if not filtered_wells.empty else 0
            st.metric("Average Depth", f"{avg_depth}m")
            
            if data["farm_polygons"]:
                st.metric("Total Farms", len(data["farm_polygons"]))
            
            st.markdown("**Metadata**")
            metadata_panel(selected_row)
            st.markdown("**Cost Estimation (by depth)**")
            chart_cost_estimation(data["cost_df"])
            download_button(filtered_wells)

        elif selected == "Water Survival Analysis":
            st.markdown("**Ground Water Analytics**")
            chart_ground_water_analytics(data["water_levels"], selected_well_id)
            st.markdown("**Survival Rate**")
            chart_survival_rate(filtered_wells)
            st.markdown("**Metadata**")
            metadata_panel(selected_row)

        elif selected == "Underground Water Discovery":
            st.markdown("**Ground Water Discovery**")
            chart_probability_by_depth(data["prob_df"])
            st.markdown("**Metadata**")
            metadata_panel(selected_row)
            st.markdown("**💡 Discovery Tips**")
            st.info("""
            🗺️ **Map Controls:** Use the checkboxes above the map to toggle layers
            
            **Map Legend:**
            - 🟢 Green dots: Successful wells
            - 🔴 Red dots: Failed wells  
            - 🔥 Heatmap: Probability zones (red=high, blue=low)
            - 🚜 Colored areas: Farm boundaries
            - 📐 Blue areas: Field boundaries
            
            💧 **Best Discovery Zones:**
            Look for bright red/orange heatmap areas with nearby successful wells.
            """)

        elif selected == "AI Assistant":
            st.markdown("**Assistant**")
            user_msg = st.chat_input("Ask about geology or wells…")
            if user_msg:
                st.chat_message("user").write(user_msg)
                st.chat_message("assistant").write("This is a placeholder response.")
            registry = PluginRegistry()
            registry.register(NotesPlugin())
            registry.render_all()


if __name__ == "__main__":
    main()