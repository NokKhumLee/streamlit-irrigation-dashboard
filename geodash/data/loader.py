# geodash/data/loader.py - Updated for farm-based time series and distance filtering

"""
Main data loader hub for the geological dashboard.
Updated to handle farm-based time series instead of well-based time series.
Now includes distance_to_farm filtering capability.
"""
from pathlib import Path
from typing import Dict, Union, Optional
import logging

from .data_loaders import (
    WellsLoader,
    PolygonsLoader, 
    FarmsLoader,
    HeatmapLoader
)
from .mockup import generate_mock_data


# Configure logging for the data loading system
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataLoader")


class DashboardDataLoader:
    """
    Main coordinator for all dashboard data loading.
    Updated to handle farm-based time series data and distance filtering.
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
        self.heatmap_loader = HeatmapLoader(data_dir)
        
        logger.info("✅ All specialized loaders initialized")
    
    def load_all_data(self, max_distance_to_farm_m: Optional[float] = None) -> Dict[str, object]:
        """
        Load all dashboard data using specialized loaders.
        
        Args:
            max_distance_to_farm_m: Maximum distance to farm in meters (default: 10km)
        
        Returns:
            Dict containing all dashboard data:
            - polygons: List[Dict] - Field boundary polygons
            - farm_polygons: List[Dict] - Farm boundary polygons with colors
            - wells_df: pd.DataFrame - Well/groundwater data (filtered by distance)
            - farm_time_series: pd.DataFrame - Time series data for farms/regions
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
            # Load field water CSV for enrichment
            import pandas as pd
            field_csv_path = self.data_dir / "field_water_data" / "field_data.csv"
            field_data_df = pd.read_csv(field_csv_path)
            
            # Phase 2: Load wells data (most critical for derived data) with distance filtering
            logger.info("🏔️  Phase 2: Loading wells data with distance filtering...")
            wells_df = self.wells_loader.load(max_distance_to_farm_m)
            
            # Phase 3: Generate derived data based on wells
            logger.info("📊 Phase 3: Generating derived datasets...")
            heat_points = self.heatmap_loader.load(wells_df)
            
            # Phase 4: Generate farm-based time series and additional datasets
            logger.info("🚜 Phase 4: Generating farm time series and additional data...")
            farm_time_series = self._generate_farm_time_series(wells_df)
            
            # Load mock cost and probability data
            mock_data = generate_mock_data()
            cost_df = mock_data["cost_df"]
            prob_df = mock_data["prob_df"]
            
            # Combine all data into final structure
            data = {
                "polygons": polygons,
                "farm_polygons": farm_polygons,
                "wells_df": wells_df,
                "farm_time_series": farm_time_series,
                "heat_points": heat_points,
                "cost_df": cost_df,
                "prob_df": prob_df,
                "field_data_df": field_data_df,
            }
            
            # Validate and log final results
            self._validate_data_integrity(data)
            self._log_comprehensive_summary(data)
            
            logger.info("🎉 Data loading completed successfully!")
            return data
            
        except Exception as e:
            logger.error(f"❌ Critical error during data loading: {e}")
            logger.warning("🔄 Falling back to complete mock dataset...")
            return self._load_complete_fallback_data(max_distance_to_farm_m)
    
    def _generate_farm_time_series(self, wells_df) -> object:
        """
        Generate farm-based time series data from wells data.
        
        Args:
            wells_df: DataFrame containing well data
            
        Returns:
            DataFrame with farm/region time series data
        """
        try:
            import pandas as pd
            import numpy as np
            
            if wells_df.empty:
                logger.warning("⚠️  No wells data available for farm time series generation")
                return pd.DataFrame()
            
            rng = np.random.default_rng(42)
            
            # Generate 24 months of data (2 years)
            months = pd.date_range(end=pd.Timestamp.today().normalize(), periods=24, freq="MS")
            
            # Get unique regions from wells data
            unique_regions = wells_df["region"].unique()
            farm_time_series_data = []
            
            for region in unique_regions:
                # Get wells in this region
                region_wells = wells_df[wells_df["region"] == region]
                base_survival_rate = region_wells["survived"].mean()
                total_wells_in_region = len(region_wells)
                
                # Calculate average distance to farm for this region
                avg_distance_to_farm = region_wells["distance_to_farm"].mean() if "distance_to_farm" in region_wells.columns else 5000
                
                for month in months:
                    # Add seasonal variation
                    month_num = month.month
                    seasonal_factor = 1.0
                    
                    # Thailand rainy season (May-October) - higher survival rates
                    if 5 <= month_num <= 10:
                        seasonal_factor = rng.uniform(1.05, 1.2)
                    else:
                        seasonal_factor = rng.uniform(0.85, 1.0)
                    
                    # Distance factor: closer to farms = slightly better performance
                    distance_factor = 1.0
                    if avg_distance_to_farm < 2000:  # < 2km
                        distance_factor = 1.05
                    elif avg_distance_to_farm > 10000:  # > 10km
                        distance_factor = 0.95
                    
                    # Add noise
                    noise = rng.normal(0, 0.03)
                    survival_rate = np.clip(base_survival_rate * seasonal_factor * distance_factor + noise, 0.0, 1.0)
                    
                    farm_time_series_data.append({
                        "date": month,
                        "region": region,
                        "survival_rate": survival_rate,
                        "total_wells": total_wells_in_region,
                        "successful_wells": int(total_wells_in_region * survival_rate),
                        "water_level_avg_m": rng.uniform(3.0, 8.0),
                        "rainfall_mm": rng.uniform(0, 150) if 5 <= month_num <= 10 else rng.uniform(0, 50),
                        "avg_distance_to_farm": avg_distance_to_farm
                    })
            
            farm_time_series = pd.DataFrame(farm_time_series_data)
            logger.info(f"✅ Generated farm time series for {len(unique_regions)} regions over {len(months)} months")
            return farm_time_series
            
        except Exception as e:
            logger.error(f"❌ Error generating farm time series: {e}")
            # Fallback to mock data
            mock_data = generate_mock_data()
            return mock_data.get("farm_time_series", pd.DataFrame())
    
    def load_specific_data(self, data_types: list, max_distance_to_farm_m: Optional[float] = None) -> Dict[str, object]:
        """
        Load only specific types of data.
        
        Args:
            data_types: List of data types to load 
                       ['wells', 'polygons', 'farms', 'farm_timeseries', 'heatmap']
            max_distance_to_farm_m: Maximum distance to farm in meters
        """
        logger.info(f"🎯 Loading specific data types: {data_types}")
        
        data = {}
        
        if 'wells' in data_types:
            data['wells_df'] = self.wells_loader.load(max_distance_to_farm_m)
        
        if 'polygons' in data_types:
            data['polygons'] = self.polygons_loader.load()
        
        if 'farms' in data_types:
            data['farm_polygons'] = self.farms_loader.load()
        
        if 'farm_timeseries' in data_types:
            wells_df = data.get('wells_df', self.wells_loader.load(max_distance_to_farm_m))
            data['farm_time_series'] = self._generate_farm_time_series(wells_df)
        
        if 'heatmap' in data_types:
            wells_df = data.get('wells_df', self.wells_loader.load(max_distance_to_farm_m))
            data['heat_points'] = self.heatmap_loader.load(wells_df)
        
        logger.info(f"✅ Specific data loading complete: {list(data.keys())}")
        return data
    
    def _validate_data_integrity(self, data: Dict[str, object]) -> None:
        """
        Validate that loaded data has proper structure and relationships.
        """
        logger.info("🔍 Validating data integrity...")
        
        # Check that all expected keys exist
        expected_keys = ["polygons", "farm_polygons", "wells_df", "farm_time_series", "heat_points", "cost_df", "prob_df"]
        missing_keys = [key for key in expected_keys if key not in data]
        
        if missing_keys:
            logger.warning(f"⚠️  Missing data keys: {missing_keys}")
        
        # Validate wells data
        wells_df = data.get("wells_df")
        if wells_df is not None and not wells_df.empty:
            required_cols = ['well_id', 'lat', 'lon', 'depth_m', 'region', 'survived', 'distance_to_farm']
            missing_cols = [col for col in required_cols if col not in wells_df.columns]
            if missing_cols:
                logger.warning(f"⚠️  Wells data missing columns: {missing_cols}")
            else:
                logger.info("✅ Wells data structure validated")
        
        # Validate farm time series consistency
        farm_time_series = data.get("farm_time_series")
        if wells_df is not None and farm_time_series is not None and not wells_df.empty and not farm_time_series.empty:
            regions_in_ts = set(farm_time_series['region'].unique())
            regions_in_wells = set(wells_df['region'].unique())
            if not regions_in_ts.issubset(regions_in_wells):
                logger.warning("⚠️  Farm time series contains regions not in wells dataset")
            else:
                logger.info("✅ Farm time series data consistency validated")
        
        logger.info("🔍 Data integrity validation complete")
    
    def _log_comprehensive_summary(self, data: Dict[str, object]) -> None:
        """
        Log detailed summary of all loaded data.
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
            
            # Distance to farm summary
            if 'distance_to_farm' in wells_df.columns:
                min_dist = wells_df['distance_to_farm'].min()
                max_dist = wells_df['distance_to_farm'].max()
                avg_dist = wells_df['distance_to_farm'].mean()
                logger.info(f"   • Distance to farm: {min_dist:.0f}m - {max_dist:.0f}m (avg: {avg_dist:.0f}m)")
                
                # Distance distribution
                within_1km = (wells_df['distance_to_farm'] <= 1000).sum()
                within_5km = (wells_df['distance_to_farm'] <= 5000).sum()
                within_10km = (wells_df['distance_to_farm'] <= 10000).sum()
                logger.info(f"   • Within 1km: {within_1km}, 5km: {within_5km}, 10km: {within_10km}")
        
        # Farm time series data summary
        farm_time_series = data.get("farm_time_series")
        if farm_time_series is not None and not farm_time_series.empty:
            date_range = f"{farm_time_series['date'].min().strftime('%Y-%m')} to {farm_time_series['date'].max().strftime('%Y-%m')}"
            logger.info(f"🚜 Farm Time Series Data:")
            logger.info(f"   • Records: {len(farm_time_series):,}")
            logger.info(f"   • Date range: {date_range}")
            logger.info(f"   • Regions covered: {farm_time_series['region'].nunique()}")
            logger.info(f"   • Avg survival rate: {farm_time_series['survival_rate'].mean():.1%}")
        
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
    
    def _load_complete_fallback_data(self, max_distance_to_farm_m: Optional[float] = None) -> Dict[str, object]:
        """
        Load complete fallback dataset when all else fails.
        """
        logger.warning("🚨 Loading complete fallback dataset")
        mock_data = generate_mock_data()
        
        # Apply distance filter to mock data if specified
        wells_df = mock_data.get("wells_df")
        if wells_df is not None:
            import numpy as np
            # Add mock distance column if not present (up to 30km range)
            if 'distance_to_farm' not in wells_df.columns:
                rng = np.random.default_rng(42)
                wells_df['distance_to_farm'] = rng.uniform(100, 30000, size=len(wells_df))
            
            # Apply filter if specified
            if max_distance_to_farm_m is not None:
                wells_df = wells_df[wells_df['distance_to_farm'] <= max_distance_to_farm_m]
        
        # Ensure all required keys are present
        complete_data = {
            "polygons": mock_data.get("polygons", []),
            "farm_polygons": [],  # Empty farm polygons for fallback
            "wells_df": wells_df,
            "farm_time_series": mock_data.get("farm_time_series"),
            "heat_points": mock_data.get("heat_points", []),
            "cost_df": mock_data.get("cost_df"),
            "prob_df": mock_data.get("prob_df"),
        }
        
        logger.warning("⚠️  Using complete mock dataset - check data file availability")
        return complete_data
    
    def get_distance_statistics(self, max_distance_to_farm_m: Optional[float] = None) -> Dict[str, object]:
        """
        Get statistics about distance filtering and wells distribution.
        
        Args:
            max_distance_to_farm_m: Maximum distance filter to apply
            
        Returns:
            Dictionary with distance statistics
        """
        try:
            wells_df = self.wells_loader.load(max_distance_to_farm_m)
            return self.wells_loader.get_distance_statistics(wells_df)
        except Exception as e:
            logger.error(f"❌ Error getting distance statistics: {e}")
            return {}
    
    def get_data_source_info(self) -> Dict[str, Dict[str, str]]:
        """
        Get information about available data sources and their status.
        
        Returns:
            Dictionary with data source information
        """
        source_info = {
            "wells": {
                "file": str(self.wells_loader.csv_file),
                "status": "available" if self.wells_loader._file_exists(self.wells_loader.csv_file) else "missing",
                "type": "CSV"
            },
            "polygons": {
                "directory": str(self.polygons_loader.rdc_fields_dir),
                "status": "available" if self.polygons_loader.rdc_fields_dir.exists() else "missing",
                "type": "Geospatial"
            },
            "farms": {
                "file": str(self.farms_loader.farms_shapefile),
                "status": "available" if self.farms_loader._file_exists(self.farms_loader.farms_shapefile) else "missing",
                "type": "Shapefile"
            }
        }
        
        return source_info


# Main function that app.py should call (maintains backward compatibility)
def load_dashboard_data(data_dir: Union[str, Path] = "geodash/data", max_distance_to_farm_m: Optional[float] = 10000) -> Dict[str, object]:
    """
    Main function to load all dashboard data.
    This is the primary interface for app.py and maintains backward compatibility.
    
    Args:
        data_dir: Directory containing data files
        max_distance_to_farm_m: Maximum distance to farm in meters (default: 10km)
        
    Returns:
        Dictionary containing all dashboard data
    """
    loader = DashboardDataLoader(data_dir)
    return loader.load_all_data(max_distance_to_farm_m)


# Additional convenience functions for specific use cases
def load_wells_only(data_dir: Union[str, Path] = "geodash/data", max_distance_to_farm_m: Optional[float] = None):
    """Load only wells data (useful for testing)."""
    loader = DashboardDataLoader(data_dir)
    return loader.load_specific_data(['wells'], max_distance_to_farm_m)


def load_farm_data(data_dir: Union[str, Path] = "geodash/data"):
    """Load farm polygons and time series data."""
    loader = DashboardDataLoader(data_dir)
    return loader.load_specific_data(['farms', 'farm_timeseries'])


def get_data_status(data_dir: Union[str, Path] = "geodash/data") -> Dict[str, Dict[str, str]]:
    """Get status information about available data sources."""
    loader = DashboardDataLoader(data_dir)
    return loader.get_data_source_info()


def get_distance_statistics(data_dir: Union[str, Path] = "geodash/data", max_distance_to_farm_m: Optional[float] = None) -> Dict[str, object]:
    """Get distance to farm statistics."""
    loader = DashboardDataLoader(data_dir)
    return loader.get_distance_statistics(max_distance_to_farm_m)


# Export main interface and utilities
__all__ = [
    "DashboardDataLoader",
    "load_dashboard_data",
    "load_wells_only", 
    "load_farm_data",
    "get_data_status",
    "get_distance_statistics"
]