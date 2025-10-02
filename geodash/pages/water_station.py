"""
Water Station page for survival rate analysis.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Optional

from geodash.data.data_loaders.water_stations_loader import WaterStationsLoader


def render_water_station_page() -> None:
    """Render the water station analysis page."""
    st.title("🏭 Water Station Analysis")
    st.markdown("Analyze survival rates of water stations from 2010-2025")
    
    # Initialize loader
    loader = WaterStationsLoader()
    
    # Load data
    with st.spinner("Loading water station data..."):
        data = loader.load_data()
    
    stations_df = data["stations_df"]
    survival_years = data["survival_years"]
    stations_summary = data["stations_summary"]
    
    if stations_df.empty:
        st.error("❌ No water station data available")
        return
    
    # Display summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Stations", stations_summary.get('total_stations', 0))
    with col2:
        st.metric("Total Wells", stations_summary.get('total_wells', 0))
    with col3:
        year_range = stations_summary.get('year_range', {})
        if year_range.get('start') and year_range.get('end'):
            st.metric("Data Range", f"{year_range['start']}-{year_range['end']}")
        else:
            st.metric("Data Range", "N/A")
    with col4:
        provinces = stations_summary.get('provinces', [])
        st.metric("Provinces", len(provinces))
    
    st.markdown("---")
    
    # Create two columns for layout
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.markdown("### 🎛️ Station Selection")
        
        # Station selection
        station_options = stations_df['station_id'].unique().tolist() if 'station_id' in stations_df.columns else []
        selected_station = st.selectbox(
            "Select Station (หมายเลขสถานี)",
            options=station_options,
            index=0 if station_options else None,
            help="Choose a water station to analyze"
        )
        
        # Well selection (based on selected station)
        well_options = []
        if selected_station and 'well_number' in stations_df.columns:
            station_wells = stations_df[stations_df['station_id'] == selected_station]['well_number'].unique()
            well_options = ['All Wells'] + station_wells.tolist()
        
        selected_well = st.selectbox(
            "Select Well (หมายเลขบ่อ)",
            options=well_options,
            index=0 if well_options else None,
            help="Choose a specific well or view all wells for the station"
        )
        
        # Display station information
        if selected_station:
            station_info = stations_df[stations_df['station_id'] == selected_station].iloc[0]
            
            st.markdown("### 📍 Station Information")
            st.markdown(f"**Station ID:** {selected_station}")
            st.markdown(f"**Location:** {station_info.get('location', 'Unknown')}")
            st.markdown(f"**Province:** {station_info.get('province', 'Unknown')}")
            st.markdown(f"**District:** {station_info.get('district', 'Unknown')}")
            
            if 'latitude' in station_info and 'longitude' in station_info:
                st.markdown(f"**Coordinates:** {station_info['latitude']:.4f}, {station_info['longitude']:.4f}")
            
            # Show wells count for this station
            wells_count = len(stations_df[stations_df['station_id'] == selected_station])
            st.markdown(f"**Wells at Station:** {wells_count}")
    
    with col_right:
        if selected_station and survival_years:
            st.markdown("### 📊 Survival Rate Analysis")
            
            # Get survival data for charting
            well_param = None if selected_well == 'All Wells' else selected_well
            chart_data = loader.get_survival_data_for_chart(selected_station, well_param)
            
            if "error" in chart_data:
                st.error(f"❌ {chart_data['error']}")
            elif chart_data["years"] and chart_data["survival_rates"]:
                # Create the survival rate chart
                fig = create_survival_rate_chart(chart_data, selected_station, selected_well)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display statistics
                st.markdown("### 📈 Statistics")
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                
                survival_rates = chart_data["survival_rates"]
                with col_stat1:
                    st.metric("Average Survival Rate", f"{sum(survival_rates)/len(survival_rates):.2%}")
                with col_stat2:
                    st.metric("Highest Rate", f"{max(survival_rates):.2%}")
                with col_stat3:
                    st.metric("Lowest Rate", f"{min(survival_rates):.2%}")
                
                # Show trend
                if len(survival_rates) >= 2:
                    trend = survival_rates[-1] - survival_rates[0]
                    trend_icon = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"
                    st.markdown(f"**Trend (2010-2024):** {trend_icon} {trend:+.2%}")
                
                # Display data table
                with st.expander("📋 View Raw Data"):
                    data_df = pd.DataFrame({
                        'Year': chart_data["years"],
                        'Survival Rate': [f"{rate:.2%}" for rate in chart_data["survival_rates"]]
                    })
                    st.dataframe(data_df, use_container_width=True)
            else:
                st.warning("⚠️ No survival data available for the selected station/well combination")
        else:
            st.info("👈 Please select a station to view survival rate analysis")
    
    # Overall survival trends
    st.markdown("---")
    st.markdown("### 🌍 Overall Survival Trends")
    
    if survival_years and stations_summary.get('avg_survival_by_year'):
        avg_survival_by_year = stations_summary['avg_survival_by_year']
        
        # Create overall trend chart
        overall_fig = go.Figure()
        overall_fig.add_trace(go.Scatter(
            x=list(avg_survival_by_year.keys()),
            y=list(avg_survival_by_year.values()),
            mode='lines+markers',
            name='Average Survival Rate',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8)
        ))
        
        overall_fig.update_layout(
            title="Average Survival Rate Across All Stations",
            xaxis_title="Year",
            yaxis_title="Survival Rate",
            yaxis=dict(tickformat='.1%'),
            template='plotly_white',
            height=400
        )
        
        st.plotly_chart(overall_fig, use_container_width=True)


def create_survival_rate_chart(chart_data: Dict[str, Any], station_id: str, well_number: str) -> go.Figure:
    """Create a survival rate chart for the selected station/well."""
    years = chart_data["years"]
    survival_rates = chart_data["survival_rates"]
    
    # Create the plot
    fig = go.Figure()
    
    # Add line plot
    fig.add_trace(go.Scatter(
        x=years,
        y=survival_rates,
        mode='lines+markers',
        name='Survival Rate',
        line=dict(color='#2E86C1', width=3),
        marker=dict(size=8, color='#2E86C1'),
        hovertemplate='<b>Year:</b> %{x}<br><b>Survival Rate:</b> %{y:.2%}<extra></extra>'
    ))
    
    # Add trend line if we have enough data points
    if len(years) >= 3:
        import numpy as np
        # Simple linear regression for trend line
        x_vals = np.array(years)
        y_vals = np.array(survival_rates)
        z = np.polyfit(x_vals, y_vals, 1)
        p = np.poly1d(z)
        
        fig.add_trace(go.Scatter(
            x=years,
            y=p(x_vals),
            mode='lines',
            name='Trend',
            line=dict(color='red', width=2, dash='dash'),
            hovertemplate='<b>Trend Line</b><extra></extra>'
        ))
    
    # Update layout
    title = f"Survival Rate - Station {station_id}"
    if well_number and well_number != 'All Wells':
        title += f" (Well {well_number})"
    
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Survival Rate",
        yaxis=dict(tickformat='.1%', range=[0, 1.1]),
        template='plotly_white',
        height=500,
        showlegend=True
    )
    
    return fig
