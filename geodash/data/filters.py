# geodash/data/filters.py
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
    
    # NEW: Map Layer Controls
    st.sidebar.header("Map Layers")
    show_polygons = st.sidebar.checkbox("Show Field Polygons", value=True)
    show_farms = st.sidebar.checkbox("Show Farm Polygons", value=True)
    show_wells = st.sidebar.checkbox("Show Wells", value=True)
    show_heatmap = st.sidebar.checkbox("Show Probability Heatmap", value=False)
    
    return {
        "search_q": search_q, 
        "region": region, 
        "depth_range": depth_range,
        # NEW: Map layer toggles
        "show_polygons": show_polygons,
        "show_farms": show_farms,
        "show_wells": show_wells,
        "show_heatmap": show_heatmap,
    }


def filter_wells(wells_df: pd.DataFrame, filters: Dict[str, object]) -> pd.DataFrame:
    df = wells_df.copy()
    if filters["region"] != "All":
        df = df[df["region"] == filters["region"]]
    dmin, dmax = filters["depth_range"]
    df = df[(df["depth_m"] >= dmin) & (df["depth_m"] <= dmax)]
    if filters["search_q"]:
        q = str(filters["search_q"]).strip().lower()
        df = df[df["well_id"].str.lower().str.contains(q)]
    return df