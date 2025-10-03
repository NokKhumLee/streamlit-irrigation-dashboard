"""
Enhanced Underground Water Discovery page - With potential drilling suggestions.
"""
from typing import Dict, Optional
import pandas as pd
import streamlit as st
import altair as alt

from geodash.ui import (
    build_map_with_controls,
    chart_probability_by_depth,
    metadata_panel,
)


def render_discovery(
    data: Dict,
    filtered_wells: pd.DataFrame,
    map_state: Dict,
    selected_row: Optional[pd.Series]
) -> None:
    """
    Render the underground water discovery page with potential well suggestions.
    """
    
    st.markdown("**🔍 Ground Water Discovery Probability**")
    chart_probability_by_depth(data["prob_df"])
    
    st.markdown("---")
    
    # === DEPTH FILTER FOR POTENTIAL WELLS ===
    st.markdown("### 💡 Potential Drilling Locations")
    
    potential_wells_df = data.get("potential_wells_df", pd.DataFrame())
    
    if not potential_wells_df.empty:
        col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
        
        with col_filter1:
            show_shallow = st.checkbox("Shallow (<60m)", value=True, key="show_shallow")
        with col_filter2:
            show_medium = st.checkbox("Medium (60-80m)", value=True, key="show_medium")
        with col_filter3:
            show_deep = st.checkbox("Deep (>80m)", value=True, key="show_deep")
        with col_filter4:
            num_display = st.number_input("Show top N", min_value=5, max_value=50, value=15, step=5)
        
        # Filter by depth category
        filtered_potential = potential_wells_df.copy()
        depth_filters = []
        if show_shallow:
            depth_filters.append('shallow')
        if show_medium:
            depth_filters.append('medium')
        if show_deep:
            depth_filters.append('deep')
        
        if depth_filters:
            filtered_potential = filtered_potential[
                filtered_potential['depth_category'].isin(depth_filters)
            ]
        
        filtered_potential = filtered_potential.head(num_display)
        
        # === SUMMARY METRICS ===
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Potential Locations", len(filtered_potential))
        with col2:
            avg_prob = filtered_potential['success_probability'].mean()
            st.metric("Avg Success Rate", f"{avg_prob:.0%}")
        with col3:
            avg_yield = filtered_potential['expected_water_yield_m3h'].mean()
            st.metric("Avg Exp. Yield", f"{avg_yield:.1f} m³/h")
        with col4:
            total_cost = filtered_potential['estimated_cost_thb'].sum() / 1_000_000
            st.metric("Total Investment", f"฿{total_cost:.1f}M")
        
        st.markdown("---")
        
        # === PRIORITY FIELDS ANALYSIS ===
        st.markdown("### 🎯 Priority Fields (Water Demand Gap)")
        
        demand_gap_df = data.get("demand_gap_df", pd.DataFrame())
        
        if not demand_gap_df.empty:
            # Show top 5 priority fields
            priority_fields = demand_gap_df[demand_gap_df['water_gap_m3_day'] > 0].head(5)
            
            if not priority_fields.empty:
                for idx, field in priority_fields.iterrows():
                    with st.expander(
                        f"{'🔴' if field['priority_level'] == 'Critical' else '🟡' if field['priority_level'] == 'High' else '🔵'} "
                        f"{field['field_name']} - {field['priority_level']} Priority "
                        f"({field['gap_percentage']:.0f}% gap)",
                        expanded=(idx == priority_fields.index[0])
                    ):
                        col_info1, col_info2, col_info3 = st.columns(3)
                        
                        with col_info1:
                            st.markdown("**Current Situation**")
                            st.markdown(f"• Area: **{field['area_rai']:.1f}** rai")
                            st.markdown(f"• Daily Demand: **{field['water_demand_m3_day']:.0f}** m³")
                            st.markdown(f"• Current Supply: **{field['current_supply_m3_day']:.0f}** m³")
                            st.markdown(f"• **Gap: {field['water_gap_m3_day']:.0f} m³/day** ({field['gap_percentage']:.0f}%)")
                        
                        with col_info2:
                            st.markdown("**Existing Infrastructure**")
                            st.markdown(f"• Wells within 5km: **{field['existing_wells_nearby']}**")
                            st.markdown(f"• Successful wells: **{field['successful_wells_nearby']}**")
                            st.markdown(f"• Available potential sites: **{field['potential_wells_available']}**")
                        
                        with col_info3:
                            st.markdown("**After Drilling Potential Wells**")
                            st.markdown(f"• Additional supply: **{field['potential_additional_supply_m3_day']:.0f}** m³/day")
                            st.markdown(f"• Remaining gap: **{field['gap_after_drilling']:.0f}** m³/day")
                            coverage = (1 - field['gap_after_drilling'] / field['water_gap_m3_day']) * 100 if field['water_gap_m3_day'] > 0 else 0
                            st.markdown(f"• Gap coverage: **{coverage:.0f}%**")
                        
                        # Show recommended wells for this field
                        field_wells = filtered_potential[
                            filtered_potential['field_name'] == field['field_name']
                        ]
                        
                        if not field_wells.empty:
                            st.markdown("**💡 Recommended Drilling Locations:**")
                            
                            for _, well in field_wells.iterrows():
                                col_w1, col_w2, col_w3, col_w4 = st.columns([2, 2, 2, 2])
                                
                                with col_w1:
                                    st.markdown(f"**{well['potential_id']}**")
                                    st.caption(f"Depth: {well['recommended_depth_m']}m")
                                
                                with col_w2:
                                    st.markdown(f"**{well['success_probability']:.0%}** success")
                                    st.caption(f"{well['expected_water_yield_m3h']:.1f} m³/h yield")
                                
                                with col_w3:
                                    st.markdown(f"**฿{well['estimated_cost_thb']:,}**")
                                    st.caption(f"Drilling: ฿{well['drilling_cost_thb']:,}")
                                
                                with col_w4:
                                    # Calculate ROI
                                    daily_supply = well['expected_water_yield_m3h'] * 8
                                    months_to_payback = (well['estimated_cost_thb'] / (daily_supply * 30 * 50)) if daily_supply > 0 else 999
                                    st.markdown(f"**Score: {well['priority_score']:.2f}**")
                                    st.caption(f"~{months_to_payback:.0f} months ROI")
            else:
                st.success("✅ All fields have adequate water supply!")
        
        st.markdown("---")
        
        # === DETAILED POTENTIAL WELLS TABLE ===
        st.markdown("### 📋 All Potential Drilling Locations")
        
        # Create display dataframe
        display_df = filtered_potential.copy()
        display_df['Success Rate'] = display_df['success_probability'].apply(lambda x: f"{x:.0%}")
        display_df['Exp. Yield'] = display_df['expected_water_yield_m3h'].apply(lambda x: f"{x:.1f} m³/h")
        display_df['Total Cost'] = display_df['estimated_cost_thb'].apply(lambda x: f"฿{x:,}")
        display_df['Priority'] = display_df['priority_score']
        
        # Select columns for display
        display_cols = [
            'potential_id', 'field_name', 'region', 'recommended_depth_m',
            'depth_category', 'Success Rate', 'Exp. Yield', 'Total Cost', 'Priority'
        ]
        
        display_df = display_df[display_cols]
        display_df.columns = [
            'ID', 'Field', 'Region', 'Depth (m)', 'Category',
            'Success Rate', 'Expected Yield', 'Est. Cost', 'Priority Score'
        ]
        
        # Show dataframe
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )
        
        # === DOWNLOAD BUTTON ===
        csv = filtered_potential.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Potential Wells Data (CSV)",
            data=csv,
            file_name="potential_drilling_locations.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        
        # === DEPTH DISTRIBUTION CHART ===
        st.markdown("### 📊 Depth Distribution of Potential Wells")
        
        depth_counts = filtered_potential['depth_category'].value_counts().reset_index()
        depth_counts.columns = ['Category', 'Count']
        
        # Map categories to readable labels
        category_map = {
            'shallow': 'Shallow (<60m)',
            'medium': 'Medium (60-80m)',
            'deep': 'Deep (>80m)'
        }
        depth_counts['Category'] = depth_counts['Category'].map(category_map)
        
        depth_chart = (
            alt.Chart(depth_counts)
            .mark_bar()
            .encode(
                x=alt.X('Category:N', title='Depth Category'),
                y=alt.Y('Count:Q', title='Number of Locations'),
                color=alt.Color(
                    'Category:N',
                    scale=alt.Scale(
                        domain=['Shallow (<60m)', 'Medium (60-80m)', 'Deep (>80m)'],
                        range=['#FFC107', '#FF9800', '#FF5722']
                    ),
                    legend=None
                ),
                tooltip=['Category:N', 'Count:Q']
            )
            .properties(height=300)
        )
        
        st.altair_chart(depth_chart, use_container_width=True)
        
    else:
        st.warning("⚠️ No potential drilling locations available. Check data loading.")
    
    st.markdown("---")
    
    # === SELECTED WELL METADATA ===
    st.markdown("**📋 Selected Well Metadata**")
    metadata_panel(selected_row)
    
    st.markdown("---")
    
    # === DISCOVERY TIPS ===
    st.markdown("**💡 Discovery Tips & Guidelines**")
    st.info("""
    **🎯 How to Use This Analysis:**
    
    **1. Priority Assessment:**
    - 🔴 Critical: Fields with >70% water gap
    - 🟡 High: Fields with 50-70% water gap
    - 🔵 Medium: Fields with 30-50% water gap
    
    **2. Depth Selection:**
    - **Shallow (<60m):** Lower cost (฿48-72k), moderate success (50-70%), suitable for seasonal use
    - **Medium (60-80m):** Balanced option (฿72-96k), good success (70-85%), recommended for most cases
    - **Deep (>80m):** Higher cost (฿96-144k), best success (75-90%), stable year-round supply
    
    **3. Cost Considerations:**
    - Drilling cost: ฿1,200/meter
    - Pump system: ฿30-60k
    - Total investment shown includes both
    - ROI typically 12-36 months for agricultural use
    
    **4. Location Guidelines:**
    - Suggested locations are 100m-2km from field boundaries
    - Minimum 100m spacing from existing wells
    - Consider proximity to power supply and access roads
    - Professional geophysical survey recommended before drilling
    
    **5. Service Coverage:**
    - Each well can serve approximately 5km radius
    - Average yield: 8-12 m³/hour
    - Operating 8 hours/day provides ~240-360 m³/day
    - Sugarcane needs ~20-30 m³/rai/day during peak season
    
    **💰 Financial Planning:**
    - Consider drilling multiple wells in phases
    - Prioritize fields with highest water gaps first
    - Group nearby locations for cost efficiency
    - Factor in electricity costs: ฿500-2,000/month per well
    """)
    
    # === SUCCESS RATE ANALYSIS ===
    with st.expander("📊 Success Rate Analysis"):
        if not filtered_wells.empty:
            success_rate = filtered_wells["survived"].mean()
            total_wells = len(filtered_wells)
            successful = filtered_wells["survived"].sum()
            failed = total_wells - successful
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Wells", total_wells)
            with col2:
                st.metric("Successful", successful)
            with col3:
                st.metric("Success Rate", f"{success_rate:.1%}")
            
            st.markdown(f"""
            **Analysis Summary:**
            - {successful} out of {total_wells} wells are successful
            - Success rate: {success_rate:.1%}
            - Failed wells: {failed}
            
            {'✅ Good success rate! This area shows promise.' if success_rate > 0.7 else '⚠️ Lower success rate. Consider careful site selection and professional surveys.'}
            """)