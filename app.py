from typing import Optional

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

from geodash.data import generate_mock_data, sidebar_filters, filter_wells
from geodash.ui import (
    build_map,
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
        page_title="Water Budddy",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded",  # Changed to expanded to show the option menu
    )


def main() -> None:
    initialize_page_config()
    
    # Sidebar with option menu
    with st.sidebar:
        selected = option_menu(
            menu_title="Water Buddy",
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
        
        # Generate data and filters
        data = generate_mock_data()
        filters = sidebar_filters(data["wells_df"])
        
        st.markdown("---")
        st.markdown(
            """
            <div style="font-size: 0.8em; color: #6c757d; line-height: 1.5;">
                <span>🌍 <em>Geological Dashboard</em></span><br>
                📊 Interactive Well Analysis<br>
                💧 Water Resource Management<br>
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
        st.subheader("Map")
        if selected == "Main":
            # Show polygons and wells; no heatmap by default
            map_state = build_map(
                data["polygons"],
                filtered_wells,
                data["heat_points"],
                show_layer_toggles=True,
                default_show_polygons=True,
                default_show_wells=True,
                default_show_heatmap=False,
            )
        elif selected == "Water Survival Analysis":
            # Focus on wells; polygons optional
            map_state = build_map(
                data["polygons"],
                filtered_wells,
                data["heat_points"],
                show_layer_toggles=True,
                default_show_polygons=False,
                default_show_wells=True,
                default_show_heatmap=False,
            )
        elif selected == "Underground Water Discovery":
            # Focus on heatmap; hide wells/polygons by default
            map_state = build_map(
                data["polygons"],
                filtered_wells,
                data["heat_points"],
                show_layer_toggles=True,
                default_show_polygons=False,
                default_show_wells=False,
                default_show_heatmap=True,
            )
        elif selected == "AI Assistant":
            # Minimal map; allow toggles
            map_state = build_map(
                data["polygons"],
                filtered_wells,
                data["heat_points"],
                show_layer_toggles=True,
                default_show_polygons=True,
                default_show_wells=False,
                default_show_heatmap=False,
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

        # Per-page dashboards
        if selected == "Main":
            avg_depth = int(filtered_wells["depth_m"].mean()) if not filtered_wells.empty else 0
            st.metric("Average Depth", f"{avg_depth}m")
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