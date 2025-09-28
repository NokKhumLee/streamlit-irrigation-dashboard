# app.py - Updated to use farm-based time series
from typing import Optional

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

from geodash.data import load_dashboard_data, filter_wells
from geodash.data.rain_service import get_rain_service
from geodash.ui import (
    build_map_with_controls,
    chart_farm_survival_analytics,  # Updated function name
    chart_region_comparison,        # New function
    chart_seasonal_analysis,        # New function
    chart_survival_rate,
    chart_probability_by_depth,
    chart_cost_estimation,
    chart_rain_statistics,
    chart_rain_frequency,
    metadata_panel,
    download_button,
)
from geodash.plugins import PluginRegistry
from geodash.plugins.examples import NotesPlugin


def _point_in_polygon(lat: float, lon: float, polygon_coords: list) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.
    """
    x, y = lon, lat
    n = len(polygon_coords)
    inside = False
    
    p1x, p1y = polygon_coords[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon_coords[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside


def _get_polygon_center(polygon_coords: list) -> tuple:
    """
    Get the center point of a polygon.
    """
    if not polygon_coords:
        return 0.0, 0.0
    
    lats = [coord[0] for coord in polygon_coords]
    lons = [coord[1] for coord in polygon_coords]
    
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    return center_lat, center_lon


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
        
        # NEW: Farm/Region selection for time series analysis
        if selected == "Water Survival Analysis":
            st.sidebar.header("Farm Analysis")
            available_regions = ["All"] + sorted(data["farm_time_series"]["region"].unique().tolist()) if not data["farm_time_series"].empty else ["All"]
            selected_farm_region = st.sidebar.selectbox("Select Farm/Region for Analysis", options=available_regions)
            if selected_farm_region == "All":
                selected_farm_region = None
        else:
            selected_farm_region = None
        
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
                🚜 Farm-based Time Series<br>
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
    selected_farm_coordinates = None
    rain_data = None
    rain_stats = None

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

        # Handle map clicks for wells and farms
        if isinstance(map_state, dict):
            last_click = map_state.get("last_object_clicked")
            farm_polygons = map_state.get("farm_polygons", [])
            
            if isinstance(last_click, dict):
                lat = last_click.get("lat")
                lng = last_click.get("lng")
                
                if lat is not None and lng is not None:
                    # Check if click is on a farm polygon
                    clicked_farm = None
                    for farm in farm_polygons:
                        # Try point-in-polygon first
                        if _point_in_polygon(float(lat), float(lng), farm["coordinates"]):
                            clicked_farm = farm
                            break
                        
                        # Fallback: check if click is close to farm center (within 0.01 degrees ≈ 1km)
                        center_lat, center_lon = _get_polygon_center(farm["coordinates"])
                        distance = ((float(lat) - center_lat) ** 2 + (float(lng) - center_lon) ** 2) ** 0.5
                        
                        if distance < 0.01:  # Within ~1km
                            clicked_farm = farm
                            break
                    
                    if clicked_farm:
                        # Farm clicked - get rain data
                        selected_farm_coordinates = clicked_farm["coordinates"]
                        rain_service = get_rain_service()
                        
                        if rain_service.client is not None:
                            center_lat, center_lon = rain_service.get_farm_center_coordinates(selected_farm_coordinates)
                            
                            with st.spinner("Fetching rain data..."):
                                rain_data = rain_service.get_rain_data(center_lat, center_lon, days_back=365)
                                if rain_data is not None:
                                    rain_stats = rain_service.get_rain_statistics(rain_data)
                        else:
                            st.warning("Rain data service is not available. Please install required packages: openmeteo-requests, requests-cache, retry-requests")
                    
                    # Check for nearest well if no farm clicked
                    elif not data["wells_df"].empty:
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

        # Per-page dashboards
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
            # Show rain data if farm is selected
            if selected_farm_coordinates is not None and rain_data is not None:
                st.markdown("**🌧️ Rain Statistics (1 Year)**")
                st.success("✅ Rain data loaded for selected farm location")
                chart_rain_statistics(rain_data, rain_stats)
                st.markdown("---")
            
            # NEW: Farm-based time series analysis
            st.markdown("**🚜 Farm Survival Analytics**")
            chart_farm_survival_analytics(data["farm_time_series"], selected_farm_region)
            
            # Show regional comparison if no specific region selected
            if selected_farm_region is None:
                st.markdown("**📊 Regional Comparison**")
                chart_region_comparison(data["farm_time_series"])
                
                st.markdown("**🌿 Seasonal Analysis**")
                chart_seasonal_analysis(data["farm_time_series"])
            
            st.markdown("**Overall Well Success Rate**")
            chart_survival_rate(filtered_wells)
            
            st.markdown("**Metadata**")
            metadata_panel(selected_row)
            
            # Instructions
            if selected_farm_coordinates is None:
                st.info("💡 **Tips:**\n- Click on a farm polygon to view rain statistics\n- Select a specific region in the sidebar for detailed time series analysis")

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