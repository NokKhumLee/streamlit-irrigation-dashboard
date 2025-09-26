"""
Main data loader/handler for the geological dashboard.
This is the primary interface that app.py should use to load data.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Union, Optional
import warnings

import numpy as np
import pandas as pd

# Try to import geospatial libraries, fallback gracefully if not available
try:
    import geopandas as gpd
    GEOSPATIAL_AVAILABLE = True
except ImportError:
    GEOSPATIAL_AVAILABLE = False
    warnings.warn("GeoPandas not available. Real geospatial data loading disabled.")

from .mockup import generate_mock_data as generate_fallback_data


class DataLoader:
    """Main data loader class that handles both real and mock data."""
    
    def __init__(self, data_dir: Union[str, Path] = "geodash/data"):
        self.data_dir = Path(data_dir)
        self.rdc_fields_dir = self.data_dir / "RDC_Fields"
        self.wells_data_dir = self.data_dir / "wells"  # For future real wells data
        
    def load_all_data(self) -> Dict[str, object]:
        """
        Main method to load all dashboard data.
        Tries to load real data first, falls back to mock data if needed.
        
        Returns:
            Dict containing all dashboard data:
            - polygons: field polygons
            - wells_df: well data 
            - water_levels: time series data
            - heat_points: heatmap data
            - cost_df: cost estimation data
            - prob_df: probability data
        """
        print("🔄 Loading dashboard data...")
        
        # Load field polygons (real data)
        polygons = self._load_field_polygons()
        
        # Load other data (mock for now, but can be replaced with real data loaders)
        mock_data = generate_fallback_data()
        
        # Combine real and mock data
        data = {
            "polygons": polygons,
            "wells_df": mock_data["wells_df"],
            "water_levels": mock_data["water_levels"], 
            "heat_points": mock_data["heat_points"],
            "cost_df": mock_data["cost_df"],
            "prob_df": mock_data["prob_df"],
        }
        
        print(f"✅ Data loaded: {len(polygons)} polygons, {len(data['wells_df'])} wells")
        return data
    
    def _load_field_polygons(self) -> List[Dict[str, object]]:
        """Load field polygon data from RDC_Fields directory."""
        if not GEOSPATIAL_AVAILABLE:
            print("⚠️  GeoPandas not available. Using mock polygon data.")
            return generate_fallback_data()["polygons"]
            
        if not self.rdc_fields_dir.exists():
            print(f"⚠️  {self.rdc_fields_dir} not found. Using mock polygon data.")
            return generate_fallback_data()["polygons"]
        
        polygons = []
        
        # Try to load different file formats
        for file_path in self.rdc_fields_dir.iterdir():
            if file_path.suffix.lower() in ['.geojson', '.json']:
                polygons.extend(self._load_geojson(file_path))
            elif file_path.suffix.lower() == '.shp':
                polygons.extend(self._load_shapefile(file_path))
            elif file_path.suffix.lower() == '.gpkg':
                polygons.extend(self._load_geopackage(file_path))
        
        if not polygons:
            print(f"⚠️  No valid polygon files found in {self.rdc_fields_dir}. Using mock data.")
            return generate_fallback_data()["polygons"]
        
        return polygons
    
    def _load_geojson(self, file_path: Path) -> List[Dict[str, object]]:
        """Load polygons from GeoJSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            polygons = []
            features = geojson_data.get('features', [])
            
            for i, feature in enumerate(features):
                geometry = feature.get('geometry', {})
                properties = feature.get('properties', {})
                
                if geometry.get('type') in ['Polygon', 'MultiPolygon']:
                    coords = self._extract_geojson_coordinates(geometry)
                    if coords:
                        name = properties.get('name', properties.get('field_name', 
                               properties.get('id', f"Field_{i+1}")))
                        region = properties.get('region', properties.get('zone', 
                                 self._classify_region_by_coords(coords)))
                        
                        polygons.append({
                            "name": str(name),
                            "region": str(region),
                            "coordinates": coords
                        })
            
            print(f"📍 Loaded {len(polygons)} polygons from {file_path.name}")
            return polygons
            
        except Exception as e:
            print(f"❌ Error loading GeoJSON {file_path}: {e}")
            return []
    
    def _load_shapefile(self, file_path: Path) -> List[Dict[str, object]]:
        """Load polygons from Shapefile."""
        if not GEOSPATIAL_AVAILABLE:
            return []
            
        try:
            gdf = gpd.read_file(file_path)
            return self._geopandas_to_polygons(gdf, file_path.name)
        except Exception as e:
            print(f"❌ Error loading Shapefile {file_path}: {e}")
            return []
    
    def _load_geopackage(self, file_path: Path) -> List[Dict[str, object]]:
        """Load polygons from GeoPackage.""" 
        if not GEOSPATIAL_AVAILABLE:
            return []
            
        try:
            gdf = gpd.read_file(file_path)
            return self._geopandas_to_polygons(gdf, file_path.name)
        except Exception as e:
            print(f"❌ Error loading GeoPackage {file_path}: {e}")
            return []
    
    def _geopandas_to_polygons(self, gdf: gpd.GeoDataFrame, filename: str) -> List[Dict[str, object]]:
        """Convert GeoPandas DataFrame to polygon list."""
        try:
            # Convert to WGS84 if not already
            if gdf.crs is not None and gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            
            polygons = []
            
            for i, row in gdf.iterrows():
                try:
                    geometry = row.geometry
                    
                    if geometry is None or geometry.is_empty:
                        continue
                        
                    if geometry.geom_type in ['Polygon', 'MultiPolygon']:
                        coords = self._extract_shapely_coordinates(geometry)
                        if coords and len(coords) >= 3:  # Valid polygon needs at least 3 points
                            # Try common field names for name and region based on RDC data structure
                            name_fields = ['farm_name', 'plot_code', 'zone_name', 'name', 'field_name', 'NAME', 'FIELD_NAME', 'id', 'ID']
                            region_fields = ['zone_name', 'farm_name', 'region', 'zone', 'REGION', 'ZONE', 'area', 'AREA']
                            
                            name = None
                            for field in name_fields:
                                if field in row.index and pd.notna(row[field]):
                                    name = str(row[field])
                                    break
                            
                            region = None
                            for field in region_fields:
                                if field in row.index and pd.notna(row[field]):
                                    region = str(row[field])
                                    break
                            
                            # Fallbacks
                            if not name:
                                name = f"Field_{i+1}"
                            if not region:
                                region = self._classify_region_by_coords(coords)
                            
                            polygons.append({
                                "name": name,
                                "region": region,
                                "coordinates": coords
                            })
                            
                except Exception as e:
                    print(f"⚠️  Error processing row {i}: {e}")
                    continue
            
            print(f"📍 Successfully loaded {len(polygons)} polygons from {filename}")
            return polygons
            
        except Exception as e:
            print(f"❌ Error processing GeoDataFrame from {filename}: {e}")
            return []
    
    def _extract_geojson_coordinates(self, geometry: Dict) -> List[List[float]]:
        """Extract coordinates from GeoJSON geometry."""
        try:
            geom_type = geometry.get('type')
            coordinates = geometry.get('coordinates', [])
            
            if geom_type == 'Polygon':
                if coordinates and len(coordinates[0]) > 0:
                    return [[float(coord[1]), float(coord[0])] for coord in coordinates[0][:-1]]
            
            elif geom_type == 'MultiPolygon':
                if coordinates and len(coordinates[0]) > 0 and len(coordinates[0][0]) > 0:
                    return [[float(coord[1]), float(coord[0])] for coord in coordinates[0][0][:-1]]
            
        except Exception as e:
            print(f"⚠️  Error extracting GeoJSON coordinates: {e}")
            return []
        
        return []
    
    def _extract_shapely_coordinates(self, geometry):
        """Extract coordinates from Shapely geometry."""
        try:
            if geometry is None or geometry.is_empty:
                return []
                
            if geometry.geom_type == 'Polygon':
                coords = list(geometry.exterior.coords)[:-1]  # Remove closing coordinate
                if coords and len(coords) > 0:
                    return [[float(coord[1]), float(coord[0])] for coord in coords]  # Convert lon,lat to lat,lon
            
            elif geometry.geom_type == 'MultiPolygon':
                geoms_list = list(geometry.geoms)
                if geoms_list:
                    first_polygon = geoms_list[0]
                    coords = list(first_polygon.exterior.coords)[:-1]
                    if coords and len(coords) > 0:
                        return [[float(coord[1]), float(coord[0])] for coord in coords]
            
        except Exception as e:
            print(f"⚠️  Error extracting Shapely coordinates: {e}")
            return []
        
        return []
    
    def _classify_region_by_coords(self, coords: List[List[float]]) -> str:
        """Classify region based on coordinate centroid."""
        if not coords:
            return "Unknown"
        
        try:
            # Calculate centroid
            lat_avg = sum(coord[0] for coord in coords) / len(coords)
            lon_avg = sum(coord[1] for coord in coords) / len(coords)
            
            # Simple geographic classification for Thailand
            # This is generic and works for any location in Thailand
            if lat_avg > 16.0:
                return "North"
            elif lon_avg > 100.5:
                return "East"
            elif lat_avg < 15.0:
                return "South"
            else:
                return "Central"
        except Exception:
            return "Unknown"


# Main function that app.py should call
def load_dashboard_data(data_dir: Union[str, Path] = "geodash/data") -> Dict[str, object]:
    """
    Main function to load all dashboard data.
    This is the primary interface for app.py.
    
    Args:
        data_dir: Directory containing data files
        
    Returns:
        Dictionary containing all dashboard data
    """
    loader = DataLoader(data_dir)
    return loader.load_all_data()