# geodash/ui/map_panel.py
from typing import Dict, List

import folium
from folium.plugins import HeatMap
import streamlit as st
from streamlit_folium import st_folium
import pandas as pd


def build_map_with_controls(
    polygons: List[Dict[str, object]],
    farm_polygons: List[Dict[str, object]],
    wells_df: pd.DataFrame,
    heat_points: List[List[float]],
    current_filters: Dict[str, object],
) -> Dict[str, object]:
    """
    Build interactive map with dropdown filter controls.
    """
    
    # === MAP TITLE AND DROPDOWN CONTROLS ===
    st.markdown("### 🗺️ Interactive Map")
    
    # Dropdown panel for map layer controls
    with st.expander("🎛️ Map Layer Controls", expanded=False):
        # Create columns for controls inside the expander
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            show_polygons = st.checkbox("🏞️ Fields", value=current_filters.get("show_polygons", True), key="map_polygons")
        with col2:
            show_farms = st.checkbox("🚜 Farms", value=current_filters.get("show_farms", True), key="map_farms")
        with col3:
            show_wells = st.checkbox("🏔️ Wells", value=current_filters.get("show_wells", True), key="map_wells")
        with col4:
            show_heatmap = st.checkbox("💧 Groundwater", value=current_filters.get("show_heatmap", False), key="map_heatmap")
    
    # Small separator
    st.markdown("---")
    
    # === BUILD MAP ===
    center_lat = float(wells_df["lat"].mean()) if not wells_df.empty else 15.95
    center_lon = float(wells_df["lon"].mean()) if not wells_df.empty else 100.1

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

    # Farm polygons layer
    if show_farms and farm_polygons:
        for i, farm_poly in enumerate(farm_polygons):
            coords = farm_poly["coordinates"] + [farm_poly["coordinates"][0]]
            farm_id = farm_poly.get('farm_id', f'farm_{i}')
            
            folium.Polygon(
                locations=coords,
                color=farm_poly.get("color", "#FF6B6B"),
                weight=farm_poly.get("weight", 2),
                fill=True,
                fill_color=farm_poly.get("fill_color", farm_poly.get("color", "#FF6B6B")),
                fill_opacity=farm_poly.get("fill_opacity", 0.3),
                tooltip=f"🚜 {farm_poly['name']} (Farm ID: {farm_id})",
                popup=folium.Popup(
                    f"<b>🚜 {farm_poly['name']}</b><br>Farm ID: {farm_id}<br>Type: Farm Boundary<br>Click to view rain data",
                    max_width=250
                ),
            ).add_to(fmap)

    # Field polygons layer
    if show_polygons:
        for poly in polygons:
            coords = poly["coordinates"] + [poly["coordinates"][0]]
            folium.Polygon(
                locations=coords,
                color="#2c7fb8",
                weight=1,
                fill=True,
                fill_color="#a6bddb",
                fill_opacity=0.2,
                tooltip=f"📐 {poly['name']} ({poly['region']})",
                popup=folium.Popup(
                    f"<b>📐 {poly['name']}</b><br>Region: {poly['region']}<br>Type: Field Boundary",
                    max_width=250
                ),
            ).add_to(fmap)

    # Wells layer
    if show_wells and not wells_df.empty:
        for _, r in wells_df.iterrows():
            popup_html = (
                f"<b>{r['well_id']}</b><br>Region: {r['region']}<br>"
                f"Depth: {int(r['depth_m'])} m<br>Survival: {'Yes' if r['survived'] else 'No'}"
            )
            folium.CircleMarker(
                location=[float(r["lat"]), float(r["lon"])],
                radius=1,
                color="#238b45" if r["survived"] else "#cb181d",
                fill=True,
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=r["well_id"],
            ).add_to(fmap)

    # Heatmap layer
    if show_heatmap and heat_points:
        HeatMap(heat_points, radius=18, blur=22, min_opacity=0.3).add_to(fmap)

    # Render map
    map_state = st_folium(fmap, width=None, height=600, returned_objects=["last_object_clicked"])
    
    # Return both map state and current layer settings
    return {
        **(map_state or {}),
        "layer_settings": {
            "show_polygons": show_polygons,
            "show_farms": show_farms,
            "show_wells": show_wells,
            "show_heatmap": show_heatmap,
        },
        "farm_polygons": farm_polygons if show_farms else []
    }


def build_map_with_floating_controls(
    polygons: List[Dict[str, object]],
    farm_polygons: List[Dict[str, object]],
    wells_df: pd.DataFrame,
    heat_points: List[List[float]],
    current_filters: Dict[str, object],
) -> Dict[str, object]:
    """
    Alternative approach: Floating control panel over the map.
    """
    
    # Create a container for the map with overlay controls
    map_container = st.container()
    
    with map_container:
        # Title and toggle for controls
        col_title, col_toggle = st.columns([3, 1])
        
        with col_title:
            st.markdown("### 🗺️ Interactive Map")
        with col_toggle:
            show_controls = st.checkbox("🎛️ Controls", value=False, key="show_floating_controls")
        
        # Floating controls (only show if enabled)
        if show_controls:
            controls_col, _, _ = st.columns([1, 2, 1])
            
            with controls_col:
                with st.expander("🎛️ Map Controls", expanded=True):
                    show_polygons = st.checkbox("Field Polygons", value=current_filters.get("show_polygons", True))
                    show_farms = st.checkbox("Farm Polygons", value=current_filters.get("show_farms", True))
                    show_wells = st.checkbox("Wells", value=current_filters.get("show_wells", True))
                    show_heatmap = st.checkbox("Groundwater Probability", value=current_filters.get("show_heatmap", False))
                    
                    # Quick actions
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("🌍 Show All"):
                            show_polygons = show_farms = show_wells = show_heatmap = True
                            st.rerun()
                    with col_b:
                        if st.button("🔄 Clear All"):
                            show_polygons = show_farms = show_wells = show_heatmap = False
                            st.rerun()
        else:
            # Use default values when controls are hidden
            show_polygons = current_filters.get("show_polygons", True)
            show_farms = current_filters.get("show_farms", True)
            show_wells = current_filters.get("show_wells", True)
            show_heatmap = current_filters.get("show_heatmap", False)
        
        # Build the map
        center_lat = float(wells_df["lat"].mean()) if not wells_df.empty else 15.95
        center_lon = float(wells_df["lon"].mean()) if not wells_df.empty else 100.1

        fmap = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

        # Add layers based on controls
        if show_farms and farm_polygons:
            for farm_poly in farm_polygons:
                coords = farm_poly["coordinates"] + [farm_poly["coordinates"][0]]
                folium.Polygon(
                    locations=coords,
                    color=farm_poly.get("color", "#FF6B6B"),
                    weight=farm_poly.get("weight", 2),
                    fill=True,
                    fill_color=farm_poly.get("fill_color", farm_poly.get("color", "#FF6B6B")),
                    fill_opacity=farm_poly.get("fill_opacity", 0.3),
                    tooltip=f"🚜 {farm_poly['name']}",
                ).add_to(fmap)

        if show_polygons:
            for poly in polygons:
                coords = poly["coordinates"] + [poly["coordinates"][0]]
                folium.Polygon(
                    locations=coords,
                    color="#2c7fb8",
                    weight=1,
                    fill=True,
                    fill_color="#a6bddb",
                    fill_opacity=0.2,
                    tooltip=f"📐 {poly['name']}",
                ).add_to(fmap)

        if show_wells and not wells_df.empty:
            for _, r in wells_df.iterrows():
                folium.CircleMarker(
                    location=[float(r["lat"]), float(r["lon"])],
                    radius=1,
                    color="#238b45" if r["survived"] else "#cb181d",
                    fill=True,
                    fill_opacity=0.8,
                    tooltip=r["well_id"],
                ).add_to(fmap)

        if show_heatmap and heat_points:
            HeatMap(heat_points, radius=18, blur=22, min_opacity=0.3).add_to(fmap)

        map_state = st_folium(fmap, width=None, height=650, returned_objects=["last_object_clicked"])
        
        return {
            **(map_state or {}),
            "layer_settings": {
                "show_polygons": show_polygons,
                "show_farms": show_farms,
                "show_wells": show_wells,
                "show_heatmap": show_heatmap,
            }
        }


def build_map_with_button_bar(
    polygons: List[Dict[str, object]],
    farm_polygons: List[Dict[str, object]],
    wells_df: pd.DataFrame,
    heat_points: List[List[float]],
    current_filters: Dict[str, object],
) -> Dict[str, object]:
    """
    Third approach: Button bar above the map for quick toggles.
    """
    
    # Title and controls toggle
    col_title, col_toggle = st.columns([3, 1])
    
    with col_title:
        st.markdown("### 🗺️ Interactive Map")
    with col_toggle:
        show_button_controls = st.checkbox("🎛️ Show Controls", value=True, key="show_button_controls")
    
    if show_button_controls:
        # Button bar for quick toggles
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 2])
        
        # Toggle buttons (using session state to maintain state)
        if "map_layers" not in st.session_state:
            st.session_state.map_layers = {
                "polygons": current_filters.get("show_polygons", True),
                "farms": current_filters.get("show_farms", True),
                "wells": current_filters.get("show_wells", True),
                "heatmap": current_filters.get("show_heatmap", False),
            }
        
        with col1:
            if st.button("🏞️ Fields", type="primary" if st.session_state.map_layers["polygons"] else "secondary"):
                st.session_state.map_layers["polygons"] = not st.session_state.map_layers["polygons"]
                st.rerun()
        
        with col2:
            if st.button("🚜 Farms", type="primary" if st.session_state.map_layers["farms"] else "secondary"):
                st.session_state.map_layers["farms"] = not st.session_state.map_layers["farms"]
                st.rerun()
        
        with col3:
            if st.button("🏔️ Wells", type="primary" if st.session_state.map_layers["wells"] else "secondary"):
                st.session_state.map_layers["wells"] = not st.session_state.map_layers["wells"]
                st.rerun()
        
        with col4:
            if st.button("💧 Prob", type="primary" if st.session_state.map_layers["heatmap"] else "secondary"):
                st.session_state.map_layers["heatmap"] = not st.session_state.map_layers["heatmap"]
                st.rerun()
        
        with col5:
            if st.button("🌍 All"):
                st.session_state.map_layers = {"polygons": True, "farms": True, "wells": True, "heatmap": True}
                st.rerun()
        
        with col6:
            # Map info
            active_layers = sum(st.session_state.map_layers.values())
            st.caption(f"📊 {active_layers}/4 layers active")
        
        # Build map with current layer states
        show_polygons = st.session_state.map_layers["polygons"]
        show_farms = st.session_state.map_layers["farms"]
        show_wells = st.session_state.map_layers["wells"]
        show_heatmap = st.session_state.map_layers["heatmap"]
    else:
        # Use default values when controls are hidden
        if "map_layers" not in st.session_state:
            st.session_state.map_layers = {
                "polygons": current_filters.get("show_polygons", True),
                "farms": current_filters.get("show_farms", True),
                "wells": current_filters.get("show_wells", True),
                "heatmap": current_filters.get("show_heatmap", False),
            }
        
        show_polygons = st.session_state.map_layers["polygons"]
        show_farms = st.session_state.map_layers["farms"]
        show_wells = st.session_state.map_layers["wells"]
        show_heatmap = st.session_state.map_layers["heatmap"]
    
    # Map building logic
    center_lat = float(wells_df["lat"].mean()) if not wells_df.empty else 15.95
    center_lon = float(wells_df["lon"].mean()) if not wells_df.empty else 100.1

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

    # Add layers
    if show_farms and farm_polygons:
        for farm_poly in farm_polygons:
            coords = farm_poly["coordinates"] + [farm_poly["coordinates"][0]]
            folium.Polygon(
                locations=coords,
                color=farm_poly.get("color", "#FF6B6B"),
                weight=farm_poly.get("weight", 2),
                fill=True,
                fill_color=farm_poly.get("fill_color", farm_poly.get("color", "#FF6B6B")),
                fill_opacity=farm_poly.get("fill_opacity", 0.3),
                tooltip=f"🚜 {farm_poly['name']}",
            ).add_to(fmap)

    if show_polygons:
        for poly in polygons:
            coords = poly["coordinates"] + [poly["coordinates"][0]]
            folium.Polygon(
                locations=coords,
                color="#2c7fb8",
                weight=1,
                fill=True,
                fill_color="#a6bddb",
                fill_opacity=0.2,
                tooltip=f"📐 {poly['name']}",
            ).add_to(fmap)

    if show_wells and not wells_df.empty:
        for _, r in wells_df.iterrows():
            folium.CircleMarker(
                location=[float(r["lat"]), float(r["lon"])],
                radius=1,
                color="#238b45" if r["survived"] else "#cb181d",
                fill=True,
                fill_opacity=0.8,
                tooltip=r["well_id"],
            ).add_to(fmap)

    if show_heatmap and heat_points:
        HeatMap(heat_points, radius=18, blur=22, min_opacity=0.3).add_to(fmap)

    map_state = st_folium(fmap, width=None, height=600, returned_objects=["last_object_clicked"])
    
    return {
        **(map_state or {}),
        "layer_settings": st.session_state.map_layers
    }


# Keep the original function for backward compatibility
def build_map(
    polygons: List[Dict[str, object]],
    farm_polygons: List[Dict[str, object]],
    wells_df: pd.DataFrame,
    heat_points: List[List[float]],
    show_polygons: bool = True,
    show_farms: bool = True,
    show_wells: bool = True,
    show_heatmap: bool = False,
) -> Dict[str, object]:
    """Original build_map function for backward compatibility."""
    
    center_lat = float(wells_df["lat"].mean()) if not wells_df.empty else 15.95
    center_lon = float(wells_df["lon"].mean()) if not wells_df.empty else 100.1

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

    if show_farms and farm_polygons:
        for farm_poly in farm_polygons:
            coords = farm_poly["coordinates"] + [farm_poly["coordinates"][0]]
            folium.Polygon(
                locations=coords,
                color=farm_poly.get("color", "#FF6B6B"),
                weight=farm_poly.get("weight", 2),
                fill=True,
                fill_color=farm_poly.get("fill_color", farm_poly.get("color", "#FF6B6B")),
                fill_opacity=farm_poly.get("fill_opacity", 0.3),
                tooltip=f"🚜 {farm_poly['name']}",
            ).add_to(fmap)

    if show_polygons:
        for poly in polygons:
            coords = poly["coordinates"] + [poly["coordinates"][0]]
            folium.Polygon(
                locations=coords,
                color="#2c7fb8",
                weight=1,
                fill=True,
                fill_color="#a6bddb",
                fill_opacity=0.2,
                tooltip=f"📐 {poly['name']}",
            ).add_to(fmap)

    if show_wells and not wells_df.empty:
        for _, r in wells_df.iterrows():
            popup_html = (
                f"<b>{r['well_id']}</b><br>Region: {r['region']}<br>"
                f"Depth: {int(r['depth_m'])} m<br>Survival: {'Yes' if r['survived'] else 'No'}"
            )
            folium.CircleMarker(
                location=[float(r["lat"]), float(r["lon"])],
                radius=1,
                color="#238b45" if r["survived"] else "#cb181d",
                fill=True,
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=r["well_id"],
            ).add_to(fmap)

    if show_heatmap and heat_points:
        HeatMap(heat_points, radius=18, blur=22, min_opacity=0.3).add_to(fmap)

    map_state = st_folium(fmap, width=None, height=700, returned_objects=["last_object_clicked"])
    return map_state or {}