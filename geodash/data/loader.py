# geodash/data/loader.py - Updated for farm-based time series

"""
Main data loader hub for the geological dashboard.
Updated to handle farm-based time series instead of well-based time series.
"""
from pathlib import Path
from typing import Dict, Union
import logging

from .data_loaders import (
    WellsLoader,
    PolygonsLoader, 
    FarmsLoader,
    # TimeSeriesLoader,  # Not needed for farm-based approach
    HeatmapLoader
)
from .mockup import generate_mock_data


# Configure logging for the data loading system
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataLoader")


class DashboardDataLoader:
    """
    Main coordinator for all dashboard data loading.
    Updated to handle farm-based time series data.
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
        # Remove timeseries_loader since we're generating farm-based data directly
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
            
            # Phase 2: Load wells data (most critical for derived data)
            logger.info("🏔️  Phase 2: Loading wells data...")
            wells_df = self.wells_loader.load()
            
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
                "farm_time_series": farm_time_series,  # Changed from water_levels
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
                
                for month in months:
                    # Add seasonal variation
                    month_num = month.month
                    seasonal_factor = 1.0
                    
                    # Thailand rainy season (May-October) - higher survival rates
                    if 5 <= month_num <= 10:
                        seasonal_factor = rng.uniform(1.05, 1.2)
                    else:
                        seasonal_factor = rng.uniform(0.85, 1.0)
                    
                    # Add noise
                    noise = rng.normal(0, 0.03)
                    survival_rate = np.clip(base_survival_rate * seasonal_factor + noise, 0.0, 1.0)
                    
                    farm_time_series_data.append({
                        "date": month,
                        "region": region,
                        "survival_rate": survival_rate,
                        "total_wells": total_wells_in_region,
                        "successful_wells": int(total_wells_in_region * survival_rate),
                        "water_level_avg_m": rng.uniform(3.0, 8.0),
                        "rainfall_mm": rng.uniform(0, 150) if 5 <= month_num <= 10 else rng.uniform(0, 50)
                    })
            
            farm_time_series = pd.DataFrame(farm_time_series_data)
            logger.info(f"✅ Generated farm time series for {len(unique_regions)} regions over {len(months)} months")
            return farm_time_series
            
        except Exception as e:
            logger.error(f"❌ Error generating farm time series: {e}")
            # Fallback to mock data
            mock_data = generate_mock_data()
            return mock_data.get("farm_time_series", pd.DataFrame())
    
    def load_specific_data(self, data_types: list) -> Dict[str, object]:
        """
        Load only specific types of data.
        
        Args:
            data_types: List of data types to load 
                       ['wells', 'polygons', 'farms', 'farm_timeseries', 'heatmap']
        """
        logger.info(f"🎯 Loading specific data types: {data_types}")
        
        data = {}
        
        if 'wells' in data_types:
            data['wells_df'] = self.wells_loader.load()
        
        if 'polygons' in data_types:
            data['polygons'] = self.polygons_loader.load()
        
        if 'farms' in data_types:
            data['farm_polygons'] = self.farms_loader.load()
        
        if 'farm_timeseries' in data_types:
            wells_df = data.get('wells_df', self.wells_loader.load())
            data['farm_time_series'] = self._generate_farm_time_series(wells_df)
        
        if 'heatmap' in data_types:
            wells_df = data.get('wells_df', self.wells_loader.load())
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
            required_cols = ['well_id', 'lat', 'lon', 'depth_m', 'region', 'survived']
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
    
    def _load_complete_fallback_data(self) -> Dict[str, object]:
        """
        Load complete fallback dataset when all else fails.
        """
        logger.warning("🚨 Loading complete fallback dataset")
        mock_data = generate_mock_data()
        
        # Ensure all required keys are present
        complete_data = {
            "polygons": mock_data.get("polygons", []),
            "farm_polygons": [],  # Empty farm polygons for fallback
            "wells_df": mock_data.get("wells_df"),
            "farm_time_series": mock_data.get("farm_time_series"),  # Changed from water_levels
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


def load_farm_data(data_dir: Union[str, Path] = "geodash/data"):
    """Load farm polygons and time series data."""
    loader = DashboardDataLoader(data_dir)
    return loader.load_specific_data(['farms', 'farm_timeseries'])


def get_data_status(data_dir: Union[str, Path] = "geodash/data") -> Dict[str, Dict[str, str]]:
    """Get status information about available data sources."""
    loader = DashboardDataLoader(data_dir)
    return loader.get_data_source_info()


# Export main interface and utilities
__all__ = [
    "DashboardDataLoader",
    "load_dashboard_data",
    "load_wells_only",
    "load_farm_data",
    "get_data_status"
]