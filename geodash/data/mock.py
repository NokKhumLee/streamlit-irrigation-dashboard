from typing import Dict, List

import numpy as np
import pandas as pd


def generate_mock_data() -> Dict[str, object]:
    """
    Produce synthetic datasets for the dashboard.

    Returns a dict with:
    - polygons: List[dict]
        Each polygon is a more realistic irregular boundary for farmland.
        Keys:
          - name: str (human-readable label)
          - region: str (categorical region name)
          - coordinates: List[List[float]] of [lat, lon] vertices (no closing vertex)

    - wells_df: pd.DataFrame
        Per-well attributes with columns:
          - well_id: str (e.g., "WELL-001")
          - region: str (one of {North, East, South, West})
          - lat: float (latitude in WGS84)
          - lon: float (longitude in WGS84)
          - depth_m: int (drilling depth in meters)
          - survived: bool (survival outcome)

    - water_levels: pd.DataFrame
        Time series of water level per well with columns:
          - date: pandas.Timestamp (month start)
          - well_id: str
          - water_level_m: float (meters)

    - heat_points: List[List[float]]
        Heatmap points as [lat, lon, weight] triples where weight∈[0,1].

    - cost_df: pd.DataFrame
        Estimated drilling cost by depth bucket with columns:
          - depth_m: int (bucket midpoint)
          - estimated_cost_thb: float (Thai Baht)

    - prob_df: pd.DataFrame
        Groundwater discovery probability by depth with columns:
          - depth_m: int
          - probability: float in [0,1]
    """
    rng = np.random.default_rng(42)

    def create_irregular_polygon(center_lat: float, center_lon: float, 
                                base_radius: float, num_points: int = None) -> List[List[float]]:
        """Create an irregular polygon around a center point."""
        if num_points is None:
            num_points = rng.integers(6, 12)  # Random number of points between 6-11
        
        # Generate angles evenly spaced around the circle
        angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
        # Add some randomness to the angles
        angle_noise = rng.normal(0, 0.3, num_points)
        angles = angles + angle_noise
        
        coordinates = []
        for angle in angles:
            # Vary the radius for each point to create irregularity
            radius_variation = rng.uniform(0.7, 1.3)
            actual_radius = base_radius * radius_variation
            
            # Convert polar to cartesian and add to center
            lat = center_lat + actual_radius * np.cos(angle)
            lon = center_lon + actual_radius * np.sin(angle)
            
            coordinates.append([lat, lon])
        
        return coordinates

    # Thai field names for realistic naming
    thai_places = [
        "ไร่โพธิ์", "ไร่ไผ่", "ไร่กล้วย", "ไร่มะขาม", "ไร่สวน",
        "ไร่หนองหิน", "ไร่ดอนยาง", "ไร่คลองใหม่", "ไร่หัวสะพาน", "ไร่ทุ่งใหญ่",
        "ไร่โนนสูง", "ไร่ลาดใหญ่", "ไร่หนองแสง", "ไร่ดงพญาไฟ", "ไร่บึงกาฬ",
        "ไร่สามแยก", "ไร่ทุ่งทอง", "ไร่คลองเตย", "ไร่บางบัว", "ไร่นาดี"
    ]
    
    # Create non-overlapping polygon centers with better spacing
    grid_positions = [
        (15.75, 99.80), (15.75, 100.10), (15.75, 100.40),
        (15.90, 99.75), (15.90, 100.05), (15.90, 100.35),
        (16.05, 99.80), (16.05, 100.10), (16.05, 100.40),
        (16.20, 99.75), (16.20, 100.05), (16.20, 100.35),
        (15.82, 99.95), (15.97, 100.25), (16.12, 99.90)
    ]
    
    # Create polygons with sufficient spacing to avoid overlap
    polygons = []
    regions = ["North", "East", "South", "West"]
    
    # Select random subset of positions and places
    num_polygons = 12
    selected_positions = rng.choice(len(grid_positions), size=num_polygons, replace=False)
    selected_places = rng.choice(thai_places, size=num_polygons, replace=False)
    
    for i, pos_idx in enumerate(selected_positions):
        lat, lon = grid_positions[pos_idx]
        place_name = selected_places[i]
        region = regions[i % len(regions)]
        
        # Add smaller random offset to center to reduce overlap risk
        lat_offset = rng.uniform(-0.015, 0.015)
        lon_offset = rng.uniform(-0.015, 0.015)
        
        polygons.append({
            "name": place_name,
            "region": region,
            "coordinates": create_irregular_polygon(
                lat + lat_offset, 
                lon + lon_offset, 
                0.035,  # Even smaller radius to prevent overlap
                rng.integers(6, 9)
            ),
        })

    # Generate more wells for better coverage
    well_ids: List[str] = [f"WELL-{i:03d}" for i in range(1, 121)]  # Increased from 50 to 120 wells
    regions = rng.choice(["North", "East", "South", "West"], size=len(well_ids))
    lats = 15.7 + rng.random(len(well_ids)) * 0.6
    lngs = 99.8 + rng.random(len(well_ids)) * 0.7
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

    heat_points = []
    for _ in range(300):
        lat = 15.7 + rng.random() * 0.6
        lon = 99.8 + rng.random() * 0.7
        weight = float(rng.uniform(0.2, 1.0))
        heat_points.append([lat, lon, weight])

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