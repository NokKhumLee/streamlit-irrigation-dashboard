from typing import Dict, List

import numpy as np
import pandas as pd


def generate_mock_data() -> Dict[str, object]:
    """
    Produce synthetic datasets for the dashboard.

    Returns a dict with:
    - polygons: List[dict]
        Each polygon is a simple rectangular boundary for farmland.
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

    polygons = [
        {
            "name": "ไร่ A",
            "region": "North",
            "coordinates": [
                [16.05, 99.85],
                [16.05, 100.05],
                [15.85, 100.05],
                [15.85, 99.85],
            ],
        },
        {
            "name": "ไร่ B",
            "region": "East",
            "coordinates": [
                [15.95, 100.15],
                [15.95, 100.35],
                [15.75, 100.35],
                [15.75, 100.15],
            ],
        },
    ]

    well_ids: List[str] = [f"WELL-{i:03d}" for i in range(1, 51)]
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



