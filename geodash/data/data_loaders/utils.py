"""
Shared utilities for data loaders.
Common functions used across multiple loaders.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


def classify_region_by_coords(coords: List[List[float]]) -> str:
    """
    Classify region based on coordinate centroid.
    Generic geographic classification for Thailand.
    
    Args:
        coords: List of [lat, lon] coordinate pairs
        
    Returns:
        Region name (North, South, East, Central, or Unknown)
    """
    if not coords:
        return "Unknown"
    
    try:
        # Calculate centroid
        lat_avg = sum(coord[0] for coord in coords) / len(coords)
        lon_avg = sum(coord[1] for coord in coords) / len(coords)
        
        # Simple geographic classification for Thailand
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


def extract_geojson_coordinates(geometry: Dict[str, Any]) -> List[List[float]]:
    """
    Extract coordinates from GeoJSON geometry.
    
    Args:
        geometry: GeoJSON geometry dictionary
        
    Returns:
        List of [lat, lon] coordinate pairs
    """
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


def load_geojson_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load polygons from GeoJSON file.
    
    Args:
        file_path: Path to GeoJSON file
        
    Returns:
        List of polygon dictionaries
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        polygons = []
        features = geojson_data.get('features', [])
        
        for i, feature in enumerate(features):
            geometry = feature.get('geometry', {})
            properties = feature.get('properties', {})
            
            if geometry.get('type') in ['Polygon', 'MultiPolygon']:
                coords = extract_geojson_coordinates(geometry)
                if coords:
                    name = properties.get('name', properties.get('field_name', 
                           properties.get('id', f"Field_{i+1}")))
                    region = properties.get('region', properties.get('zone', 
                             classify_region_by_coords(coords)))
                    
                    polygons.append({
                        "name": str(name),
                        "region": str(region),
                        "coordinates": coords
                    })
        
        return polygons
        
    except Exception as e:
        print(f"❌ Error loading GeoJSON {file_path}: {e}")
        return []


def clean_dataframe_columns(df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Clean DataFrame by renaming columns and handling common issues.
    
    Args:
        df: Input DataFrame
        column_mapping: Dictionary mapping old column names to new names
        
    Returns:
        Cleaned DataFrame
    """
    # Create a copy to avoid modifying original
    cleaned_df = df.copy()
    
    # Rename columns
    cleaned_df = cleaned_df.rename(columns=column_mapping)
    
    # Strip whitespace from string columns
    for col in cleaned_df.select_dtypes(include=['object']).columns:
        cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
    
    return cleaned_df


def convert_coordinates_to_numeric(df: pd.DataFrame, lat_col: str = 'lat', lon_col: str = 'lon') -> pd.DataFrame:
    """
    Convert coordinate columns to numeric, handling errors gracefully.
    
    Args:
        df: Input DataFrame
        lat_col: Name of latitude column
        lon_col: Name of longitude column
        
    Returns:
        DataFrame with numeric coordinates
    """
    df_clean = df.copy()
    
    # Convert to numeric
    df_clean[lat_col] = pd.to_numeric(df_clean[lat_col], errors='coerce')
    df_clean[lon_col] = pd.to_numeric(df_clean[lon_col], errors='coerce')
    
    # Remove rows with invalid coordinates
    df_clean = df_clean.dropna(subset=[lat_col, lon_col])
    df_clean = df_clean[
        (df_clean[lat_col].between(-90, 90)) & 
        (df_clean[lon_col].between(-180, 180))
    ]
    
    return df_clean


def validate_polygon_coordinates(coords: List[List[float]]) -> bool:
    """
    Validate polygon coordinates.
    
    Args:
        coords: List of [lat, lon] coordinate pairs
        
    Returns:
        True if coordinates are valid, False otherwise
    """
    if not coords or len(coords) < 3:
        return False
    
    for coord in coords:
        if len(coord) != 2:
            return False
        lat, lon = coord
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
    
    return True


def generate_well_id_if_missing(df: pd.DataFrame, id_column: str = 'well_id', prefix: str = 'WELL') -> pd.DataFrame:
    """
    Generate well IDs for rows that are missing them.
    
    Args:
        df: Input DataFrame
        id_column: Name of the ID column
        prefix: Prefix for generated IDs
        
    Returns:
        DataFrame with generated IDs for missing values
    """
    df_with_ids = df.copy()
    
    if id_column not in df_with_ids.columns:
        # Create the column if it doesn't exist
        df_with_ids[id_column] = [f"{prefix}-{i:03d}" for i in range(1, len(df_with_ids) + 1)]
    else:
        # Fill missing values
        missing_mask = df_with_ids[id_column].isna() | (df_with_ids[id_column] == '')
        missing_count = missing_mask.sum()
        
        if missing_count > 0:
            start_idx = len(df_with_ids) - missing_count + 1
            generated_ids = [f"{prefix}-{i:03d}" for i in range(start_idx, start_idx + missing_count)]
            df_with_ids.loc[missing_mask, id_column] = generated_ids
    
    return df_with_ids


def calculate_data_bounds(df: pd.DataFrame, lat_col: str = 'lat', lon_col: str = 'lon') -> Tuple[float, float, float, float]:
    """
    Calculate geographic bounds of data.
    
    Args:
        df: DataFrame with coordinate data
        lat_col: Name of latitude column
        lon_col: Name of longitude column
        
    Returns:
        Tuple of (min_lat, max_lat, min_lon, max_lon)
    """
    if df.empty or lat_col not in df.columns or lon_col not in df.columns:
        # Default to Thailand bounds
        return 5.0, 21.0, 97.0, 106.0
    
    return (
        float(df[lat_col].min()),
        float(df[lat_col].max()),
        float(df[lon_col].min()),
        float(df[lon_col].max())
    )


def generate_realistic_depths(size: int, min_depth: int = 40, max_depth: int = 220) -> np.ndarray:
    """
    Generate realistic well depths with distribution bias toward optimal ranges.
    
    Args:
        size: Number of depths to generate
        min_depth: Minimum depth in meters
        max_depth: Maximum depth in meters
        
    Returns:
        Array of depths
    """
    # Use a beta distribution to favor depths around 80-150m range
    # which is typical for successful groundwater wells
    rng = np.random.default_rng(42)
    
    # Generate beta-distributed values (0-1)
    beta_values = rng.beta(2, 2, size)
    
    # Scale to desired range
    depths = min_depth + beta_values * (max_depth - min_depth)
    
    return depths.astype(int)


def calculate_success_probability(depth: float, optimal_range: Tuple[float, float] = (80, 150)) -> float:
    """
    Calculate success probability based on well depth.
    
    Args:
        depth: Well depth in meters
        optimal_range: Tuple of (min_optimal, max_optimal) depths
        
    Returns:
        Success probability (0.0 to 1.0)
    """
    min_optimal, max_optimal = optimal_range
    
    if min_optimal <= depth <= max_optimal:
        # High probability in optimal range
        return 0.85 + np.random.normal(0, 0.05)
    elif depth < min_optimal:
        # Lower probability for shallow wells
        factor = depth / min_optimal
        return 0.6 * factor + np.random.normal(0, 0.1)
    else:
        # Lower probability for very deep wells
        factor = max(0.1, 1.0 - (depth - max_optimal) / 100)
        return 0.7 * factor + np.random.normal(0, 0.1)


def log_data_summary(data_type: str, count: int, sample_data: Any = None, source: str = "real"):
    """
    Log a summary of loaded data for debugging.
    
    Args:
        data_type: Type of data being logged
        count: Number of items loaded
        sample_data: Sample of the data for inspection
        source: Source of data (real/mock)
    """
    emoji = "✅" if source == "real" else "🔄"
    print(f"{emoji} Loaded {count} {data_type} items ({source} data)")
    
    if sample_data is not None and count > 0:
        if isinstance(sample_data, pd.DataFrame) and not sample_data.empty:
            print(f"📊 Sample columns: {list(sample_data.columns[:5])}")
            if 'lat' in sample_data.columns and 'lon' in sample_data.columns:
                lat_range = f"{sample_data['lat'].min():.3f}-{sample_data['lat'].max():.3f}"
                lon_range = f"{sample_data['lon'].min():.3f}-{sample_data['lon'].max():.3f}"
                print(f"📍 Coordinate range: Lat {lat_range}, Lon {lon_range}")
        elif isinstance(sample_data, list) and len(sample_data) > 0:
            print(f"📋 Sample keys: {list(sample_data[0].keys()) if sample_data[0] else 'N/A'}")


# Export utility functions
__all__ = [
    "classify_region_by_coords",
    "extract_geojson_coordinates", 
    "load_geojson_file",
    "clean_dataframe_columns",
    "convert_coordinates_to_numeric",
    "validate_polygon_coordinates",
    "generate_well_id_if_missing",
    "calculate_data_bounds",
    "generate_realistic_depths",
    "calculate_success_probability",
    "log_data_summary"
]