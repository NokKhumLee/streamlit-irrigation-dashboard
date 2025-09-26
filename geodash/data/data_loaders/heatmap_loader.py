"""
Heatmap data loader for probability/density visualization.
Generates heatmap points based on well locations and success patterns.
"""
import numpy as np
import pandas as pd
from typing import List, Tuple

from .base import BaseDataLoader
from .utils import calculate_data_bounds, log_data_summary
from ..mockup import generate_mock_data


class HeatmapLoader(BaseDataLoader):
    """Loader for heatmap probability data based on well locations."""
    
    def __init__(self, data_dir: str = "geodash/data"):
        super().__init__(data_dir)
        self.base_points_count = 300
        self.points_per_well = 3
    
    def load(self, wells_df: pd.DataFrame = None) -> List[List[float]]:
        """
        Generate heatmap points based on well locations and success patterns.
        
        Args:
            wells_df: DataFrame of wells data to base heatmap on
            
        Returns:
            List of [lat, lon, weight] points for heatmap visualization
        """
        if wells_df is None or wells_df.empty:
            self._log_fallback("heatmap data", "No wells data provided")
            return self._load_fallback_data()
        
        try:
            self._log_loading_attempt("heatmap data")
            heat_points = self._generate_heat_points_for_wells(wells_df)
            
            log_data_summary("heatmap points", len(heat_points), None, "generated")
            return heat_points
            
        except Exception as e:
            self._log_fallback("heatmap data", f"Error generating data: {e}")
            return self._load_fallback_data()
    
    def _load_fallback_data(self) -> List[List[float]]:
        """Load mock heatmap data."""
        mock_data = generate_mock_data()
        heat_points = mock_data["heat_points"]
        log_data_summary("heatmap points", len(heat_points), None, "mock")
        return heat_points
    
    def _generate_heat_points_for_wells(self, wells_df: pd.DataFrame) -> List[List[float]]:
        """
        Generate heatmap points based on well locations and success rates.
        
        Args:
            wells_df: DataFrame containing well information
            
        Returns:
            List of [lat, lon, weight] points
        """
        heat_points = []
        
        # Get data bounds for generating background points
        min_lat, max_lat, min_lon, max_lon = calculate_data_bounds(wells_df)
        
        # Generate background points across the study area
        background_points = self._generate_background_points(
            min_lat, max_lat, min_lon, max_lon
        )
        heat_points.extend(background_points)
        
        # Add points based on well locations and success
        well_based_points = self._generate_well_based_points(wells_df)
        heat_points.extend(well_based_points)
        
        return heat_points
    
    def _generate_background_points(
        self, 
        min_lat: float, 
        max_lat: float, 
        min_lon: float, 
        max_lon: float
    ) -> List[List[float]]:
        """
        Generate background heatmap points across the study area.
        
        Args:
            min_lat, max_lat, min_lon, max_lon: Geographic bounds
            
        Returns:
            List of background heat points
        """
        background_points = []
        
        # Generate random points within bounds
        rng = np.random.default_rng(42)  # Seed for reproducibility
        
        for _ in range(self.base_points_count):
            lat = rng.uniform(min_lat, max_lat)
            lon = rng.uniform(min_lon, max_lon)
            
            # Base weight for background (lower than well-based points)
            weight = float(rng.uniform(0.1, 0.4))
            
            background_points.append([lat, lon, weight])
        
        return background_points
    
    def _generate_well_based_points(self, wells_df: pd.DataFrame) -> List[List[float]]:
        """
        Generate heatmap points based on existing well locations.
        
        Args:
            wells_df: DataFrame containing well information
            
        Returns:
            List of well-based heat points
        """
        well_points = []
        rng = np.random.default_rng(42)
        
        for _, well in wells_df.iterrows():
            lat, lon = well['lat'], well['lon']
            survived = well['survived']
            depth = well['depth_m']
            
            # Add point at exact well location
            well_weight = self._calculate_well_weight(survived, depth)
            well_points.append([lat, lon, well_weight])
            
            # Add nearby points to create clustering effect
            nearby_points = self._generate_nearby_points(
                lat, lon, survived, depth, rng
            )
            well_points.extend(nearby_points)
        
        return well_points
    
    def _calculate_well_weight(self, survived: bool, depth: float) -> float:
        """
        Calculate heatmap weight for a well based on its characteristics.
        
        Args:
            survived: Whether the well is successful
            depth: Well depth in meters
            
        Returns:
            Weight value for heatmap (0.0 to 1.0)
        """
        if survived:
            base_weight = 0.8
            
            # Bonus for wells in optimal depth range
            if 80 <= depth <= 150:
                base_weight = 0.9
            elif depth > 200:
                base_weight = 0.7  # Very deep wells are less predictive
                
        else:
            base_weight = 0.3
            
            # Failed shallow wells indicate poor area
            if depth < 60:
                base_weight = 0.2
        
        # Add small random variation
        variation = np.random.normal(0, 0.05)
        final_weight = np.clip(base_weight + variation, 0.1, 1.0)
        
        return float(final_weight)
    
    def _generate_nearby_points(
        self, 
        center_lat: float, 
        center_lon: float, 
        survived: bool, 
        depth: float,
        rng: np.random.Generator
    ) -> List[List[float]]:
        """
        Generate points near a well location to create clustering effect.
        
        Args:
            center_lat, center_lon: Central well coordinates
            survived: Whether the central well is successful
            depth: Central well depth
            rng: Random number generator
            
        Returns:
            List of nearby heat points
        """
        nearby_points = []
        
        # Generate multiple points around each well
        for _ in range(self.points_per_well):
            # Small offset around each well (within ~1km radius)
            lat_offset = rng.normal(0, 0.005)  # ~0.5km standard deviation
            lon_offset = rng.normal(0, 0.005)
            
            nearby_lat = center_lat + lat_offset
            nearby_lon = center_lon + lon_offset
            
            # Weight decreases with distance from well
            distance_factor = rng.uniform(0.6, 0.9)
            base_weight = self._calculate_well_weight(survived, depth)
            nearby_weight = base_weight * distance_factor
            
            nearby_points.append([nearby_lat, nearby_lon, float(nearby_weight)])
        
        return nearby_points
    
    def _add_geological_patterns(self, heat_points: List[List[float]]) -> List[List[float]]:
        """
        Add geological patterns to enhance realism (optional enhancement).
        
        Args:
            heat_points: Existing heat points
            
        Returns:
            Enhanced heat points with geological patterns
        """
        # This could be enhanced to add:
        # - River/water body proximity effects
        # - Elevation-based patterns
        # - Geological formation influences
        # For now, return points as-is
        return heat_points
    
    def set_point_density(self, base_points: int, points_per_well: int) -> None:
        """
        Configure the density of heatmap points.
        
        Args:
            base_points: Number of background points to generate
            points_per_well: Number of additional points around each well
        """
        if base_points > 0:
            self.base_points_count = base_points
        
        if points_per_well > 0:
            self.points_per_well = points_per_well
    
    def get_heatmap_statistics(self, heat_points: List[List[float]]) -> dict:
        """
        Get statistics about generated heatmap data.
        
        Args:
            heat_points: List of heat points
            
        Returns:
            Dictionary with heatmap statistics
        """
        if not heat_points:
            return {"count": 0}
        
        weights = [point[2] for point in heat_points]
        
        return {
            "count": len(heat_points),
            "weight_min": min(weights),
            "weight_max": max(weights),
            "weight_mean": np.mean(weights),
            "weight_std": np.std(weights),
            "high_probability_points": sum(1 for w in weights if w > 0.7)
        }


# Export the loader class
__all__ = ["HeatmapLoader"]