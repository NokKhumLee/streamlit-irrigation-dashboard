"""
Farm polygons data loader with color assignment.
Handles loading farm boundary polygons from shapefiles with distinct colors.
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List

from .base import BaseGeospatialLoader, DataValidationMixin, ColorManager
from .utils import validate_polygon_coordinates, log_data_summary
from ..mockup import generate_mock_data


class FarmsLoader(BaseGeospatialLoader, DataValidationMixin):
    """Loader for farm boundary polygons with color assignment."""
    
    def __init__(self, data_dir: str = "geodash/data"):
        super().__init__(data_dir)
        self.farms_shapefile = self.rdc_farms_dir / "farm_convex_hulls.shp"
    
    def load(self) -> List[Dict[str, object]]:
        """
        Load farm polygons from RDC_Farms directory with distinct colors.
        
        Returns:
            List of farm polygon dictionaries with colors and styling
        """
        if not self._file_exists(self.farms_shapefile):
            self._log_fallback("farm polygons", f"File not found: {self.farms_shapefile}")
            return self._load_fallback_data()
        
        try:
            self._log_loading_attempt("farm polygons", self.farms_shapefile)
            gdf = self._load_geospatial_file(self.farms_shapefile)
            
            if gdf is None:
                self._log_fallback("farm polygons", "Failed to load shapefile")
                return self._load_fallback_data()
            
            farm_polygons = self._process_farm_polygons(gdf)
            
            if not farm_polygons:
                self._log_fallback("farm polygons", "No valid polygons found after processing")
                return self._load_fallback_data()
            
            log_data_summary("farm polygons", len(farm_polygons), farm_polygons, "real")
            return farm_polygons
            
        except Exception as e:
            self._log_fallback("farm polygons", f"Error loading farm data: {e}")
            return self._load_fallback_data()
    
    def _load_fallback_data(self) -> List[Dict[str, object]]:
        """Load mock farm polygons data."""
        # Return empty list since mock data doesn't include farm polygons
        # This ensures the app still works but without farm boundaries
        log_data_summary("farm polygons", 0, [], "mock")
        return []
    
    def _process_farm_polygons(self, gdf) -> List[Dict[str, object]]:
        """
        Process farm polygons from GeoPandas DataFrame.
        
        Args:
            gdf: GeoPandas GeoDataFrame from shapefile
            
        Returns:
            List of farm polygon dictionaries with styling
        """
        farm_polygons = []
        
        for i, row in gdf.iterrows():
            try:
                geometry = row.geometry
                
                if geometry is None or geometry.is_empty:
                    continue
                
                if geometry.geom_type in ['Polygon', 'MultiPolygon']:
                    coords = self._extract_coordinates_from_geometry(geometry)
                    
                    if coords and validate_polygon_coordinates(coords):
                        # Find farm name
                        farm_name = self._find_farm_name(row, i)
                        
                        # Assign color from palette
                        color = ColorManager.get_farm_color(i)
                        
                        farm_polygon = {
                            "name": farm_name,
                            "farm_id": i + 1,
                            "coordinates": coords,
                            "color": color,
                            "fill_color": color,
                            "fill_opacity": 0.3,
                            "weight": 2
                        }
                        
                        farm_polygons.append(farm_polygon)
                        
            except Exception as e:
                self.logger.warning(f"⚠️  Error processing farm row {i}: {e}")
                continue
        
        self.logger.info(f"🚜 Successfully processed {len(farm_polygons)} farm polygons")
        return farm_polygons
    
    def _find_farm_name(self, row, index: int) -> str:
        """
        Find farm name from row data or generate one.
        
        Args:
            row: Pandas Series representing a row from the GeoDataFrame
            index: Row index for fallback naming
            
        Returns:
            Farm name string
        """
        farm_name_fields = [
            'farm_name', 'farm_id', 'name', 'Farm_Name', 'FARM_NAME', 
            'id', 'ID', 'zone_name', 'area_name'
        ]
        
        farm_name = self._find_field_value(row, farm_name_fields)
        return farm_name if farm_name else f"Farm_{index+1}"
    
    def get_color_palette(self) -> List[str]:
        """
        Get the color palette used for farm polygons.
        
        Returns:
            List of hex color codes
        """
        return ColorManager.FARM_COLORS.copy()
    
    def get_farm_styling_defaults(self) -> Dict[str, object]:
        """
        Get default styling parameters for farm polygons.
        
        Returns:
            Dictionary of default styling parameters
        """
        return {
            "fill_opacity": 0.3,
            "weight": 2,
            "fillColor": None,  # Will be set per farm
            "color": None,      # Will be set per farm
        }


# Export the loader class
__all__ = ["FarmsLoader"]