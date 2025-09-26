from typing import Dict, List

import folium
from folium.plugins import HeatMap
import streamlit as st
from streamlit_folium import st_folium
import pandas as pd


def build_map(
    polygons: List[Dict[str, object]],
    farm_polygons: List[Dict[str, object]],  # NEW: farm polygons parameter
    wells_df: pd.DataFrame,
    heat_points: List[List[float]],
    *,
    show_layer_toggles: bool = True,
    default_show_polygons: bool = True,
    default_show_farms: bool = True,  # NEW: farm polygons toggle
    default_show_wells: bool = True,
    default_show_heatmap: bool = False,
) -> Dict[str, object]:
    if show_layer_toggles:
        show_polygons = st.checkbox("Show Field Polygons", value=default_show_polygons)
        show_farms = st.checkbox("Show Farm Polygons", value=default_show_farms)  # NEW
        show_wells = st.checkbox("Show Wells", value=default_show_wells)
        show_heatmap = st.checkbox("Show Probability Heatmap", value=default_show_heatmap)
    else:
        show_polygons = default_show_polygons
        show_farms = default_show_farms  # NEW
        show_wells = default_show_wells
        show_heatmap = default_show_heatmap

    center_lat = float(wells_df["lat"].mean()) if not wells_df.empty else 15.95
    center_lon = float(wells_df["lon"].mean()) if not wells_df.empty else 100.1

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

    # Farm polygons layer (rendered first, underneath field polygons)
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
                tooltip=f"🚜 {farm_poly['name']} (Farm ID: {farm_poly.get('farm_id', 'N/A')})",
                popup=folium.Popup(
                    f"<b>🚜 {farm_poly['name']}</b><br>Farm ID: {farm_poly.get('farm_id', 'N/A')}<br>Type: Farm Boundary",
                    max_width=250
                ),
            ).add_to(fmap)

    # Field polygons layer (rendered on top of farm polygons)
    if show_polygons:
        for poly in polygons:
            coords = poly["coordinates"] + [poly["coordinates"][0]]
            folium.Polygon(
                locations=coords,
                color="#2c7fb8",
                weight=1,  # Thinner lines for field polygons to distinguish from farms
                fill=True,
                fill_color="#a6bddb",
                fill_opacity=0.2,  # Lower opacity for field polygons
                tooltip=f"📐 {poly['name']} ({poly['region']})",
                popup=folium.Popup(
                    f"<b>📐 {poly['name']}</b><br>Region: {poly['region']}<br>Type: Field Boundary",
                    max_width=250
                ),
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