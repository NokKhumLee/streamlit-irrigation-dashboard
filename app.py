"""
Badan (บาดาล) - Geological Dashboard
Main application file with distance-to-farm filtering.
"""
from typing import Optional
import streamlit as st
from streamlit_option_menu import option_menu

from geodash.data import load_dashboard_data, filter_wells
from geodash.data.rain_service import get_rain_service
from geodash.ui import build_map_with_controls

# Import page renderers
from geodash.pages import (
    render_main_dashboard,
    render_water_survival,
    render_discovery,
    render_ai_assistant,
)


def initialize_page_config() -> None:
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Badan (บาดาล)",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def _point_in_polygon(lat: float, lon: float, polygon_coords: list) -> bool:
    """Check if point is inside polygon (ray casting algorithm)."""
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
    """Get center point of polygon."""
    if not polygon_coords:
        return 0.0, 0.0
    
    lats = [coord[0] for coord in polygon_coords]
    lons = [coord[1] for coord in polygon_coords]
    
    return sum(lats) / len(lats), sum(lons) / len(lons)


def main() -> None:
    """Main application entry point."""
    initialize_page_config()
    
    # Sidebar navigation
    with st.sidebar:
        selected = option_menu(
            menu_title="Badan (บาดาล)",
            options=["Main", "Water Survival Analysis", "Underground Water Discovery", "AI Assistant"],
            icons=['house', 'droplet', 'search', 'robot'],
            menu_icon="globe",
            default_index=0,
        )
        
        st.markdown("---")
        
        # Load data WITHOUT distance filter (load all wells, filter in UI)
        if 'data' not in st.session_state:
            st.session_state.data = load_dashboard_data(max_distance_to_farm_m=None)
        
        data = st.session_state.data
        
        # Sidebar filters
        st.sidebar.header("Data Filters")
        
        # Search filter
        search_q = st.sidebar.text_input("Search Well/Polygon ID")
        
        # Region filter
        region = st.sidebar.selectbox(
            "Region", 
            options=["All"] + sorted(data["wells_df"]["region"].unique().tolist())
        )
        
        # Depth filter
        min_depth, max_depth = int(data["wells_df"]["depth_m"].min()), int(data["wells_df"]["depth_m"].max())
        depth_range = st.sidebar.slider(
            "Depth range (m)", 
            min_value=min_depth, 
            max_value=max_depth, 
            value=(min_depth, max_depth), 
            step=5
        )
        
        # NEW: Distance to Farm Filter
        st.sidebar.subheader("🏚️ Distance to Farm")
        
        if 'distance_to_farm' in data["wells_df"].columns and not data["wells_df"].empty:
            min_distance_m = int(data["wells_df"]["distance_to_farm"].min())
            actual_max_distance_m = int(data["wells_df"]["distance_to_farm"].max())
            
            # Convert to kilometers for the slider
            min_distance_km = min_distance_m / 1000
            max_distance_km = 30.0  # 30km maximum
            default_distance_km = 10.0  # 10km default
            
            distance_range_km = st.sidebar.slider(
                "Max distance to farm (km)", 
                min_value=min_distance_km, 
                max_value=max_distance_km, 
                value=default_distance_km, 
                step=0.5,
                help="Filter wells by maximum distance to nearest farm"
            )
            
            # Convert back to meters for internal use
            distance_range = int(distance_range_km * 1000)
            
            # Show wells matching current filter
            wells_in_filter = (data["wells_df"]["distance_to_farm"] <= distance_range).sum()
            st.sidebar.caption(f"📊 Wells within {distance_range_km:.1f}km: **{wells_in_filter:,}**")
        else:
            distance_range = 10000  # Default 10km in meters
            st.sidebar.info("Distance data not available")
        
        # Farm selection for Water Survival page
        if selected == "Water Survival Analysis":
            st.sidebar.header("Farm Analysis")
            available_regions = ["All"] + sorted(data["farm_time_series"]["region"].unique().tolist()) if not data["farm_time_series"].empty else ["All"]
            selected_farm_region = st.sidebar.selectbox("Select Farm/Region", options=available_regions)
            selected_farm_region = None if selected_farm_region == "All" else selected_farm_region
        else:
            selected_farm_region = None
        
        # Build filters dictionary
        filters = {
            "search_q": search_q, 
            "region": region, 
            "depth_range": depth_range,
            "distance_range": distance_range
        }
        
        st.markdown("---")
        st.markdown("""
        <div style="font-size: 0.8em; color: #6c757d;">
            🌍 Geological Dashboard<br>
            📊 Interactive Analysis<br>
            💧 Water Management<br>
            🗓️ 2025
        </div>
        """, unsafe_allow_html=True)
    
    # Page title
    st.title(f"🔍 {selected}")
    
    # Layout: Map | Dashboard
    col_map, col_dash = st.columns([2, 1])
    
    # Filter wells
    filtered_wells = filter_wells(data["wells_df"], filters)
    
    # State variables
    selected_well_id: Optional[str] = None
    selected_row = None
    map_state = None
    selected_farm_coordinates = None
    rain_data = None
    rain_stats = None
    
    # Build map
    with col_map:
        # Default layer settings per page
        default_layers = {
            "Main": {"show_polygons": True, "show_farms": True, "show_wells": True, "show_heatmap": False},
            "Water Survival Analysis": {"show_polygons": False, "show_farms": True, "show_wells": True, "show_heatmap": False},
            "Underground Water Discovery": {"show_polygons": True, "show_farms": True, "show_wells": True, "show_heatmap": True},
            "AI Assistant": {"show_polygons": True, "show_farms": False, "show_wells": False, "show_heatmap": False},
        }
        
        map_state = build_map_with_controls(
            data["polygons"],
            data["farm_polygons"],
            filtered_wells,
            data["heat_points"],
            current_filters=default_layers.get(selected, {}),
        )
    
    # Dashboard content
    with col_dash:
        st.subheader("Dashboard")
        
        # Show filter summary
        original_count = len(data["wells_df"])
        filtered_count = len(filtered_wells)
        if filtered_count < original_count:
            removed = original_count - filtered_count
            st.info(f"**Filtered:** {filtered_count:,} / {original_count:,} wells ({removed:,} removed)")
        
        # Well selection
        if selected != "AI Assistant":
            manual_well_id = st.text_input("Well ID")
            if manual_well_id and manual_well_id in data["wells_df"]["well_id"].values:
                selected_well_id = manual_well_id
        
        # Handle map clicks
        if isinstance(map_state, dict):
            last_click = map_state.get("last_object_clicked")
            farm_polygons = map_state.get("farm_polygons", [])
            
            if isinstance(last_click, dict):
                lat, lng = last_click.get("lat"), last_click.get("lng")
                
                if lat and lng:
                    # Check farm click
                    for farm in farm_polygons:
                        if _point_in_polygon(float(lat), float(lng), farm["coordinates"]):
                            selected_farm_coordinates = farm["coordinates"]
                            rain_service = get_rain_service()
                            
                            if rain_service.client:
                                center_lat, center_lon = rain_service.get_farm_center_coordinates(selected_farm_coordinates)
                                with st.spinner("Fetching rain data..."):
                                    rain_data = rain_service.get_rain_data(center_lat, center_lon, days_back=365)
                                    if rain_data is not None:
                                        rain_stats = rain_service.get_rain_statistics(rain_data)
                            break
                    
                    # Check well click
                    if not selected_farm_coordinates and not data["wells_df"].empty:
                        df = data["wells_df"].copy()
                        df["dist"] = (df["lat"] - float(lat)) ** 2 + (df["lon"] - float(lng)) ** 2
                        nearest = df.nsmallest(1, "dist")
                        if not nearest.empty and nearest.iloc[0]["dist"] < 0.0005:
                            selected_well_id = str(nearest.iloc[0]["well_id"])
        
        # Get selected row
        if selected_well_id:
            match = data["wells_df"][data["wells_df"]["well_id"] == selected_well_id]
            if not match.empty:
                selected_row = match.iloc[0]
        
        # Render page-specific content
        if selected == "Main":
            render_main_dashboard(data, filtered_wells, map_state, selected_row)
        
        elif selected == "Water Survival Analysis":
            render_water_survival(
                data, filtered_wells, map_state, selected_row,
                selected_farm_region, selected_farm_coordinates, rain_data, rain_stats
            )
        
        elif selected == "Underground Water Discovery":
            render_discovery(data, filtered_wells, map_state, selected_row)
        
        elif selected == "AI Assistant":
            render_ai_assistant(data)


if __name__ == "__main__":
    main()