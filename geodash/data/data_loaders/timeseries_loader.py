"""
Time series data loader for water level data.
Generates realistic time series water level data based on well characteristics.
"""
import numpy as np
import pandas as pd
from typing import List

from .base import BaseDataLoader
from .utils import log_data_summary
from ..mockup import generate_mock_data


class TimeSeriesLoader(BaseDataLoader):
    """Loader for time series water level data."""
    
    def __init__(self, data_dir: str = "geodash/data"):
        super().__init__(data_dir)
        self.months_of_data = 12
    
    def load(self, wells_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Generate time series water level data for wells.
        
        Args:
            wells_df: DataFrame of wells data to generate time series for
            
        Returns:
            DataFrame with columns: date, well_id, water_level_m
        """
        if wells_df is None or wells_df.empty:
            self._log_fallback("time series data", "No wells data provided")
            return self._load_fallback_data()
        
        try:
            self._log_loading_attempt("time series data")
            water_levels = self._generate_water_levels_for_wells(wells_df)
            
            log_data_summary("time series records", len(water_levels), water_levels, "generated")
            return water_levels
            
        except Exception as e:
            self._log_fallback("time series data", f"Error generating data: {e}")
            return self._load_fallback_data()
    
    def _load_fallback_data(self) -> pd.DataFrame:
        """Load mock time series data."""
        mock_data = generate_mock_data()
        water_levels = mock_data["water_levels"]
        log_data_summary("time series records", len(water_levels), water_levels, "mock")
        return water_levels
    
    def _generate_water_levels_for_wells(self, wells_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate realistic time series water level data for wells.
        
        Args:
            wells_df: DataFrame containing well information
            
        Returns:
            DataFrame with time series water level data
        """
        # Generate date range
        months = pd.date_range(
            end=pd.Timestamp.today().normalize(),
            periods=self.months_of_data,
            freq="MS"
        )
        
        well_ids = wells_df['well_id'].tolist()
        water_levels_data = []
        
        for well_id in well_ids:
            well_info = wells_df[wells_df['well_id'] == well_id].iloc[0]
            depth = well_info['depth_m']
            survived = well_info['survived']
            
            # Generate time series for this well
            well_time_series = self._generate_well_time_series(
                well_id, depth, survived, months
            )
            water_levels_data.extend(well_time_series)
        
        return pd.DataFrame(water_levels_data)
    
    def _generate_well_time_series(
        self, 
        well_id: str, 
        depth: float, 
        survived: bool, 
        dates: pd.DatetimeIndex
    ) -> List[dict]:
        """
        Generate time series data for a single well.
        
        Args:
            well_id: Well identifier
            depth: Well depth in meters
            survived: Whether the well is successful
            dates: Date range for time series
            
        Returns:
            List of time series records
        """
        # Base water level depends on depth and survival status
        base_level = self._calculate_base_water_level(depth, survived)
        
        time_series = []
        
        for i, date in enumerate(dates):
            # Add seasonal variation (annual cycle)
            seasonal_factor = self._calculate_seasonal_factor(i, len(dates))
            
            # Add random noise
            noise = np.random.normal(0, 0.2)
            
            # Calculate final water level
            water_level = max(0.5, base_level * seasonal_factor + noise)
            
            time_series.append({
                'date': date,
                'well_id': well_id,
                'water_level_m': round(water_level, 2)
            })
        
        return time_series
    
    def _calculate_base_water_level(self, depth: float, survived: bool) -> float:
        """
        Calculate base water level based on well characteristics.
        
        Args:
            depth: Well depth in meters
            survived: Whether the well is successful
            
        Returns:
            Base water level in meters
        """
        if survived:
            # Successful wells have decent water levels
            # Deeper wells might have more stable water sources
            base_level = max(2.0, depth * 0.05)
            
            # Add some variation based on depth optimality
            if 80 <= depth <= 150:  # Optimal depth range
                base_level *= 1.2
            elif depth > 200:  # Very deep wells might have lower levels
                base_level *= 0.8
                
        else:
            # Failed wells have consistently low water levels
            base_level = max(1.0, depth * 0.02)
        
        return base_level
    
    def _calculate_seasonal_factor(self, month_index: int, total_months: int) -> float:
        """
        Calculate seasonal variation factor.
        
        Args:
            month_index: Current month index (0-based)
            total_months: Total number of months in the series
            
        Returns:
            Seasonal multiplication factor
        """
        # Create annual cycle with peak in rainy season (around month 6-8)
        seasonal_phase = 2 * np.pi * month_index / 12
        
        # Rainy season has higher water levels
        # Dry season (months 2-4) has lower levels
        seasonal_factor = 1 + 0.3 * np.sin(seasonal_phase + np.pi/3)
        
        return max(0.5, seasonal_factor)  # Ensure it doesn't go too low
    
    def get_date_range(self) -> pd.DatetimeIndex:
        """
        Get the date range used for time series generation.
        
        Returns:
            DatetimeIndex representing the time series range
        """
        return pd.date_range(
            end=pd.Timestamp.today().normalize(),
            periods=self.months_of_data,
            freq="MS"
        )
    
    def set_months_of_data(self, months: int) -> None:
        """
        Set the number of months of historical data to generate.
        
        Args:
            months: Number of months (default: 12)
        """
        if months > 0:
            self.months_of_data = months
        else:
            self.logger.warning("Months must be positive. Using default value.")


# Export the loader class
__all__ = ["TimeSeriesLoader"]