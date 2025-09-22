from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st


def chart_ground_water_analytics(water_levels: pd.DataFrame, selected_well: Optional[str]) -> None:
    if selected_well is None:
        st.info("Select a well (via map click or search) to view time series.")
        return
    df = water_levels[water_levels["well_id"] == selected_well]
    line = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(x="date:T", y=alt.Y("water_level_m:Q", title="Water level (m)"))
        .properties(height=200)
    )
    st.altair_chart(line, use_container_width=True)


def chart_survival_rate(wells_df: pd.DataFrame) -> None:
    counts = wells_df["survived"].value_counts().rename(index={True: "Success", False: "Failure"}).reset_index()
    counts.columns = ["status", "count"]
    pie = alt.Chart(counts).mark_arc(innerRadius=40).encode(theta="count:Q", color="status:N")
    st.altair_chart(pie, use_container_width=True)


def chart_probability_by_depth(prob_df: pd.DataFrame) -> None:
    bars = alt.Chart(prob_df).mark_bar().encode(x="depth_m:O", y=alt.Y("probability:Q", axis=alt.Axis(format=".0%")))
    st.altair_chart(bars, use_container_width=True)


def chart_cost_estimation(cost_df: pd.DataFrame) -> None:
    bars = alt.Chart(cost_df).mark_bar().encode(x="depth_m:O", y=alt.Y("estimated_cost_thb:Q", title="Estimated cost (THB)"))
    st.altair_chart(bars, use_container_width=True)



