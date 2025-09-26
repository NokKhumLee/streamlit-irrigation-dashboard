"""
Field polygons data loader for GeoJSON, Shapefile, and GeoPackage files.
Handles loading field boundary polygons from various geospatial formats.
"""
from pathlib import Path
from typing import Dict, List

from .base import BaseGeospatialLoader, DataValidationMixin
from .utils import (
    load_geojson_file,
    classify_region_by_coords,
    validate_polygon_coordinates,
    log_data_summary
)
from ..mockup import generate_mock_data


class PolygonsLoader(BaseGeospatialLoader, DataValidationMixin):
    """Loader for field boundary polygons from geospatial files."""
    
    def __init__(self, data_dir: str = "geodash/data"):
        super().__init__(data_dir)
        self.supported_extensions = ['.geojson', '.json', '.shp', '.gpkg']
    
    def load(self) -> List[Dict[str, object]]:
        """
        Load field polygons from RDC_Fields directory.
        
        Returns:
            List of polygon dictionaries with name, region, and coordinates
        """
        if not self.rdc_fields_dir.exists():
            self._log_fallback("field polygons", f"Directory not found: {self.rdc_fields_dir}")
            return self._load_fallback_data()
        
        polygons = []
        
        # Find all supported geospatial files
        geospatial_files = self._find_files_with_extensions(
            self.rdc_fields_dir, 
            self.supported_extensions
        )
        
        if not geospatial_files:
            self._log_fallback("field polygons", f"No supported files found in {self.rdc_fields_dir}")
            return self._load_fallback_data()
        
        # Process each file
        for file_path in geospatial_files:
            try:
                file_polygons = self._load_polygons_from_file(file_path)
                polygons.extend(file_polygons)
                
            except Exception as e:
                self.logger.warning(f"⚠️  Error loading {file_path}: {e}")
                continue
        
        if not polygons:
            self._log_fallback("field polygons", "No valid polygons found in any file")
            return self._load_fallback_data()
        
        log_data_summary("field polygons", len(polygons), polygons, "real")
        return polygons
    
    def _load_fallback_data(self) -> List[Dict[str, object]]:
        """Load mock field polygons data."""
        mock_data = generate_mock_data()
        polygons = mock_data["polygons"]
        log_data_summary("field polygons", len(polygons), polygons, "mock")
        return polygons
    
    def _load_polygons_from_file(self, file_path: Path) -> List[Dict[str, object]]:
        """
        Load polygons from a single geospatial file.
        
        Args:
            file_path: Path to the geospatial file
            
        Returns:
            List of polygon dictionaries
        """
        self._log_loading_attempt("field polygons", file_path)
        
        file_ext = file_path.suffix.lower()
        
        if file_ext in ['.geojson', '.json']:
            return self._load_from_geojson(file_path)
        elif file_ext == '.shp':
            return self._load_from_shapefile(file_path)
        elif file_ext == '.gpkg':
            return self._load_from_geopackage(file_path)
        else:
            self.logger.warning(f"⚠️  Unsupported file format: {file_ext}")
            return []
    
    def _load_from_geojson(self, file_path: Path) -> List[Dict[str, object]]:
        """Load polygons from GeoJSON file."""
        try:
            polygons = load_geojson_file(file_path)
            self._log_success("field polygons", len(polygons), "real")
            return polygons
        except Exception as e:
            self.logger.error(f"❌ Error loading GeoJSON {file_path}: {e}")
            return []
    
    def _load_from_shapefile(self, file_path: Path) -> List[Dict[str, object]]:
        """Load polygons from Shapefile."""
        try:
            gdf = self._load_geospatial_file(file_path)
            if gdf is None:
                return []
            
            polygons = self._geopandas_to_polygons(gdf, file_path.name)
            self._log_success("field polygons", len(polygons), "real")
            return polygons
            
        except Exception as e:
            self.logger.error(f"❌ Error loading Shapefile {file_path}: {e}")
            return []
    
    def _load_from_geopackage(self, file_path: Path) -> List[Dict[str, object]]:
        """Load polygons from GeoPackage."""
        try:
            gdf = self._load_geospatial_file(file_path)
            if gdf is None:
                return []
            
            polygons = self._geopandas_to_polygons(gdf, file_path.name)
            self._log_success("field polygons", len(polygons), "real")
            return polygons
            
        except Exception as e:
            self.logger.error(f"❌ Error loading GeoPackage {file_path}: {e}")
            return []
    
    def _geopandas_to_polygons(self, gdf, filename: str) -> List[Dict[str, object]]:
        """
        Convert GeoPandas DataFrame to polygon list.
        
        Args:
            gdf: GeoPandas GeoDataFrame
            filename: Name of the source file for logging
            
        Returns:
            List of polygon dictionaries
        """
        polygons = []
        
        for i, row in gdf.iterrows():
            try:
                geometry = row.geometry
                
                if geometry is None or geometry.is_empty:
                    continue
                
                if geometry.geom_type in ['Polygon', 'MultiPolygon']:
                    coords = self._extract_coordinates_from_geometry(geometry)
                    
                    if coords and validate_polygon_coordinates(coords):
                        # Try common field names for name and region
                        name = self._find_polygon_name(row, i)
                        region = self._find_polygon_region(row, coords)
                        
                        polygons.append({
                            "name": name,
                            "region": region,
                            "coordinates": coords
                        })
                        
            except Exception as e:
                self.logger.warning(f"⚠️  Error processing polygon {i} in {filename}: {e}")
                continue
        
        self.logger.info(f"📍 Successfully loaded {len(polygons)} polygons from {filename}")
        return polygons
    
    def _find_polygon_name(self, row, index: int) -> str:
        """Find or generate polygon name from row data."""
        name_fields = [
            'farm_name', 'plot_code', 'zone_name', 'name', 'field_name', 
            'NAME', 'FIELD_NAME', 'id', 'ID'
        ]
        
        name = self._find_field_value(row, name_fields)
        return name if name else f"Field_{index+1}"
    
    def _find_polygon_region(self, row, coords: List[List[float]]) -> str:
        """Find or classify polygon region from row data."""
        region_fields = [
            'zone_name', 'farm_name', 'region', 'zone', 'REGION', 
            'ZONE', 'area', 'AREA', 'amphoe', 'district'
        ]
        
        region = self._find_field_value(row, region_fields)
        return region if region else classify_region_by_coords(coords)


# Export the loader class
__all__ = ["PolygonsLoader"]