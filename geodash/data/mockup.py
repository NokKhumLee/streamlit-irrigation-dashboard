# geodash/data/mockup.py - Updated to generate farm-based time series

"""
Mockup/fallback data generator for the geological dashboard.
This module provides mock data when real data is not available.
Updated to generate time series data for farms instead of individual wells.
"""
from typing import Dict, List

import numpy as np
import pandas as pd


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
        }
    )

    # NEW: Farm-based time series data instead of well-based
    # Generate time series for each region (representing farm areas)
    months = pd.date_range(end=pd.Timestamp.today().normalize(), periods=24, freq="MS")  # 2 years of data
    
    # Get unique regions to create farm time series
    unique_regions = regions
    farm_time_series_data = []
    
    for region in np.unique(unique_regions):
        # Generate realistic seasonal patterns for each farm/region
        base_survival_rate = rng.uniform(0.6, 0.9)  # Base survival rate for this region
        
        for month in months:
            # Add seasonal variation (higher in rainy season, lower in dry season)
            month_num = month.month
            seasonal_factor = 1.0
            
            # Thailand rainy season (May-October) - higher survival rates
            if 5 <= month_num <= 10:
                seasonal_factor = rng.uniform(1.1, 1.3)
            # Dry season (November-April) - lower survival rates  
            else:
                seasonal_factor = rng.uniform(0.8, 1.0)
            
            # Add some random noise
            noise = rng.normal(0, 0.05)
            
            survival_rate = np.clip(base_survival_rate * seasonal_factor + noise, 0.0, 1.0)
            
            # Calculate number of wells in this region for this time period
            wells_in_region = np.sum(regions == region)
            
            farm_time_series_data.append({
                "date": month,
                "region": region,
                "survival_rate": survival_rate,
                "total_wells": wells_in_region,
                "successful_wells": int(wells_in_region * survival_rate),
                "water_level_avg_m": rng.uniform(3.0, 8.0),  # Average water level for the region
                "rainfall_mm": rng.uniform(0, 150) if 5 <= month_num <= 10 else rng.uniform(0, 50)
            })
    
    farm_time_series = pd.DataFrame(farm_time_series_data)

    # Mock heatmap points - ALIGNED with Dan Chang district area (same boundaries as wells)
    heat_points = []
    for _ in range(300):
        lat = dan_chang_lat_min + rng.random() * (dan_chang_lat_max - dan_chang_lat_min)
        lon = dan_chang_lng_min + rng.random() * (dan_chang_lng_max - dan_chang_lng_min)
        weight = float(rng.uniform(0.2, 1.0))
        heat_points.append([lat, lon, weight])

    # Add heatmap points clustered around actual wells for more realistic visualization
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
        "farm_time_series": farm_time_series,  # NEW: Farm-based time series instead of water_levels
        "heat_points": heat_points,
        "cost_df": cost_df,
        "prob_df": prob_df,
    }