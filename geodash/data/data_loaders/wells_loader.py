"""
Wells data loader for government groundwater CSV files.
Handles loading, cleaning, and processing of well/groundwater data.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

from .base import BaseDataLoader, DataValidationMixin
from .utils import (
    clean_dataframe_columns,
    convert_coordinates_to_numeric,
    generate_well_id_if_missing,
    generate_realistic_depths,
    calculate_success_probability,
    log_data_summary
)
from ..mockup import generate_mock_data


class WellsLoader(BaseDataLoader, DataValidationMixin):
    """Loader for wells/groundwater data from CSV files."""
    
    def __init__(self, data_dir: str = "geodash/data"):
        super().__init__(data_dir)
        self.csv_file = self.groundwater_dir / "gov_groundwater_scope.csv"
    
    def load(self) -> pd.DataFrame:
        """
        Load wells data from CSV file or fallback to mock data.
        
        Returns:
            DataFrame with columns: well_id, region, lat, lon, depth_m, survived
        """
        # Try to load real data first
        if self._file_exists(self.csv_file):
            try:
                self._log_loading_attempt("wells data", self.csv_file)
                df = pd.read_csv(self.csv_file, encoding='utf-8')
                wells_df = self._process_groundwater_csv(df)
                
                if self._validate_wells_dataframe(wells_df):
                    log_data_summary("wells", len(wells_df), wells_df, "real")
                    return wells_df
                else:
                    self._log_fallback("wells data", "Invalid data structure after processing")
                    
            except Exception as e:
                self._log_fallback("wells data", f"Error loading CSV: {e}")
        else:
            self._log_fallback("wells data", f"File not found: {self.csv_file}")
        
        # Fallback to mock data
        return self._load_fallback_data()
    
    def _load_fallback_data(self) -> pd.DataFrame:
        """Load mock wells data."""
        mock_data = generate_mock_data()
        wells_df = mock_data["wells_df"]
        log_data_summary("wells", len(wells_df), wells_df, "mock")
        return wells_df
    
    def _process_groundwater_csv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process and clean the government groundwater CSV data.
        
        Args:
            df: Raw DataFrame from CSV
            
        Returns:
            Processed DataFrame with standardized columns
        """
        try:
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
            
            # Clean and rename columns
            processed_df = clean_dataframe_columns(df, column_mapping)
            
            # Ensure required columns exist
            required_cols = ['well_id', 'lat', 'lon']
            missing_cols = [col for col in required_cols if col not in processed_df.columns]
            if missing_cols:
                self.logger.error(f"❌ Missing required columns: {missing_cols}")
                return pd.DataFrame()
            
            # Convert coordinates to numeric
            processed_df = convert_coordinates_to_numeric(processed_df)
            
            # Generate well IDs if missing
            processed_df = generate_well_id_if_missing(processed_df)
            
            # Process depth data
            processed_df = self._process_depth_data(processed_df)
            
            # Create region from amphoe (district)
            processed_df = self._process_region_data(processed_df)
            
            # Generate survival status
            processed_df = self._process_survival_data(processed_df)
            
            # Select and validate final columns
            final_cols = ['well_id', 'region', 'lat', 'lon', 'depth_m', 'survived']
            processed_df = processed_df[final_cols]
            
            # Ensure data types
            processed_df['well_id'] = processed_df['well_id'].astype(str)
            processed_df['depth_m'] = processed_df['depth_m'].astype(int)
            processed_df['survived'] = processed_df['survived'].astype(bool)
            
            self._log_processing_summary(processed_df)
            return processed_df
            
        except Exception as e:
            self.logger.error(f"❌ Error processing groundwater CSV: {e}")
            return pd.DataFrame()
    
    def _process_depth_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process well depth information."""
        # Use depth_drilled as primary depth, fallback to depth_developed
        if 'depth_drilled' in df.columns:
            df['depth_m'] = pd.to_numeric(df['depth_drilled'], errors='coerce')
        elif 'depth_developed' in df.columns:
            df['depth_m'] = pd.to_numeric(df['depth_developed'], errors='coerce')
        else:
            # Generate realistic depths if no depth data available
            df['depth_m'] = generate_realistic_depths(len(df))
            self.logger.warning("⚠️  No depth data found, using generated depths")
        
        # Fill missing depth values with realistic estimates
        missing_depths = df['depth_m'].isna()
        if missing_depths.any():
            df.loc[missing_depths, 'depth_m'] = generate_realistic_depths(missing_depths.sum())
        
        return df
    
    def _process_region_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process region/district information."""
        if 'amphoe' in df.columns:
            df['region'] = df['amphoe'].fillna('Unknown')
        elif 'tambon' in df.columns:
            df['region'] = df['tambon'].fillna('Unknown')
        else:
            df['region'] = 'Unknown'
        
        # Clean region names
        df['region'] = df['region'].apply(self._clean_string_field)
        
        return df
    
    def _process_survival_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process well survival/success status."""
        if 'water_volume' in df.columns:
            # Wells with water volume > 1 m³/h are considered successful
            water_vol = pd.to_numeric(df['water_volume'], errors='coerce')
            df['survived'] = (water_vol > 1.0).fillna(False)
        else:
            # Calculate success probability based on depth
            df['survived'] = df['depth_m'].apply(
                lambda depth: np.random.random() < calculate_success_probability(depth)
            )
        
        return df
    
    def _log_processing_summary(self, df: pd.DataFrame) -> None:
        """Log summary of processed data."""
        if df.empty:
            return
        
        self.logger.info(f"📊 Processed {len(df)} wells successfully")
        
        # Coordinate range
        lat_range = f"{df['lat'].min():.3f}-{df['lat'].max():.3f}"
        lon_range = f"{df['lon'].min():.3f}-{df['lon'].max():.3f}"
        self.logger.info(f"📍 Coordinate range: Lat {lat_range}, Lon {lon_range}")
        
        # Depth statistics
        depth_range = f"{df['depth_m'].min():.1f}-{df['depth_m'].max():.1f}m"
        self.logger.info(f"🏔️  Depth range: {depth_range}")
        
        # Success rate
        success_rate = f"{df['survived'].mean():.1%}"
        self.logger.info(f"✅ Success rate: {success_rate}")
        
        # Regional distribution
        region_counts = df['region'].value_counts().head(3)
        top_regions = ", ".join([f"{region} ({count})" for region, count in region_counts.items()])
        self.logger.info(f"🌍 Top regions: {top_regions}")


# Export the loader class
__all__ = ["WellsLoader"]