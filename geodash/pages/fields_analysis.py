"""
Fields Analysis page - Comprehensive farm and field analysis with custom layout.
Updated to use 'average_yield' from field_data.csv instead of yield_probability.
"""
from typing import Dict, List, Optional
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import altair as alt


def calculate_farm_statistics(field_data_df: pd.DataFrame, farm_polygons: List[Dict]) -> pd.DataFrame:
    """
    Calculate statistics for each farm from field data.
    
    Args:
        field_data_df: DataFrame with field data
        farm_polygons: List of farm polygon dictionaries
        
    Returns:
        DataFrame with farm statistics
    """
    if field_data_df is None or field_data_df.empty:
        return pd.DataFrame()
    
    # Create a mapping of farm names
    farm_stats = []
    
    for farm in farm_polygons:
        farm_name = farm.get('name', 'Unknown')
        
        # For demo, calculate statistics from all fields
        # In production, you'd filter fields by farm
        stats = {
            'farm_name': farm_name,
            'total_fields': len(field_data_df),
            'total_area_rai': field_data_df['average_area'].sum() if 'average_area' in field_data_df.columns else 0,
            'avg_actual_yield': field_data_df['average_yield'].mean() if 'average_yield' in field_data_df.columns else 0,
            'total_additional_water_mm': field_data_df['average_additional_water(mm)'].sum() if 'average_additional_water(mm)' in field_data_df.columns else 0,
            'area_hectares': farm.get('area_hectares', 0),
            'area_rai': farm.get('area_rai', 0),
        }
        
        farm_stats.append(stats)
    
    return pd.DataFrame(farm_stats)


def render_farms_dashboard(farm_stats_df: pd.DataFrame) -> None:
    """
    Render the top dashboard showing overview of all farms.
    
    Args:
        farm_stats_df: DataFrame with farm statistics
    """
    st.markdown("## 🏞️ All Farms Overview")
    
    if farm_stats_df.empty:
        st.warning("No farm data available")
        return
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_farms = len(farm_stats_df)
        st.metric("Total Farms", total_farms)
    
    with col2:
        total_area = farm_stats_df['area_rai'].sum()
        st.metric("Total Area", f"{total_area:,.0f} rai")
    
    with col3:
        avg_yield = farm_stats_df['avg_actual_yield'].mean() if 'avg_actual_yield' in farm_stats_df.columns else 0
        st.metric("Avg Yield (3 yrs)", f"{avg_yield:.2f} t/rai")
    
    with col4:
        total_fields = farm_stats_df['total_fields'].sum()
        st.metric("Total Fields", f"{total_fields:,}")
    
    st.markdown("---")
    
    # Farm comparison charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("### 📊 Farm Area Comparison")
        
        if not farm_stats_df.empty:
            area_chart = (
                alt.Chart(farm_stats_df)
                .mark_bar(color='#4CAF50')
                .encode(
                    x=alt.X('farm_name:N', title='Farm Name', sort='-y'),
                    y=alt.Y('area_rai:Q', title='Area (rai)'),
                    tooltip=['farm_name:N', 'area_rai:Q', 'area_hectares:Q']
                )
                .properties(height=300)
            )
            st.altair_chart(area_chart, use_container_width=True)
    
    with col_chart2:
        st.markdown("### 🌾 Average Actual Yields (3 years) by Farm")
        
        if not farm_stats_df.empty and 'avg_actual_yield' in farm_stats_df.columns:
            yield_chart = (
                alt.Chart(farm_stats_df)
                .mark_bar()
                .encode(
                    x=alt.X('farm_name:N', title='Farm Name', sort='-y'),
                    y=alt.Y('avg_actual_yield:Q', title='Average Yield (tons/rai)'),
                    color=alt.Color('avg_actual_yield:Q', scale=alt.Scale(scheme='greens')),
                    tooltip=['farm_name:N', 'avg_actual_yield:Q', 'total_fields:Q']
                )
                .properties(height=300)
            )
            st.altair_chart(yield_chart, use_container_width=True)
    
    # Detailed farm statistics table
    with st.expander("📋 Detailed Farm Statistics"):
        display_df = farm_stats_df.copy()
        
        # Format columns for display
        formatted_data = []
        for _, row in display_df.iterrows():
            formatted_data.append({
                'Farm Name': row['farm_name'],
                'Total Fields': int(row['total_fields']),
                'Area (rai)': f"{row['area_rai']:,.2f}",
                'Area (ha)': f"{row['area_hectares']:,.2f}",
                'Avg Yield (t/rai)': f"{row['avg_actual_yield']:.2f}" if 'avg_actual_yield' in row else 'N/A',
                'Add. Water (mm)': f"{row['total_additional_water_mm']:,.1f}"
            })
        
        formatted_df = pd.DataFrame(formatted_data)
        st.dataframe(formatted_df, use_container_width=True)


def build_farm_map(
    selected_farm: Dict,
    field_polygons: List[Dict],
    field_data_df: pd.DataFrame
) -> Dict:
    """
    Build map showing only selected farm and its fields.
    
    Args:
        selected_farm: Selected farm polygon dictionary
        field_polygons: All field polygons
        field_data_df: DataFrame with field data
        
    Returns:
        Map state dictionary
    """
    # Calculate center of farm
    farm_coords = selected_farm.get('coordinates', [])
    if not farm_coords:
        center_lat, center_lon = 14.95, 99.62
    else:
        center_lat = sum(coord[0] for coord in farm_coords) / len(farm_coords)
        center_lon = sum(coord[1] for coord in farm_coords) / len(farm_coords)
    
    # Create map
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles="OpenStreetMap"
    )
    
    # Add farm boundary
    farm_coords_closed = farm_coords + [farm_coords[0]]
    folium.Polygon(
        locations=farm_coords_closed,
        color=selected_farm.get('color', '#FF6B6B'),
        weight=3,
        fill=True,
        fill_color=selected_farm.get('fill_color', selected_farm.get('color', '#FF6B6B')),
        fill_opacity=0.2,
        popup=folium.Popup(
            f"<b>🚜 {selected_farm['name']}</b><br>"
            f"Area: {selected_farm.get('area_rai', 0):.2f} rai<br>"
            f"Farm ID: {selected_farm.get('farm_id', 'N/A')}",
            max_width=250
        ),
        tooltip=f"🚜 {selected_farm['name']}"
    ).add_to(fmap)
    
    # Build field lookup
    field_lookup = {}
    if field_data_df is not None and not field_data_df.empty:
        try:
            fld = field_data_df.copy()
            fld['new_plot_code'] = fld['new_plot_code'].astype(str)
            field_lookup = {
                str(row['new_plot_code']): row
                for _, row in fld.iterrows()
            }
        except Exception:
            field_lookup = {}
    
    # Helper function for field colors based on actual yield
    def color_for_yield(yield_value: Optional[float]) -> tuple:
        """Color fields based on actual yield (tons/rai)"""
        if yield_value is None:
            return ("#bdbdbd", "#737373")  # Gray for no data
        
        try:
            y = float(yield_value)
        except Exception:
            return ("#bdbdbd", "#737373")
        
        # Sugarcane yield benchmarks (tons/rai):
        # Excellent: >10, Good: 8-10, Average: 6-8, Poor: <6
        if y >= 10.0:
            return ("#31a354", "#238b45")  # Dark green - Excellent
        elif y >= 8.0:
            return ("#a1d99b", "#74c476")  # Medium green - Good
        elif y >= 6.0:
            return ("#fc9272", "#de2d26")  # Orange-red - Average
        else:
            return ("#de2d26", "#a50f15")  # Red - Poor
    
    # Add field polygons
    for field_poly in field_polygons:
        field_coords = field_poly.get('coordinates', [])
        if not field_coords:
            continue
        
        field_coords_closed = field_coords + [field_coords[0]]
        plot_code = str(field_poly.get('plot_code', '')) if field_poly.get('plot_code') is not None else None
        row = field_lookup.get(plot_code) if plot_code else None
        
        # Get actual yield and colors
        if row is not None and 'average_yield' in row:
            try:
                actual_yield = float(row['average_yield'])
            except Exception:
                actual_yield = None
        else:
            actual_yield = None
        
        fill_color, outline_color = color_for_yield(actual_yield)
        
        # Build popup content
        popup_html = f"<b>📐 {field_poly['name']}</b><br>Region: {field_poly['region']}<br>"
        
        if row is not None:
            if 'average_yield' in row:
                popup_html += f"Actual Yield: {float(row['average_yield']):.2f} t/rai<br>"
            if 'average_area' in row:
                popup_html += f"Area: {float(row['average_area']):.2f} rai<br>"
            
            if 'average_additional_water(mm)' in row:
                add_water_mm = float(row['average_additional_water(mm)'])
                popup_html += f"Additional Water: {add_water_mm:.1f} mm<br>"
                
                # Calculate cubic meters
                if 'average_area' in row:
                    area_rai = float(row['average_area'])
                    add_water_m3 = area_rai * 1600.0 * (add_water_mm / 1000.0)
                    popup_html += f"Additional Water: {add_water_m3:,.0f} m³"
        else:
            popup_html += "Data: N/A"
        
        folium.Polygon(
            locations=field_coords_closed,
            color=outline_color,
            weight=2,
            fill=True,
            fill_color=fill_color,
            fill_opacity=0.6,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"📐 {field_poly['name']}"
        ).add_to(fmap)
    
    # Render map
    map_state = st_folium(fmap, width=None, height=600, returned_objects=["last_object_clicked"])
    
    return map_state or {}


def render_field_information(
    selected_farm: Dict,
    field_polygons: List[Dict],
    field_data_df: pd.DataFrame,
    map_state: Dict
) -> None:
    """
    Render field information panel on the right side.
    
    Args:
        selected_farm: Selected farm dictionary
        field_polygons: List of field polygons
        field_data_df: DataFrame with field data
        map_state: Current map state
    """
    st.markdown("### 📊 Field Information")
    
    # Farm summary
    st.markdown(f"**🚜 Farm: {selected_farm['name']}**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Farm Area", f"{selected_farm.get('area_rai', 0):.2f} rai")
    with col2:
        st.metric("Total Fields", len(field_polygons))
    
    st.markdown("---")
    
    # Check if a field was clicked
    clicked_field = None
    if map_state and 'last_object_clicked' in map_state and map_state['last_object_clicked']:
        click_lat = map_state['last_object_clicked'].get('lat')
        click_lon = map_state['last_object_clicked'].get('lng')
        
        if click_lat and click_lon:
            # Find which field was clicked
            for field in field_polygons:
                field_coords = field.get('coordinates', [])
                if _point_in_polygon(click_lat, click_lon, field_coords):
                    clicked_field = field
                    break
    
    # Display clicked field details or field list
    if clicked_field:
        st.markdown("### 📐 Selected Field Details")
        
        plot_code = clicked_field.get('plot_code')
        field_data = None
        
        if plot_code and field_data_df is not None and not field_data_df.empty:
            try:
                field_data_df['new_plot_code'] = field_data_df['new_plot_code'].astype(str)
                matching_rows = field_data_df[field_data_df['new_plot_code'] == str(plot_code)]
                if not matching_rows.empty:
                    field_data = matching_rows.iloc[0]
            except Exception:
                field_data = None
        
        st.markdown(f"**Field Name:** {clicked_field['name']}")
        st.markdown(f"**Region:** {clicked_field['region']}")
        
        if field_data is not None:
            st.markdown("---")
            st.markdown("**📊 Performance Metrics**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'average_yield' in field_data:
                    actual_yield = float(field_data['average_yield'])
                    st.metric("Actual Yield (3 yrs)", f"{actual_yield:.2f} t/rai")
                
                if 'average_area' in field_data:
                    area = float(field_data['average_area'])
                    st.metric("Area", f"{area:.2f} rai")
            
            with col2:
                if 'average_additional_water(mm)' in field_data:
                    add_water_mm = float(field_data['average_additional_water(mm)'])
                    st.metric("Add. Water", f"{add_water_mm:.1f} mm")
                    
                    # Calculate m³
                    if 'average_area' in field_data:
                        area_rai = float(field_data['average_area'])
                        add_water_m3 = area_rai * 1600.0 * (add_water_mm / 1000.0)
                        st.metric("Add. Water", f"{add_water_m3:,.0f} m³")
            
            # Yield performance indicator
            st.markdown("---")
            st.markdown("**🌾 Yield Assessment**")
            
            if 'average_yield' in field_data:
                actual_yield = float(field_data['average_yield'])
                
                # Sugarcane yield benchmarks (tons/rai)
                if actual_yield >= 10.0:
                    st.success(f"✅ Excellent Yield ({actual_yield:.2f} t/rai)")
                    st.caption("Above 10 t/rai - Outstanding performance")
                elif actual_yield >= 8.0:
                    st.info(f"📊 Good Yield ({actual_yield:.2f} t/rai)")
                    st.caption("8-10 t/rai - Above average")
                elif actual_yield >= 6.0:
                    st.warning(f"⚠️ Average Yield ({actual_yield:.2f} t/rai)")
                    st.caption("6-8 t/rai - Room for improvement")
                else:
                    st.error(f"❌ Low Yield ({actual_yield:.2f} t/rai)")
                    st.caption("Below 6 t/rai - Needs attention")
        else:
            st.info("No detailed data available for this field")
    else:
        st.info("👆 Click on a field polygon in the map to view details")
        
        # Show summary of all fields
        st.markdown("---")
        st.markdown("### 📋 All Fields Summary")
        
        if field_data_df is not None and not field_data_df.empty:
            summary_stats = {
                'Total Fields': len(field_polygons),
                'Total Area (rai)': field_data_df['average_area'].sum() if 'average_area' in field_data_df.columns else 0,
                'Avg Actual Yield (t/rai)': field_data_df['average_yield'].mean() if 'average_yield' in field_data_df.columns else 0,
            }
            
            for key, value in summary_stats.items():
                if 'Yield' in key:
                    st.markdown(f"**{key}:** {value:.2f}")
                else:
                    st.markdown(f"**{key}:** {value:,.0f}")
            
            # Field list
            with st.expander("📄 Field List"):
                for i, field in enumerate(field_polygons, 1):
                    st.markdown(f"{i}. {field['name']} ({field['region']})")


def _point_in_polygon(lat: float, lon: float, polygon_coords: List[List[float]]) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.
    
    Args:
        lat: Point latitude
        lon: Point longitude
        polygon_coords: List of [lat, lon] coordinates
        
    Returns:
        True if point is inside polygon
    """
    x, y = lon, lat
    n = len(polygon_coords)
    inside = False
    
    p1x, p1y = polygon_coords[0][1], polygon_coords[0][0]  # lon, lat
    for i in range(1, n + 1):
        p2x, p2y = polygon_coords[i % n][1], polygon_coords[i % n][0]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside


def render_fields_analysis(data: Dict) -> None:
    """
    Main render function for Fields Analysis page.
    
    Args:
        data: Complete dashboard data
    """
    # Extract data
    farm_polygons = data.get('farm_polygons', [])
    field_polygons = data.get('polygons', [])
    field_data_df = data.get('field_data_df')
    
    if not farm_polygons:
        st.warning("⚠️ No farm data available. Please ensure farm polygons are loaded.")
        return
    
    # Calculate farm statistics
    farm_stats_df = calculate_farm_statistics(field_data_df, farm_polygons)
    
    # === TOP DASHBOARD ===
    render_farms_dashboard(farm_stats_df)
    
    st.markdown("---")
    st.markdown("---")
    
    # === INDIVIDUAL FARM ANALYSIS ===
    st.markdown("## 🔍 Individual Farm Analysis")
    
    # Farm selector
    farm_names = [farm['name'] for farm in farm_polygons]
    selected_farm_name = st.selectbox(
        "Select Farm",
        options=farm_names,
        index=0
    )
    
    # Get selected farm
    selected_farm = next((f for f in farm_polygons if f['name'] == selected_farm_name), None)
    
    if not selected_farm:
        st.error("❌ Selected farm not found")
        return
    
    st.markdown("---")
    
    # === TWO COLUMN LAYOUT ===
    col_map, col_info = st.columns([2, 1])
    
    with col_map:
        st.markdown("### 🗺️ Farm Map")
        map_state = build_farm_map(selected_farm, field_polygons, field_data_df)
    
    with col_info:
        render_field_information(selected_farm, field_polygons, field_data_df, map_state)
    
    # === MAP LEGEND ===
    st.markdown("---")
    st.markdown("### 🎨 Map Legend - Actual Yield Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("🟢 **Excellent** (≥10 t/rai)")
    with col2:
        st.markdown("🟡 **Good** (8-10 t/rai)")
    with col3:
        st.markdown("🟠 **Average** (6-8 t/rai)")
    with col4:
        st.markdown("🔴 **Poor** (<6 t/rai)")