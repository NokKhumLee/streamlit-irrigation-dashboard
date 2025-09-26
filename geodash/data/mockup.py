"""
Mockup/fallback data generator for the geological dashboard.
This module provides mock data when real data is not available.
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
    - water_levels: pd.DataFrame - Mock time series data
    - heat_points: List[List[float]] - Mock heatmap points
    - cost_df: pd.DataFrame - Mock cost estimation data
    - prob_df: pd.DataFrame - Mock probability data
    """
    rng = np.random.default_rng(42)

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
    # Dan Chang District coordinates: approximately 14.9°N, 99.6°E
    well_ids: List[str] = [f"WELL-{i:03d}" for i in range(1, 51)]
    
    # Dan Chang district boundaries (approximate)
    dan_chang_lat_min, dan_chang_lat_max = 14.85, 15.05  # North-South range
    dan_chang_lng_min, dan_chang_lng_max = 99.50, 99.75  # East-West range
    
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

    # Mock time series data
    months = pd.date_range(end=pd.Timestamp.today().normalize(), periods=12, freq="MS")
    water_levels = (
        pd.DataFrame(
            rng.normal(loc=5, scale=1.2, size=(len(months), len(well_ids))),
            index=months,
            columns=well_ids,
        )
        .clip(lower=2.0)
    )
    water_levels = water_levels.stack().reset_index()
    water_levels.columns = ["date", "well_id", "water_level_m"]

    # Mock heatmap points - within Dan Chang district area
    heat_points = []
    for _ in range(300):
        lat = dan_chang_lat_min + rng.random() * (dan_chang_lat_max - dan_chang_lat_min)
        lon = dan_chang_lng_min + rng.random() * (dan_chang_lng_max - dan_chang_lng_min)
        weight = float(rng.uniform(0.2, 1.0))
        heat_points.append([lat, lon, weight])

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
        "water_levels": water_levels,
        "heat_points": heat_points,
        "cost_df": cost_df,
        "prob_df": prob_df,
    }