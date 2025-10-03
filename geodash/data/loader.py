# geodash/data/loader.py - Complete version with potential wells support

"""
Main data loader hub for the geological dashboard.
Updated to handle farm-based time series and potential drilling locations.
"""
from pathlib import Path
from typing import Dict, Union, Optional
import logging
import pandas as pd
import numpy as np

from .data_loaders import (
    WellsLoader,
    PolygonsLoader, 
    FarmsLoader,
    HeatmapLoader
)
from .mockup import generate_mock_data, generate_potential_wells, calculate_water_demand_gap


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataLoader")


class DashboardDataLoader:
    """
    Main coordinator for all dashboard data loading.
    Updated to handle farm-based time series data and potential drilling locations.
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
            max_distance_to_farm_m: Maximum distance to farm in meters
        
        Returns:
            Dict containing all dashboard data
        """
        logger.info("🚀 Starting comprehensive data loading process...")
        
        try:
            # Phase 1: Load core geospatial data
            logger.info("📍 Phase 1: Loading geospatial data...")
            polygons = self.polygons_loader.load()
            farm_polygons = self.farms_loader.load()
            
            # Load field water CSV for enrichment
            field_csv_path = self.data_dir / "field_water_data" / "field_data.csv"
            try:
                field_data_df = pd.read_csv(field_csv_path)
                logger.info(f"✅ Loaded field data CSV: {len(field_data_df)} records")
            except Exception as e:
                logger.warning(f"⚠️  Could not load field data CSV: {e}")
                field_data_df = pd.DataFrame()
            
            # Phase 2: Load wells data with distance filtering
            logger.info("🏔️  Phase 2: Loading wells data...")
            wells_df = self.wells_loader.load(max_distance_to_farm_m)
            
            # Phase 3: Generate derived data based on wells
            logger.info("📊 Phase 3: Generating derived datasets...")
            heat_points = self.heatmap_loader.load(wells_df)
            
            # Phase 4: Generate farm-based time series
            logger.info("🚜 Phase 4: Generating farm time series...")
            farm_time_series = self._generate_farm_time_series(wells_df)
            
            # Phase 5: Generate potential drilling locations
            logger.info("💡 Phase 5: Generating potential drilling locations...")
            
            # Use real polygons if available
            if polygons and len(polygons) > 0:
                logger.info(f"✅ Using {len(polygons)} real field polygons for potential wells")
                potential_wells_df = generate_potential_wells(
                    polygons,
                    wells_df,
                    num_suggestions=25
                )
            else:
                logger.warning("⚠️  No real polygons available, using mock data")
                mock_data = generate_mock_data()
                potential_wells_df = generate_potential_wells(
                    mock_data["polygons"],
                    wells_df,
                    num_suggestions=25
                )
            
            # Calculate water demand gaps
            if not potential_wells_df.empty:
                logger.info(f"💧 Calculating water demand gaps...")
                demand_gap_df = calculate_water_demand_gap(
                    polygons if polygons else mock_data["polygons"],
                    wells_df,
                    potential_wells_df
                )
            else:
                logger.warning("⚠️  No potential wells generated")
                demand_gap_df = pd.DataFrame()
            
            # Load mock cost and probability data
            mock_data = generate_mock_data()
            cost_df = mock_data["cost_df"]
            prob_df = mock_data["prob_df"]
            
            # Combine all data
            data = {
                "polygons": polygons,
                "farm_polygons": farm_polygons,
                "wells_df": wells_df,
                "farm_time_series": farm_time_series,
                "heat_points": heat_points,
                "cost_df": cost_df,
                "prob_df": prob_df,
                "field_data_df": field_data_df,
                "potential_wells_df": potential_wells_df,
                "demand_gap_df": demand_gap_df,
            }
            
            # Log summary
            self._log_comprehensive_summary(data)
            
            logger.info("🎉 Data loading completed successfully!")
            return data
            
        except Exception as e:
            logger.error(f"❌ Critical error during data loading: {e}")
            import traceback
            traceback.print_exc()
            logger.warning("🔄 Falling back to complete mock dataset...")
            return self._load_complete_fallback_data(max_distance_to_farm_m)
    
    def _generate_farm_time_series(self, wells_df) -> pd.DataFrame:
        """Generate farm-based time series data from wells data."""
        try:
            if wells_df.empty:
                logger.warning("⚠️  No wells data for farm time series")
                return pd.DataFrame()
            
            rng = np.random.default_rng(42)
            
            # Generate 24 months of data
            months = pd.date_range(end=pd.Timestamp.today().normalize(), periods=24, freq="MS")
            
            # Get unique regions
            unique_regions = wells_df["region"].unique()
            farm_time_series_data = []
            
            for region in unique_regions:
                region_wells = wells_df[wells_df["region"] == region]
                base_survival_rate = region_wells["survived"].mean()
                total_wells_in_region = len(region_wells)
                
                for month in months:
                    month_num = month.month
                    seasonal_factor = 1.0
                    
                    if 5 <= month_num <= 10:
                        seasonal_factor = rng.uniform(1.05, 1.2)
                    else:
                        seasonal_factor = rng.uniform(0.85, 1.0)
                    
                    noise = rng.normal(0, 0.03)
                    survival_rate = np.clip(base_survival_rate * seasonal_factor + noise, 0.0, 1.0)
                    
                    farm_time_series_data.append({
                        "date": month,
                        "region": region,
                        "survival_rate": survival_rate,
                        "total_wells": total_wells_in_region,
                        "successful_wells": int(total_wells_in_region * survival_rate),
                        "water_level_avg_m": rng.uniform(3.0, 8.0),
                        "rainfall_mm": rng.uniform(0, 150) if 5 <= month_num <= 10 else rng.uniform(0, 50),
                    })
            
            return pd.DataFrame(farm_time_series_data)
            
        except Exception as e:
            logger.error(f"❌ Error generating farm time series: {e}")
            mock_data = generate_mock_data()
            return mock_data.get("farm_time_series", pd.DataFrame())
    
    def _load_complete_fallback_data(self, max_distance_to_farm_m: Optional[float] = None) -> Dict[str, object]:
        """Load complete fallback dataset."""
        logger.warning("🚨 Loading complete fallback dataset")
        mock_data = generate_mock_data()
        
        # Apply distance filter to mock data if specified
        wells_df = mock_data.get("wells_df")
        if wells_df is not None and max_distance_to_farm_m is not None:
            wells_df = wells_df[wells_df['distance_to_farm'] <= max_distance_to_farm_m]
        
        # Generate potential wells from mock data
        potential_wells_df = generate_potential_wells(
            mock_data["polygons"],
            wells_df,
            num_suggestions=25
        )
        
        demand_gap_df = calculate_water_demand_gap(
            mock_data["polygons"],
            wells_df,
            potential_wells_df
        )
        
        complete_data = {
            "polygons": mock_data.get("polygons", []),
            "farm_polygons": [],
            "wells_df": wells_df,
            "farm_time_series": mock_data.get("farm_time_series"),
            "heat_points": mock_data.get("heat_points", []),
            "cost_df": mock_data.get("cost_df"),
            "prob_df": mock_data.get("prob_df"),
            "field_data_df": pd.DataFrame(),
            "potential_wells_df": potential_wells_df,
            "demand_gap_df": demand_gap_df,
        }
        
        logger.warning("⚠️  Using complete mock dataset")
        return complete_data
    
    def _log_comprehensive_summary(self, data: Dict[str, object]) -> None:
        """Log detailed summary of loaded data."""
        logger.info("📋 === DATA LOADING SUMMARY ===")
        
        # Geospatial data
        polygons = data.get("polygons", [])
        farm_polygons = data.get("farm_polygons", [])
        logger.info(f"🗺️  Geospatial: {len(polygons)} fields, {len(farm_polygons)} farms")
        
        # Wells data
        wells_df = data.get("wells_df")
        if wells_df is not None and not wells_df.empty:
            success_rate = wells_df['survived'].mean()
            logger.info(f"🏔️  Wells: {len(wells_df)} total, {success_rate:.1%} success")
        
        # Potential wells
        potential_wells_df = data.get("potential_wells_df")
        if potential_wells_df is not None and not potential_wells_df.empty:
            logger.info(f"💡 Potential wells: {len(potential_wells_df)} locations")
        
        # Demand gaps
        demand_gap_df = data.get("demand_gap_df")
        if demand_gap_df is not None and not demand_gap_df.empty:
            logger.info(f"💧 Demand gaps: {len(demand_gap_df)} fields analyzed")
        
        logger.info("📋 === END SUMMARY ===")


# Main function that app.py should call
def load_dashboard_data(data_dir: Union[str, Path] = "geodash/data", max_distance_to_farm_m: Optional[float] = None) -> Dict[str, object]:
    """
    Main function to load all dashboard data.
    This is the primary interface for app.py.
    
    Args:
        data_dir: Directory containing data files
        max_distance_to_farm_m: Maximum distance to farm in meters
        
    Returns:
        Dictionary containing all dashboard data
    """
    loader = DashboardDataLoader(data_dir)
    return loader.load_all_data(max_distance_to_farm_m)


# Additional convenience functions
def load_wells_only(data_dir: Union[str, Path] = "geodash/data", max_distance_to_farm_m: Optional[float] = None):
    """Load only wells data."""
    loader = DashboardDataLoader(data_dir)
    wells_df = loader.wells_loader.load(max_distance_to_farm_m)
    return {"wells_df": wells_df}


def load_farm_data(data_dir: Union[str, Path] = "geodash/data"):
    """Load farm polygons and time series data."""
    loader = DashboardDataLoader(data_dir)
    farm_polygons = loader.farms_loader.load()
    wells_df = loader.wells_loader.load()
    farm_time_series = loader._generate_farm_time_series(wells_df)
    return {
        "farm_polygons": farm_polygons,
        "farm_time_series": farm_time_series
    }


def get_data_status(data_dir: Union[str, Path] = "geodash/data") -> Dict[str, Dict[str, str]]:
    """Get status information about available data sources."""
    loader = DashboardDataLoader(data_dir)
    
    source_info = {
        "wells": {
            "file": str(loader.wells_loader.csv_file),
            "status": "available" if loader.wells_loader._file_exists(loader.wells_loader.csv_file) else "missing",
            "type": "CSV"
        },
        "polygons": {
            "directory": str(loader.polygons_loader.rdc_fields_dir),
            "status": "available" if loader.polygons_loader.rdc_fields_dir.exists() else "missing",
            "type": "Geospatial"
        },
        "farms": {
            "file": str(loader.farms_loader.farms_shapefile),
            "status": "available" if loader.farms_loader._file_exists(loader.farms_loader.farms_shapefile) else "missing",
            "type": "Shapefile"
        }
    }
    
    return source_info


# Export main interface and utilities
__all__ = [
    "DashboardDataLoader",
    "load_dashboard_data",
    "load_wells_only", 
    "load_farm_data",
    "get_data_status",
]