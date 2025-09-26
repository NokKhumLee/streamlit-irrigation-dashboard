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
        self.rdc_farms_dir = self.data_dir / "RDC_Farms"  # New: farm polygons directory
        self.groundwater_dir = self.data_dir / "groundwater"
        
        # 20 distinct colors for farms (hex values)
        self.farm_colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
            "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
            "#F8C471", "#82E0AA", "#F1948A", "#85C1E9", "#F4D03F",
            "#D7BDE2", "#7FB3D3", "#A9DFBF", "#F9E79F", "#FADBD8"
        ]
        
    def load_all_data(self) -> Dict[str, object]:
        """
        Main method to load all dashboard data.
        Tries to load real data first, falls back to mock data if needed.
        
        Returns:
            Dict containing all dashboard data:
            - polygons: field polygons
            - farm_polygons: farm polygons with colors
            - wells_df: well data 
            - water_levels: time series data
            - heat_points: heatmap data
            - cost_df: cost estimation data
            - prob_df: probability data
        """
        print("🔄 Loading dashboard data...")
        
        # Load field polygons (real data)
        polygons = self._load_field_polygons()
        
        # Load farm polygons (NEW)
        farm_polygons = self._load_farm_polygons()
        
        # Load wells data (try real data first, then fallback to mock)
        wells_df = self._load_wells_data()
        print(f"🔍 Wells data source: {'REAL CSV' if not wells_df.empty and 'Mock' not in str(wells_df.iloc[0]['well_id']) else 'MOCK'}")
        
        # Load other data (mock for now, but can be replaced with real data loaders)
        mock_data = generate_fallback_data()
        
        # Generate derived data based on real wells if available
        water_levels = self._generate_water_levels_for_wells(wells_df)
        heat_points = self._generate_heat_points_for_wells(wells_df)
        cost_df = mock_data["cost_df"]  # Keep mock cost data for now
        prob_df = mock_data["prob_df"]  # Keep mock probability data for now
        
        # Combine real and mock data
        data = {
            "polygons": polygons,
            "farm_polygons": farm_polygons,  # NEW
            "wells_df": wells_df,
            "water_levels": water_levels,
            "heat_points": heat_points,
            "cost_df": cost_df,
            "prob_df": prob_df,
        }
        
        print(f"✅ Data loaded: {len(polygons)} field polygons, {len(farm_polygons)} farm polygons, {len(data['wells_df'])} wells")
        print(f"📍 Sample well IDs: {list(data['wells_df']['well_id'].head(3))}")
        return data
    
    def _load_farm_polygons(self) -> List[Dict[str, object]]:
        """Load farm polygon data from RDC_Farms directory with distinct colors."""
        if not GEOSPATIAL_AVAILABLE:
            print("⚠️  GeoPandas not available. Farm polygons disabled.")
            return []
            
        farm_convex_hulls_path = self.rdc_farms_dir / "farm_convex_hulls.shp"
        
        if not farm_convex_hulls_path.exists():
            print(f"⚠️  {farm_convex_hulls_path} not found. Farm polygons disabled.")
            return []
        
        try:
            # Load the farm convex hulls shapefile
            gdf = gpd.read_file(farm_convex_hulls_path)
            
            # Convert to WGS84 if not already
            if gdf.crs is not None and gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            
            farm_polygons = []
            
            for i, row in gdf.iterrows():
                try:
                    geometry = row.geometry
                    
                    if geometry is None or geometry.is_empty:
                        continue
                        
                    if geometry.geom_type in ['Polygon', 'MultiPolygon']:
                        coords = self._extract_shapely_coordinates(geometry)
                        if coords and len(coords) >= 3:  # Valid polygon needs at least 3 points
                            
                            # Try common field names for farm identification
                            farm_name_fields = ['farm_name', 'farm_id', 'name', 'Farm_Name', 'FARM_NAME', 'id', 'ID']
                            farm_name = None
                            
                            for field in farm_name_fields:
                                if field in row.index and pd.notna(row[field]):
                                    farm_name = str(row[field])
                                    break
                            
                            # Fallback farm name
                            if not farm_name:
                                farm_name = f"Farm_{i+1}"
                            
                            # Assign color from our predefined palette
                            color = self.farm_colors[i % len(self.farm_colors)]
                            
                            farm_polygons.append({
                                "name": farm_name,
                                "farm_id": i + 1,
                                "coordinates": coords,
                                "color": color,
                                "fill_color": color,
                                "fill_opacity": 0.3,
                                "weight": 2
                            })
                            
                except Exception as e:
                    print(f"⚠️  Error processing farm row {i}: {e}")
                    continue
            
            print(f"🚜 Successfully loaded {len(farm_polygons)} farm polygons")
            return farm_polygons
            
        except Exception as e:
            print(f"❌ Error loading farm polygons from {farm_convex_hulls_path}: {e}")
            return []
    
    def _load_wells_data(self) -> pd.DataFrame:
        """Load wells data from CSV file or fallback to mock data."""
        gov_groundwater_file = self.groundwater_dir / "gov_groundwater_scope.csv"
        
        if gov_groundwater_file.exists():
            try:
                # Load the government groundwater CSV
                df = pd.read_csv(gov_groundwater_file, encoding='utf-8')
                print(f"📊 Loading real groundwater data from {gov_groundwater_file}")
                
                # Clean and standardize the data
                wells_df = self._process_groundwater_csv(df)
                
                if not wells_df.empty:
                    print(f"✅ Successfully loaded {len(wells_df)} wells from government data")
                    return wells_df
                else:
                    print("⚠️  No valid wells found in government data. Using mock data.")
                    
            except Exception as e:
                print(f"❌ Error loading government groundwater data: {e}")
                
        else:
            print(f"⚠️  Government groundwater file not found at {gov_groundwater_file}. Using mock data.")
        
        # Fallback to mock data
        print("🔄 Using mock wells data")
        return generate_fallback_data()["wells_df"]
    
    def _process_groundwater_csv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean the government groundwater CSV data."""
        try:
            # Create a copy to avoid modifying original
            processed_df = df.copy()
            
            # Column mapping from Thai CSV to our standard format
            column_mapping = {
                'หมายเลขบ่อ': 'well_id',
                'ตำบล': 'tambon',
                'อำเภอ': 'amphoe', 
                'จังหวัด': 'province',
                'ประเภทบ่อ': 'well_type',
                'ความลึกเจาะ': 'depth_drilled',
                'ความลึกพัฒนา': 'depth_developed',
                'ปริมาณน้ำ': 'water_volume',
                'Latitude': 'lat',
                'Longitude': 'lon'
            }
            
            # Rename columns
            processed_df = processed_df.rename(columns=column_mapping)
            
            # Ensure required columns exist
            required_cols = ['well_id', 'lat', 'lon']
            missing_cols = [col for col in required_cols if col not in processed_df.columns]
            if missing_cols:
                print(f"❌ Missing required columns: {missing_cols}")
                return pd.DataFrame()
            
            # Clean and convert data types
            processed_df['lat'] = pd.to_numeric(processed_df['lat'], errors='coerce')
            processed_df['lon'] = pd.to_numeric(processed_df['lon'], errors='coerce')
            
            # Use depth_drilled as primary depth, fallback to depth_developed
            if 'depth_drilled' in processed_df.columns:
                processed_df['depth_m'] = pd.to_numeric(processed_df['depth_drilled'], errors='coerce')
            elif 'depth_developed' in processed_df.columns:
                processed_df['depth_m'] = pd.to_numeric(processed_df['depth_developed'], errors='coerce')
            else:
                # Generate random depths if no depth data available
                processed_df['depth_m'] = np.random.randint(40, 200, size=len(processed_df))
                print("⚠️  No depth data found, using random depths")
            
            # Create region from amphoe (district)
            if 'amphoe' in processed_df.columns:
                processed_df['region'] = processed_df['amphoe'].fillna('Unknown')
            else:
                processed_df['region'] = 'Unknown'
            
            # Generate survival status based on water volume if available
            if 'water_volume' in processed_df.columns:
                water_vol = pd.to_numeric(processed_df['water_volume'], errors='coerce')
                # Wells with water volume > 1 m³/h are considered successful
                processed_df['survived'] = (water_vol > 1.0).fillna(True)
            else:
                # Random survival rate if no water volume data
                processed_df['survived'] = np.random.choice([True, False], 
                                                           size=len(processed_df), 
                                                           p=[0.75, 0.25])
            
            # Remove rows with invalid coordinates
            processed_df = processed_df.dropna(subset=['lat', 'lon'])
            processed_df = processed_df[
                (processed_df['lat'].between(-90, 90)) & 
                (processed_df['lon'].between(-180, 180))
            ]
            
            # Fill missing depth values
            processed_df['depth_m'] = processed_df['depth_m'].fillna(
                processed_df['depth_m'].median()
            )
            
            # Select final columns
            final_cols = ['well_id', 'region', 'lat', 'lon', 'depth_m', 'survived']
            processed_df = processed_df[final_cols]
            
            # Ensure well_id is string
            processed_df['well_id'] = processed_df['well_id'].astype(str)
            
            print(f"📊 Processed {len(processed_df)} wells successfully")
            print(f"📍 Coordinate range: Lat {processed_df['lat'].min():.3f}-{processed_df['lat'].max():.3f}, "
                  f"Lon {processed_df['lon'].min():.3f}-{processed_df['lon'].max():.3f}")
            print(f"🏔️  Depth range: {processed_df['depth_m'].min():.1f}-{processed_df['depth_m'].max():.1f}m")
            print(f"✅ Success rate: {processed_df['survived'].mean():.1%}")
            
            return processed_df
            
        except Exception as e:
            print(f"❌ Error processing groundwater CSV: {e}")
            return pd.DataFrame()
    
    def _generate_water_levels_for_wells(self, wells_df: pd.DataFrame) -> pd.DataFrame:
        """Generate time series water level data for the wells."""
        if wells_df.empty:
            return generate_fallback_data()["water_levels"]
        
        # Generate 12 months of data
        months = pd.date_range(end=pd.Timestamp.today().normalize(), periods=12, freq="MS")
        well_ids = wells_df['well_id'].tolist()
        
        # Generate realistic water levels based on well depth and survival
        water_levels_data = []
        
        for well_id in well_ids:
            well_info = wells_df[wells_df['well_id'] == well_id].iloc[0]
            depth = well_info['depth_m']
            survived = well_info['survived']
            
            # Base water level depends on depth and survival
            if survived:
                base_level = max(2.0, depth * 0.05)  # Successful wells have decent water
            else:
                base_level = max(1.0, depth * 0.02)  # Failed wells have low water
            
            # Add seasonal variation
            for i, date in enumerate(months):
                seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * i / 12)  # Annual cycle
                noise = np.random.normal(0, 0.2)
                water_level = max(0.5, base_level * seasonal_factor + noise)
                
                water_levels_data.append({
                    'date': date,
                    'well_id': well_id,
                    'water_level_m': water_level
                })
        
        return pd.DataFrame(water_levels_data)
    
    def _generate_heat_points_for_wells(self, wells_df: pd.DataFrame) -> List[List[float]]:
        """Generate heatmap points based on well locations and success rates."""
        if wells_df.empty:
            return generate_fallback_data()["heat_points"]
        
        heat_points = []
        
        # Add heat points based on well locations
        for _, well in wells_df.iterrows():
            lat, lon = well['lat'], well['lon']
            survived = well['survived']
            
            # Weight based on success
            weight = 0.8 if survived else 0.3
            heat_points.append([lat, lon, weight])
            
            # Add some nearby points with lower weights for smooth heatmap
            for _ in range(3):
                noise_lat = lat + np.random.normal(0, 0.01)
                noise_lon = lon + np.random.normal(0, 0.01) 
                noise_weight = weight * np.random.uniform(0.3, 0.7)
                heat_points.append([noise_lat, noise_lon, noise_weight])
        
        return heat_points
    
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