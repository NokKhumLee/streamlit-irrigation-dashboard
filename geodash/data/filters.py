# geodash/data/filters.py - Updated with distance to farm filter
from typing import Dict

import pandas as pd
import streamlit as st


def sidebar_filters(wells_df: pd.DataFrame) -> Dict[str, object]:
    st.sidebar.header("Filters")
    
    # Existing filters
    search_q = st.sidebar.text_input("Search Well/Polygon ID")
    region = st.sidebar.selectbox("Region", options=["All"] + sorted(wells_df["region"].unique().tolist()))
    min_depth, max_depth = int(wells_df["depth_m"].min()), int(wells_df["depth_m"].max())
    depth_range = st.sidebar.slider("Depth range (m)", min_value=min_depth, max_value=max_depth, value=(min_depth, max_depth), step=5)
    
    # NEW: Distance to Farm Filter
    st.sidebar.subheader("🏚️ Distance to Farm")
    
    if 'distance_to_farm' in wells_df.columns and not wells_df.empty:
        min_distance = int(wells_df["distance_to_farm"].min())
        actual_max_distance = int(wells_df["distance_to_farm"].max())
        
        # Set maximum to 30km, regardless of actual data max
        max_distance = 30000  # Always cap at 30km
        
        # Default to 10km (10,000m)
        default_max_distance = 10000
        
        distance_range = st.sidebar.slider(
            "Max distance to farm (m)", 
            min_value=min_distance, 
            max_value=max_distance, 
            value=default_max_distance, 
            step=500,
            help="Filter wells by maximum distance to nearest farm (default: 10km, max: 30km)"
        )
        
        # Show distance in km for better readability
        st.sidebar.caption(f"Current filter: ≤ {distance_range/1000:.1f} km")
        
        # Show how many wells are within common distances (based on actual data)
        if not wells_df.empty:
            within_1km = (wells_df["distance_to_farm"] <= 1000).sum()
            within_5km = (wells_df["distance_to_farm"] <= 5000).sum()
            within_10km = (wells_df["distance_to_farm"] <= 10000).sum()
            within_20km = (wells_df["distance_to_farm"] <= 20000).sum()
            within_30km = (wells_df["distance_to_farm"] <= 30000).sum()
            
            st.sidebar.caption(f"""
            📊 **Wells by distance:**
            • Within 1km: {within_1km:,}
            • Within 5km: {within_5km:,} 
            • Within 10km: {within_10km:,}
            • Within 20km: {within_20km:,}
            • Within 30km: {within_30km:,}
            • Total available: {len(wells_df):,}
            • Actual max: {actual_max_distance/1000:.1f}km
            """)
    else:
        distance_range = 10000  # Default 10km
        st.sidebar.info("Distance data not available")
    
    # Map Layer Controls
    st.sidebar.header("Map Layers")
    show_polygons = st.sidebar.checkbox("Show Field Polygons", value=True)
    show_farms = st.sidebar.checkbox("Show Farm Polygons", value=True)
    show_wells = st.sidebar.checkbox("Show Wells", value=True)
    show_heatmap = st.sidebar.checkbox("Show Probability Heatmap", value=False)
    
    return {
        "search_q": search_q, 
        "region": region, 
        "depth_range": depth_range,
        "distance_range": distance_range,  # NEW: Distance filter
        # Map layer toggles
        "show_polygons": show_polygons,
        "show_farms": show_farms,
        "show_wells": show_wells,
        "show_heatmap": show_heatmap,
    }


def filter_wells(wells_df: pd.DataFrame, filters: Dict[str, object]) -> pd.DataFrame:
    """
    Filter wells based on all available criteria including distance to farm.
    
    Args:
        wells_df: DataFrame with wells data
        filters: Dictionary of filter criteria
        
    Returns:
        Filtered DataFrame
    """
    df = wells_df.copy()
    
    # Region filter
    if filters["region"] != "All":
        df = df[df["region"] == filters["region"]]
    
    # Depth filter
    dmin, dmax = filters["depth_range"]
    df = df[(df["depth_m"] >= dmin) & (df["depth_m"] <= dmax)]
    
    # Search filter
    if filters["search_q"]:
        q = str(filters["search_q"]).strip().lower()
        df = df[df["well_id"].str.lower().str.contains(q)]
    
    # NEW: Distance to farm filter
    if "distance_range" in filters and "distance_to_farm" in df.columns:
        max_distance = filters["distance_range"]
        df = df[df["distance_to_farm"] <= max_distance]
    
    return df


def get_filter_summary(wells_df: pd.DataFrame, filtered_df: pd.DataFrame, filters: Dict[str, object]) -> str:
    """
    Generate a summary of applied filters and their effects.
    
    Args:
        wells_df: Original wells DataFrame
        filtered_df: Filtered wells DataFrame  
        filters: Applied filters
        
    Returns:
        Formatted summary string
    """
    if wells_df.empty:
        return "No data available"
    
    original_count = len(wells_df)
    filtered_count = len(filtered_df)
    removed_count = original_count - filtered_count
    
    summary_parts = [
        f"**📊 Filter Results:**",
        f"• Original wells: {original_count:,}",
        f"• After filtering: {filtered_count:,}",
        f"• Removed: {removed_count:,} ({100*removed_count/original_count:.1f}%)"
    ]
    
    # Add active filter details
    active_filters = []
    
    if filters.get("region") != "All":
        active_filters.append(f"Region: {filters['region']}")
    
    if filters.get("search_q"):
        active_filters.append(f"Search: '{filters['search_q']}'")
    
    dmin, dmax = filters.get("depth_range", (0, 0))
    if dmin > wells_df["depth_m"].min() or dmax < wells_df["depth_m"].max():
        active_filters.append(f"Depth: {dmin}-{dmax}m")
    
    if "distance_range" in filters and "distance_to_farm" in wells_df.columns:
        max_dist_km = filters["distance_range"] / 1000
        active_filters.append(f"Distance to farm: ≤{max_dist_km:.1f}km")
    
    if active_filters:
        summary_parts.append(f"**🎛️ Active Filters:** {', '.join(active_filters)}")
    else:
        summary_parts.append("**🎛️ Active Filters:** None")
    
    return "\n\n".join(summary_parts)


def display_distance_statistics(wells_df: pd.DataFrame) -> None:
    """
    Display distance to farm statistics.
    
    Args:
        wells_df: DataFrame with distance_to_farm column
    """
    if wells_df.empty or 'distance_to_farm' not in wells_df.columns:
        st.info("Distance to farm data not available")
        return
    
    st.subheader("🏚️ Distance to Farm Statistics")
    
    # Basic statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        min_dist = wells_df['distance_to_farm'].min()
        st.metric("Minimum", f"{min_dist:.0f}m")
    
    with col2:
        max_dist = wells_df['distance_to_farm'].max() 
        st.metric("Maximum", f"{max_dist/1000:.1f}km")
    
    with col3:
        avg_dist = wells_df['distance_to_farm'].mean()
        st.metric("Average", f"{avg_dist/1000:.1f}km")
    
    with col4:
        median_dist = wells_df['distance_to_farm'].median()
        st.metric("Median", f"{median_dist/1000:.1f}km")
    
    # Distribution by distance ranges
    st.subheader("📊 Distribution by Distance")
    
    ranges = [
        ("0-1km", 0, 1000),
        ("1-5km", 1000, 5000), 
        ("5-10km", 5000, 10000),
        ("10-20km", 10000, 20000),
        ("20-30km", 20000, 30000),
        (">30km", 30000, float('inf'))
    ]
    
    range_data = []
    for label, min_dist, max_dist in ranges:
        if max_dist == float('inf'):
            count = (wells_df['distance_to_farm'] > min_dist).sum()
        else:
            count = ((wells_df['distance_to_farm'] > min_dist) & 
                    (wells_df['distance_to_farm'] <= max_dist)).sum()
        
        percentage = 100 * count / len(wells_df) if len(wells_df) > 0 else 0
        range_data.append({
            'Range': label,
            'Count': count,
            'Percentage': f"{percentage:.1f}%"
        })
    
    range_df = pd.DataFrame(range_data)
    st.dataframe(range_df, use_container_width=True)


# Enhanced filter presets for common use cases
def get_filter_presets() -> Dict[str, Dict[str, object]]:
    """
    Get predefined filter presets for common analysis scenarios.
    
    Returns:
        Dictionary of preset configurations
    """
    return {
        "All Wells": {
            "region": "All",
            "search_q": "",
            "depth_range": None,  # Will be set to full range
            "distance_range": 30000,  # 30km - maximum range
        },
        "Near Farms Only": {
            "region": "All", 
            "search_q": "",
            "depth_range": None,
            "distance_range": 5000,  # 5km
        },
        "Optimal Depth Near Farms": {
            "region": "All",
            "search_q": "",
            "depth_range": (80, 150),  # Optimal depth range
            "distance_range": 10000,  # 10km
        },
        "Very Close to Farms": {
            "region": "All",
            "search_q": "",
            "depth_range": None,
            "distance_range": 1000,  # 1km
        },
        "Medium Distance": {
            "region": "All",
            "search_q": "",
            "depth_range": None,
            "distance_range": 15000,  # 15km
        },
        "Far from Farms": {
            "region": "All",
            "search_q": "",
            "depth_range": None,
            "distance_range": 25000,  # 25km
        }
    }


def apply_filter_preset(wells_df: pd.DataFrame, preset_name: str) -> Dict[str, object]:
    """
    Apply a predefined filter preset.
    
    Args:
        wells_df: Wells DataFrame to determine ranges
        preset_name: Name of preset to apply
        
    Returns:
        Filter configuration dictionary
    """
    presets = get_filter_presets()
    
    if preset_name not in presets:
        return sidebar_filters(wells_df)  # Return default filters
    
    preset = presets[preset_name].copy()
    
    # Set depth range to full range if None
    if preset["depth_range"] is None and not wells_df.empty:
        preset["depth_range"] = (int(wells_df["depth_m"].min()), int(wells_df["depth_m"].max()))
    
    return preset