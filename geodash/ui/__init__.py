# geodash/ui/__init__.py - Updated for farm-based time series
from .map_panel import (
    build_map,
    build_map_with_controls,
    build_map_with_floating_controls,
    build_map_with_button_bar,
)
from .charts import (
    chart_farm_survival_analytics,    # NEW: Farm-based time series analysis
    chart_ground_water_analytics,     # Legacy function (redirects to farm analytics)
    chart_region_comparison,          # NEW: Compare regions
    chart_seasonal_analysis,          # NEW: Seasonal analysis
    chart_survival_rate,
    chart_probability_by_depth,
    chart_cost_estimation,
    chart_rain_statistics,
    chart_rain_frequency,
)
from .widgets import metadata_panel, download_button

__all__ = [
    "build_map",
    "build_map_with_controls",
    "build_map_with_floating_controls", 
    "build_map_with_button_bar",
    "chart_farm_survival_analytics",    # NEW
    "chart_ground_water_analytics",     # Legacy compatibility
    "chart_region_comparison",          # NEW
    "chart_seasonal_analysis",          # NEW
    "chart_survival_rate",
    "chart_probability_by_depth",
    "chart_cost_estimation",
    "chart_rain_statistics",
    "chart_rain_frequency",
    "metadata_panel",
    "download_button",
]