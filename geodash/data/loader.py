"""
Main data loader hub for the geological dashboard.
Coordinates specialized loaders and provides the main interface for app.py.
This replaces the previous monolithic loader with a clean, modular approach.
"""
from pathlib import Path
from typing import Dict, Union
import logging

from .data_loaders import (
    WellsLoader,
    PolygonsLoader, 
    FarmsLoader,
    TimeSeriesLoader,
    HeatmapLoader
)
from .mockup import generate_mock_data


# Configure logging for the data loading system
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataLoader")


class DashboardDataLoader:
    """
    Main coordinator for all dashboard data loading.
    Acts as a hub that delegates to specialized loaders.
    """
    
    def __init__(self, data_dir: Union[str, Path] = "geodash/data"):
        """
        Initialize the dashboard data loader.
        
        Args:
            data_dir: Directory containing data files
        """
        self.data_dir = Path(data_dir)
        logger.info(f"🏗️  Initializing data loader for directory: {self.data_dir}")
        
        # Initialize specialized loaders
        self.wells_loader = WellsLoader(data_dir)
        self.polygons_loader = PolygonsLoader(data_dir)
        self.farms_loader = FarmsLoader(data_dir)
        self.timeseries_loader = TimeSeriesLoader(data_dir)
        self.heatmap_loader = HeatmapLoader(data_dir)
        
        logger.info("✅ All specialized loaders initialized")
    
    def load_all_data(self) -> Dict[str, object]:
        """
        Load all dashboard data using specialized loaders.
        
        Returns:
            Dict containing all dashboard data:
            - polygons: List[Dict] - Field boundary polygons
            - farm_polygons: List[Dict] - Farm boundary polygons with colors
            - wells_df: pd.DataFrame - Well/groundwater data
            - water_levels: pd.DataFrame - Time series water level data
            - heat_points: List[List[float]] - Heatmap visualization points
            - cost_df: pd.DataFrame - Cost estimation data (mock)
            - prob_df: pd.DataFrame - Success probability data (mock)
        """
        logger.info("🚀 Starting comprehensive data loading process...")
        
        try:
            # Phase 1: Load core geospatial data
            logger.info("📍 Phase 1: Loading geospatial data...")
            polygons = self.polygons_loader.load()
            farm_polygons = self.farms_loader.load()
            
            # Phase 2: Load wells data (most critical for derived data)
            logger.info("🏔️  Phase 2: Loading wells data...")
            wells_df = self.wells_loader.load()
            
            # Phase 3: Generate derived data based on wells
            logger.info("📊 Phase 3: Generating derived datasets...")
            water_levels = self.timeseries_loader.load(wells_df)
            heat_points = self.heatmap_loader.load(wells_df)
            
            # Phase 4: Load additional datasets (currently mock data)
            logger.info("💰 Phase 4: Loading cost and probability data...")
            mock_data = generate_mock_data()
            cost_df = mock_data["cost_df"]
            prob_df = mock_data["prob_df"]
            
            # Combine all data into final structure
            data = {
                "polygons": polygons,
                "farm_polygons": farm_polygons,
                "wells_df": wells_df,
                "water_levels": water_levels,
                "heat_points": heat_points,
                "cost_df": cost_df,
                "prob_df": prob_df,
            }
            
            # Validate and log final results
            self._validate_data_integrity(data)
            self._log_comprehensive_summary(data)
            
            logger.info("🎉 Data loading completed successfully!")
            return data
            
        except Exception as e:
            logger.error(f"❌ Critical error during data loading: {e}")
            logger.warning("🔄 Falling back to complete mock dataset...")
            return self._load_complete_fallback_data()
    
    def load_specific_data(self, data_types: list) -> Dict[str, object]:
        """
        Load only specific types of data (useful for testing or partial loading).
        
        Args:
            data_types: List of data types to load 
                       ['wells', 'polygons', 'farms', 'timeseries', 'heatmap']
            
        Returns:
            Dictionary containing only the requested data types
        """
        logger.info(f"🎯 Loading specific data types: {data_types}")
        
        data = {}
        
        if 'wells' in data_types:
            data['wells_df'] = self.wells_loader.load()
        
        if 'polygons' in data_types:
            data['polygons'] = self.polygons_loader.load()
        
        if 'farms' in data_types:
            data['farm_polygons'] = self.farms_loader.load()
        
        if 'timeseries' in data_types:
            wells_df = data.get('wells_df', self.wells_loader.load())
            data['water_levels'] = self.timeseries_loader.load(wells_df)
        
        if 'heatmap' in data_types:
            wells_df = data.get('wells_df', self.wells_loader.load())
            data['heat_points'] = self.heatmap_loader.load(wells_df)
        
        logger.info(f"✅ Specific data loading complete: {list(data.keys())}")
        return data
    
    def reload_data(self, force_refresh: bool = False) -> Dict[str, object]:
        """
        Reload all data, optionally forcing refresh of cached data.
        
        Args:
            force_refresh: If True, bypass any caching mechanisms
            
        Returns:
            Freshly loaded data dictionary
        """
        if force_refresh:
            logger.info("🔄 Force refreshing all data loaders...")
            # Re-initialize loaders to clear any internal caching
            self.__init__(self.data_dir)
        
        return self.load_all_data()
    
    def get_data_source_info(self) -> Dict[str, Dict[str, str]]:
        """
        Get information about data sources and their status.
        
        Returns:
            Dictionary with status info for each data source
        """
        info = {
            "wells": {
                "source_file": str(self.wells_loader.csv_file),
                "exists": self.wells_loader._file_exists(self.wells_loader.csv_file),
                "loader_class": "WellsLoader"
            },
            "field_polygons": {
                "source_dir": str(self.polygons_loader.rdc_fields_dir),
                "exists": self.polygons_loader.rdc_fields_dir.exists(),
                "loader_class": "PolygonsLoader"
            },
            "farm_polygons": {
                "source_file": str(self.farms_loader.farms_shapefile),
                "exists": self.farms_loader._file_exists(self.farms_loader.farms_shapefile),
                "loader_class": "FarmsLoader"
            },
            "time_series": {
                "source": "Generated from wells data",
                "exists": True,
                "loader_class": "TimeSeriesLoader"
            },
            "heatmap": {
                "source": "Generated from wells data",
                "exists": True,
                "loader_class": "HeatmapLoader"
            }
        }
        return info
    
    def _validate_data_integrity(self, data: Dict[str, object]) -> None:
        """
        Validate that loaded data has proper structure and relationships.
        
        Args:
            data: Loaded data dictionary to validate
        """
        logger.info("🔍 Validating data integrity...")
        
        # Check that all expected keys exist
        expected_keys = ["polygons", "farm_polygons", "wells_df", "water_levels", "heat_points", "cost_df", "prob_df"]
        missing_keys = [key for key in expected_keys if key not in data]
        
        if missing_keys:
            logger.warning(f"⚠️  Missing data keys: {missing_keys}")
        
        # Validate wells data
        wells_df = data.get("wells_df")
        if wells_df is not None and not wells_df.empty:
            required_cols = ['well_id', 'lat', 'lon', 'depth_m', 'region', 'survived']
            missing_cols = [col for col in required_cols if col not in wells_df.columns]
            if missing_cols:
                logger.warning(f"⚠️  Wells data missing columns: {missing_cols}")
            else:
                logger.info("✅ Wells data structure validated")
        
        # Validate time series consistency
        water_levels = data.get("water_levels")
        if wells_df is not None and water_levels is not None and not wells_df.empty and not water_levels.empty:
            wells_in_ts = set(water_levels['well_id'].unique())
            wells_in_main = set(wells_df['well_id'].unique())
            if not wells_in_ts.issubset(wells_in_main):
                logger.warning("⚠️  Time series contains wells not in main dataset")
            else:
                logger.info("✅ Time series data consistency validated")
        
        logger.info("🔍 Data integrity validation complete")
    
    def _log_comprehensive_summary(self, data: Dict[str, object]) -> None:
        """
        Log detailed summary of all loaded data.
        
        Args:
            data: Loaded data dictionary
        """
        logger.info("📋 === COMPREHENSIVE DATA LOADING SUMMARY ===")
        
        # Geospatial data summary
        polygons = data.get("polygons", [])
        farm_polygons = data.get("farm_polygons", [])
        logger.info(f"🗺️  Geospatial Data:")
        logger.info(f"   • Field polygons: {len(polygons)}")
        logger.info(f"   • Farm polygons: {len(farm_polygons)}")
        
        # Wells data summary
        wells_df = data.get("wells_df")
        if wells_df is not None and not wells_df.empty:
            success_rate = wells_df['survived'].mean()
            depth_range = f"{wells_df['depth_m'].min():.0f}-{wells_df['depth_m'].max():.0f}m"
            logger.info(f"🏔️  Wells Data:")
            logger.info(f"   • Total wells: {len(wells_df)}")
            logger.info(f"   • Success rate: {success_rate:.1%}")
            logger.info(f"   • Depth range: {depth_range}")
            logger.info(f"   • Regions: {wells_df['region'].nunique()}")
        
        # Time series data summary
        water_levels = data.get("water_levels")
        if water_levels is not None and not water_levels.empty:
            date_range = f"{water_levels['date'].min().strftime('%Y-%m')} to {water_levels['date'].max().strftime('%Y-%m')}"
            logger.info(f"📊 Time Series Data:")
            logger.info(f"   • Records: {len(water_levels):,}")
            logger.info(f"   • Date range: {date_range}")
            logger.info(f"   • Wells covered: {water_levels['well_id'].nunique()}")
        
        # Heatmap data summary
        heat_points = data.get("heat_points", [])
        if heat_points:
            weights = [point[2] for point in heat_points]
            avg_weight = sum(weights) / len(weights)
            logger.info(f"🔥 Heatmap Data:")
            logger.info(f"   • Heat points: {len(heat_points):,}")
            logger.info(f"   • Average weight: {avg_weight:.3f}")
            logger.info(f"   • High probability points: {sum(1 for w in weights if w > 0.7)}")
        
        # Additional datasets
        cost_df = data.get("cost_df")
        prob_df = data.get("prob_df")
        logger.info(f"💰 Additional Data:")
        logger.info(f"   • Cost estimation records: {len(cost_df) if cost_df is not None else 0}")
        logger.info(f"   • Probability records: {len(prob_df) if prob_df is not None else 0}")
        
        logger.info("📋 === END SUMMARY ===")
    
    def _load_complete_fallback_data(self) -> Dict[str, object]:
        """
        Load complete fallback dataset when all else fails.
        
        Returns:
            Complete mock dataset
        """
        logger.warning("🚨 Loading complete fallback dataset")
        mock_data = generate_mock_data()
        
        # Ensure all required keys are present
        complete_data = {
            "polygons": mock_data.get("polygons", []),
            "farm_polygons": [],  # Empty farm polygons for fallback
            "wells_df": mock_data.get("wells_df"),
            "water_levels": mock_data.get("water_levels"),
            "heat_points": mock_data.get("heat_points", []),
            "cost_df": mock_data.get("cost_df"),
            "prob_df": mock_data.get("prob_df"),
        }
        
        logger.warning("⚠️  Using complete mock dataset - check data file availability")
        return complete_data


# Main function that app.py should call (maintains backward compatibility)
def load_dashboard_data(data_dir: Union[str, Path] = "geodash/data") -> Dict[str, object]:
    """
    Main function to load all dashboard data.
    This is the primary interface for app.py and maintains backward compatibility.
    
    Args:
        data_dir: Directory containing data files
        
    Returns:
        Dictionary containing all dashboard data
    """
    loader = DashboardDataLoader(data_dir)
    return loader.load_all_data()


# Additional convenience functions for specific use cases
def load_wells_only(data_dir: Union[str, Path] = "geodash/data"):
    """Load only wells data (useful for testing)."""
    loader = DashboardDataLoader(data_dir)
    return loader.load_specific_data(['wells'])


def load_geospatial_only(data_dir: Union[str, Path] = "geodash/data"):
    """Load only geospatial data (polygons and farms)."""
    loader = DashboardDataLoader(data_dir)
    return loader.load_specific_data(['polygons', 'farms'])


def get_data_status(data_dir: Union[str, Path] = "geodash/data") -> Dict[str, Dict[str, str]]:
    """Get status information about available data sources."""
    loader = DashboardDataLoader(data_dir)
    return loader.get_data_source_info()


# Export main interface and utilities
__all__ = [
    "DashboardDataLoader",
    "load_dashboard_data",
    "load_wells_only",
    "load_geospatial_only", 
    "get_data_status"
]