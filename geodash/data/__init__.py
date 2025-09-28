# geodash/data/__init__.py - Updated for farm-based time series
from .loader import load_dashboard_data, load_wells_only, load_farm_data, get_data_status
from .filters import filter_wells  # Remove sidebar_filters since it's simplified
from .mockup import generate_mock_data

__all__ = [
    "load_dashboard_data",      # Main interface
    "load_wells_only",          # Load only wells
    "load_farm_data",           # NEW: Load farm data including time series
    "get_data_status",          # Check data availability
    "filter_wells",             # Well filtering function
    "generate_mock_data",       # Fallback data
]