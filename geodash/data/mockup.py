# geodash/data/mockup.py - Complete version with potential wells generation

"""
Mockup/fallback data generator for the geological dashboard.
This module provides mock data when real data is not available.
Updated to generate time series data for farms and potential drilling locations.
"""
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

try:
    from shapely.geometry import Point, Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("⚠️ Shapely not available. Potential wells generation will use simplified logic.")


def generate_mock_data() -> Dict[str, object]:
    """
    Generate mock/fallback datasets for the dashboard.
    Used when real data files are not available or cannot be loaded.

    Returns a dict with:
    - polygons: List[dict] - Mock field polygons
    - wells_df: pd.DataFrame - Mock well data  
    - farm_time_series: pd.DataFrame - Mock time series data for farms (not wells)
    - heat_points: List[List[float]] - Mock heatmap points
    - cost_df: pd.DataFrame - Mock cost estimation data
    - prob_df: pd.DataFrame - Mock probability data
    """
    rng = np.random.default_rng(42)

    # Define Dan Chang district boundaries (consistent for all data)
    dan_chang_lat_min, dan_chang_lat_max = 14.85, 15.05  # North-South range
    dan_chang_lng_min, dan_chang_lng_max = 99.50, 99.75  # East-West range

    # Mock field polygons - located in Dan Chang District area
    polygons = [
        {
            "name": "ไร่ด่านช้าง A (Mock)",
            "region": "ด่านช้าง",
            "coordinates": [
                [14.95, 99.58],
                [14.95, 99.65],
                [14.90, 99.65], 
                [14.90, 99.58],
            ],
        },
        {
            "name": "ไร่หนองไผ่ B (Mock)",
            "region": "หนองไผ่",
            "coordinates": [
                [14.98, 99.60],
                [14.98, 99.67],
                [14.93, 99.67],
                [14.93, 99.60],
            ],
        },
        {
            "name": "ไร่วังลึก C (Mock)",
            "region": "วังลึก", 
            "coordinates": [
                [14.92, 99.55],
                [14.92, 99.62],
                [14.87, 99.62],
                [14.87, 99.55],
            ],
        },
    ]

    # Mock well data - located in อำเภอด่านช้าง (Dan Chang District), Suphan Buri
    well_ids: List[str] = [f"WELL-{i:03d}" for i in range(1, 51)]
    
    # Generate wells within Dan Chang district
    lats = dan_chang_lat_min + rng.random(len(well_ids)) * (dan_chang_lat_max - dan_chang_lat_min)
    lngs = dan_chang_lng_min + rng.random(len(well_ids)) * (dan_chang_lng_max - dan_chang_lng_min)
    
    # Assign regions based on sub-districts in Dan Chang
    regions = rng.choice([
        "ด่านช้าง",      # Dan Chang (main district)
        "หนองไผ่",       # Nong Phai
        "ดอนกำยาน",      # Don Kamyan  
        "หนองหญ้าปล้อง",  # Nong Ya Plong
        "วังลึก",        # Wang Luek
        "หูช้าง"         # Hu Chang
    ], size=len(well_ids))
    
    depths_m = rng.integers(40, 220, size=len(well_ids))
    survival_prob = rng.uniform(0.5, 0.95, size=len(well_ids))
    success = rng.binomial(1, survival_prob).astype(bool)

    wells_df = pd.DataFrame(
        {
            "well_id": well_ids,
            "region": regions,
            "lat": lats,
            "lon": lngs,
            "depth_m": depths_m,
            "survived": success,
            "distance_to_farm": rng.uniform(100, 30000, size=len(well_ids))  # Add distance
        }
    )

    # Farm-based time series data
    months = pd.date_range(end=pd.Timestamp.today().normalize(), periods=24, freq="MS")
    
    unique_regions = regions
    farm_time_series_data = []
    
    for region in np.unique(unique_regions):
        base_survival_rate = rng.uniform(0.6, 0.9)
        
        for month in months:
            month_num = month.month
            seasonal_factor = 1.0
            
            if 5 <= month_num <= 10:
                seasonal_factor = rng.uniform(1.1, 1.3)
            else:
                seasonal_factor = rng.uniform(0.8, 1.0)
            
            noise = rng.normal(0, 0.05)
            survival_rate = np.clip(base_survival_rate * seasonal_factor + noise, 0.0, 1.0)
            wells_in_region = np.sum(regions == region)
            
            farm_time_series_data.append({
                "date": month,
                "region": region,
                "survival_rate": survival_rate,
                "total_wells": wells_in_region,
                "successful_wells": int(wells_in_region * survival_rate),
                "water_level_avg_m": rng.uniform(3.0, 8.0),
                "rainfall_mm": rng.uniform(0, 150) if 5 <= month_num <= 10 else rng.uniform(0, 50)
            })
    
    farm_time_series = pd.DataFrame(farm_time_series_data)

    # Mock heatmap points
    heat_points = []
    for _ in range(300):
        lat = dan_chang_lat_min + rng.random() * (dan_chang_lat_max - dan_chang_lat_min)
        lon = dan_chang_lng_min + rng.random() * (dan_chang_lng_max - dan_chang_lng_min)
        weight = float(rng.uniform(0.2, 1.0))
        heat_points.append([lat, lon, weight])

    for _, well in wells_df.iterrows():
        num_nearby_points = rng.integers(2, 5)
        for _ in range(num_nearby_points):
            lat_offset = rng.normal(0, 0.005)
            lon_offset = rng.normal(0, 0.005)
            
            nearby_lat = np.clip(well['lat'] + lat_offset, dan_chang_lat_min, dan_chang_lat_max)
            nearby_lon = np.clip(well['lon'] + lon_offset, dan_chang_lng_min, dan_chang_lng_max)
            
            base_weight = 0.8 if well['survived'] else 0.4
            weight = float(np.clip(rng.normal(base_weight, 0.2), 0.1, 1.0))
            
            heat_points.append([nearby_lat, nearby_lon, weight])

    # Mock cost and probability data
    depth_bins = np.arange(50, 251, 25)
    base_cost_per_m = 1200
    cost_df = pd.DataFrame(
        {
            "depth_m": depth_bins,
            "estimated_cost_thb": (depth_bins * base_cost_per_m)
            + rng.normal(0, 15000, size=len(depth_bins)),
        }
    )

    prob_df = pd.DataFrame(
        {
            "depth_m": depth_bins,
            "probability": np.clip(
                1.0 - np.abs((depth_bins - 150) / 150) + rng.normal(0, 0.05, len(depth_bins)),
                0.05,
                0.95,
            ),
        }
    )

    return {
        "polygons": polygons,
        "wells_df": wells_df,
        "farm_time_series": farm_time_series,
        "heat_points": heat_points,
        "cost_df": cost_df,
        "prob_df": prob_df,
    }


# def generate_potential_wells():
#     pass


def generate_potential_wells(
    field_polygons: List[Dict],
    existing_wells_df: pd.DataFrame,
    num_suggestions: int = 500
) -> pd.DataFrame:
    """
    Generate potential drilling locations around (not inside) field polygons.
    Creates ~500 potential wells distributed around field boundaries.
    
    Args:
        field_polygons: List of field polygon dictionaries
        existing_wells_df: DataFrame of existing wells
        num_suggestions: Number of potential locations to generate (default: 500)
        
    Returns:
        DataFrame with potential well locations
    """
    rng = np.random.default_rng(42)
    potential_wells = []
    
    if not field_polygons:
        return pd.DataFrame()
    
    # Calculate wells per field (distribute evenly)
    wells_per_field = max(1, num_suggestions // len(field_polygons))
    
    for field_idx, field in enumerate(field_polygons):
        coords = field.get('coordinates', [])
        if not coords or len(coords) < 3:
            continue
        
        # Calculate field bounds
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        centroid_lat = sum(lats) / len(lats)
        centroid_lon = sum(lons) / len(lons)
        
        # Calculate approximate field size
        field_height = max_lat - min_lat
        field_width = max_lon - min_lon
        
        # Generate wells around this field
        field_well_count = 0
        attempts = 0
        max_attempts = wells_per_field * 20  # Allow many attempts to find good positions
        
        while field_well_count < wells_per_field and attempts < max_attempts:
            attempts += 1
            
            # Generate position AROUND the field (not inside)
            # Use circular distribution around centroid, outside field boundaries
            angle = rng.uniform(0, 2 * np.pi)
            
            # Distance from field boundary: 100m to 3km
            # Convert to degrees (~0.001 to 0.027 degrees)
            min_distance_deg = 0.001  # ~100m minimum from boundary
            max_distance_deg = 0.027  # ~3km maximum from boundary
            
            # Add field size to ensure we're outside the field
            buffer_distance = max(field_height, field_width) / 2 + rng.uniform(min_distance_deg, max_distance_deg)
            
            offset_lat = buffer_distance * np.cos(angle)
            offset_lon = buffer_distance * np.sin(angle)
            
            pot_lat = centroid_lat + offset_lat
            pot_lon = centroid_lon + offset_lon
            
            # Check if point is actually OUTSIDE the field polygon
            inside_field = _point_in_polygon_simple(pot_lat, pot_lon, coords)
            if inside_field:
                continue  # Skip if inside field
            
            # Check minimum distance from existing potential wells (avoid clustering)
            if len(potential_wells) > 0:
                min_dist_to_potentials = min(
                    np.sqrt((w['lat'] - pot_lat)**2 + (w['lon'] - pot_lon)**2)
                    for w in potential_wells
                )
                if min_dist_to_potentials < 0.0005:  # ~50m minimum spacing
                    continue
            
            # Check distance from existing wells (should be > 100m)
            if not existing_wells_df.empty:
                min_dist = np.min(
                    np.sqrt(
                        (existing_wells_df['lat'] - pot_lat)**2 + 
                        (existing_wells_df['lon'] - pot_lon)**2
                    )
                )
                if min_dist < 0.001:  # Too close to existing well
                    continue
            
            # Generate well characteristics with realistic distributions
            depth_category = rng.choice(['shallow', 'medium', 'deep'], p=[0.25, 0.50, 0.25])
            
            if depth_category == 'shallow':
                depth = rng.integers(40, 60)
                base_probability = rng.uniform(0.55, 0.70)
                base_yield = rng.uniform(4, 7)
            elif depth_category == 'medium':
                depth = rng.integers(60, 100)
                base_probability = rng.uniform(0.70, 0.85)
                base_yield = rng.uniform(7, 12)
            else:  # deep
                depth = rng.integers(100, 150)
                base_probability = rng.uniform(0.75, 0.90)
                base_yield = rng.uniform(10, 16)
            
            # Calculate cost
            cost_per_meter = 1200
            drilling_cost = depth * cost_per_meter
            pump_cost = rng.uniform(30000, 60000)
            total_cost = drilling_cost + pump_cost
            
            # Calculate priority score (higher is better)
            # Factors: probability, yield, cost efficiency
            priority_score = (base_probability * base_yield) / (total_cost / 100000)
            
            potential_wells.append({
                'potential_id': f'POT-{len(potential_wells)+1:04d}',
                'lat': pot_lat,
                'lon': pot_lon,
                'field_name': field.get('name', 'Unknown'),
                'region': field.get('region', 'Unknown'),
                'recommended_depth_m': int(depth),
                'depth_category': depth_category,
                'success_probability': round(base_probability, 2),
                'expected_water_yield_m3h': round(base_yield, 1),
                'estimated_cost_thb': int(total_cost),
                'drilling_cost_thb': int(drilling_cost),
                'priority_score': round(priority_score, 2)
            })
            
            field_well_count += 1
    
    # Convert to DataFrame and sort by priority
    potential_df = pd.DataFrame(potential_wells)
    
    if not potential_df.empty:
        # Sort by priority score (highest first)
        potential_df = potential_df.sort_values('priority_score', ascending=False)
        
        # Ensure we have exactly num_suggestions (or close to it)
        potential_df = potential_df.head(num_suggestions)
        
        # Re-index potential IDs to be sequential
        potential_df['potential_id'] = [f'POT-{i+1:04d}' for i in range(len(potential_df))]
    
    return potential_df


def _point_in_polygon_simple(lat: float, lon: float, polygon_coords: List[List[float]]) -> bool:
    """
    Simple point-in-polygon test using ray casting algorithm.
    
    Args:
        lat: Point latitude
        lon: Point longitude
        polygon_coords: List of [lat, lon] coordinates
        
    Returns:
        True if point is inside polygon
    """
    x, y = lon, lat
    n = len(polygon_coords)
    

 


def calculate_water_demand_gap(
    field_polygons: List[Dict],
    existing_wells_df: pd.DataFrame,
    potential_wells_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate water demand gap for each field considering existing and potential wells.
    
    Args:
        field_polygons: List of field polygons
        existing_wells_df: Existing wells data
        potential_wells_df: Potential wells data
        
    Returns:
        DataFrame with demand gap analysis
    """
    demand_analysis = []
    
    if not field_polygons:
        return pd.DataFrame()
    
    for field in field_polygons:
        coords = field.get('coordinates', [])
        if not coords or len(coords) < 3:
            continue
        
        # Calculate centroid
        centroid_lat = sum(c[0] for c in coords) / len(coords)
        centroid_lon = sum(c[1] for c in coords) / len(coords)
        
        # Estimate field area (very rough, in hectares)
        # Simple bounding box method
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        lat_span = max(lats) - min(lats)
        lon_span = max(lons) - min(lons)
        area_deg_sq = lat_span * lon_span
        area_hectares = area_deg_sq * 111 * 111  # Very rough conversion
        area_rai = area_hectares * 6.25  # Convert to rai
        
        # Estimate water demand (m³/day)
        water_demand_m3_day = area_rai * 25  # 25 m³/rai/day for sugarcane
        
        # Find existing wells within 5km
        if not existing_wells_df.empty:
            distances = np.sqrt(
                (existing_wells_df['lat'] - centroid_lat)**2 + 
                (existing_wells_df['lon'] - centroid_lon)**2
            )
            nearby_wells = existing_wells_df[distances < 0.045]  # ~5km
            successful_wells = nearby_wells[nearby_wells['survived'] == True]
            
            # Estimate current water supply (8 hours operation per day)
            current_supply_m3_day = len(successful_wells) * 8 * 8  # 8 m³/h average
        else:
            nearby_wells = pd.DataFrame()
            successful_wells = pd.DataFrame()
            current_supply_m3_day = 0
        
        # Calculate gap
        water_gap_m3_day = max(0, water_demand_m3_day - current_supply_m3_day)
        gap_percentage = (water_gap_m3_day / water_demand_m3_day * 100) if water_demand_m3_day > 0 else 0
        
        # Find potential wells for this field
        if not potential_wells_df.empty:
            field_potential = potential_wells_df[
                potential_wells_df['field_name'] == field.get('name', 'Unknown')
            ]
            num_potential = len(field_potential)
            
            if num_potential > 0:
                potential_supply_m3_day = field_potential['expected_water_yield_m3h'].sum() * 8
                gap_after_drilling = max(0, water_gap_m3_day - potential_supply_m3_day)
            else:
                potential_supply_m3_day = 0
                gap_after_drilling = water_gap_m3_day
        else:
            num_potential = 0
            potential_supply_m3_day = 0
            gap_after_drilling = water_gap_m3_day
        
        # Calculate priority level
        if gap_percentage > 70 and num_potential > 0:
            priority_level = 'Critical'
        elif gap_percentage > 50 and num_potential > 0:
            priority_level = 'High'
        elif gap_percentage > 30:
            priority_level = 'Medium'
        else:
            priority_level = 'Low'
        
        demand_analysis.append({
            'field_name': field.get('name', 'Unknown'),
            'region': field.get('region', 'Unknown'),
            'area_rai': round(area_rai, 2),
            'water_demand_m3_day': round(water_demand_m3_day, 1),
            'current_supply_m3_day': round(current_supply_m3_day, 1),
            'water_gap_m3_day': round(water_gap_m3_day, 1),
            'gap_percentage': round(gap_percentage, 1),
            'existing_wells_nearby': len(nearby_wells),
            'successful_wells_nearby': len(successful_wells),
            'potential_wells_available': num_potential,
            'potential_additional_supply_m3_day': round(potential_supply_m3_day, 1),
            'gap_after_drilling': round(gap_after_drilling, 1),
            'priority_level': priority_level
        })
    
    df = pd.DataFrame(demand_analysis)
    if not df.empty:
        df = df.sort_values('gap_percentage', ascending=False)
    
    return df