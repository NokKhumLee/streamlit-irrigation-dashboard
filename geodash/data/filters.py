from typing import Dict

import pandas as pd
import streamlit as st


def sidebar_filters(wells_df: pd.DataFrame) -> Dict[str, object]:
    st.sidebar.header("Filters")
    search_q = st.sidebar.text_input("Search Well/Polygon ID")
    region = st.sidebar.selectbox("Region", options=["All"] + sorted(wells_df["region"].unique().tolist()))
    min_depth, max_depth = int(wells_df["depth_m"].min()), int(wells_df["depth_m"].max())
    depth_range = st.sidebar.slider("Depth range (m)", min_value=min_depth, max_value=max_depth, value=(min_depth, max_depth), step=5)
    return {"search_q": search_q, "region": region, "depth_range": depth_range}


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



