"""
Water stations data loader for survival rate analysis.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging

from .base import BaseDataLoader


class WaterStationsLoader(BaseDataLoader):
    """Loader for water stations survival data from CSV files."""
    
    def __init__(self, csv_path: str = "geodash/data/survival_data/badan_survival.csv"):
        super().__init__()
        self.csv_path = csv_path
        self.logger = logging.getLogger(__name__)
        
    def load(self, **kwargs) -> Dict[str, Any]:
        """Load water stations data (implementation of abstract method)."""
        return self.load_data(**kwargs)
    
    def _load_fallback_data(self) -> Dict[str, Any]:
        """Load fallback data when CSV is not available."""
        self.logger.warning("Using fallback data for water stations")
        return {
            "stations_df": pd.DataFrame(),
            "survival_years": [],
            "stations_summary": {}
        }
    
    def load_data(self, **kwargs) -> Dict[str, Any]:
        """
        Load water stations data from CSV.
        
        Returns:
            Dictionary containing:
            - stations_df: DataFrame with station information
            - survival_years: List of years with survival data
        """
        try:
            # Read the CSV file
            df = pd.read_csv(self.csv_path)
            self.logger.info(f"📊 Loaded {len(df)} water station records")
            
            # Clean column names (remove any extra spaces)
            df.columns = df.columns.str.strip()
            
            # Rename columns to English for easier handling
            column_mapping = {
                'หมายเลขสถานี': 'station_id',
                'หมายเลขบ่อ': 'well_number', 
                'Latitude': 'latitude',
                'Longitude': 'longitude',
                'ที่ตั้ง': 'location',
                'หมู่บ้าน': 'village',
                'ตำบล': 'subdistrict',
                'อำเภอ': 'district',
                'จังหวัด': 'province',
                'แอ่งน้ำบาดาล': 'groundwater_basin',
                'ระดับชั้นน้ำบาดาล': 'groundwater_level',
                'ชั้นหินให้น้ำ': 'aquifer_formation',
                'รหัสชั้นหิน': 'formation_code',
                'วันที่เริ่มเจาะ': 'drilling_start_date',
                'วันที่เจาะเสร็จ': 'drilling_end_date',
                'ความลึกเจาะ': 'drilling_depth'
            }
            
            # Rename columns that exist
            existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_columns)
            
            # Get survival years (columns that are years)
            year_columns = []
            for col in df.columns:
                try:
                    if str(col).isdigit() and 2000 <= int(col) <= 2030:
                        year_columns.append(int(col))
                except (ValueError, TypeError):
                    continue
            
            year_columns.sort()
            
            # Convert numeric columns
            numeric_columns = ['latitude', 'longitude', 'drilling_depth']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Convert survival data columns to numeric
            for year in year_columns:
                if str(year) in df.columns:
                    df[str(year)] = pd.to_numeric(df[str(year)], errors='coerce')
            
            # Remove rows with missing coordinates
            initial_count = len(df)
            df = df.dropna(subset=['latitude', 'longitude'])
            if len(df) < initial_count:
                self.logger.warning(f"⚠️ Dropped {initial_count - len(df)} records with missing coordinates")
            
            # Create station summary info
            stations_summary = self._create_stations_summary(df, year_columns)
            
            self.logger.info(f"✅ Successfully processed {len(df)} water station records")
            self.logger.info(f"📅 Survival data available for years: {year_columns}")
            
            return {
                "stations_df": df,
                "survival_years": year_columns,
                "stations_summary": stations_summary
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error loading water stations data: {str(e)}")
            return {
                "stations_df": pd.DataFrame(),
                "survival_years": [],
                "stations_summary": {}
            }
    
    def _create_stations_summary(self, df: pd.DataFrame, year_columns: List[int]) -> Dict[str, Any]:
        """Create summary statistics for water stations."""
        summary = {}
        
        if not df.empty:
            summary['total_stations'] = len(df['station_id'].unique()) if 'station_id' in df.columns else 0
            summary['total_wells'] = len(df)
            summary['provinces'] = df['province'].unique().tolist() if 'province' in df.columns else []
            summary['year_range'] = {
                'start': min(year_columns) if year_columns else None,
                'end': max(year_columns) if year_columns else None
            }
            
            # Calculate average survival rates by year
            if year_columns:
                survival_by_year = {}
                for year in year_columns:
                    year_col = str(year)
                    if year_col in df.columns:
                        avg_survival = df[year_col].mean()
                        survival_by_year[year] = avg_survival if not pd.isna(avg_survival) else 0.0
                summary['avg_survival_by_year'] = survival_by_year
        
        return summary
    
    def get_station_data(self, station_id: str, well_number: Optional[str] = None) -> pd.DataFrame:
        """
        Get data for a specific station and optionally a specific well.
        
        Args:
            station_id: Station identifier
            well_number: Well number (optional)
            
        Returns:
            Filtered DataFrame
        """
        data = self.load_data()
        df = data["stations_df"]
        
        if df.empty:
            return pd.DataFrame()
        
        # Filter by station
        if 'station_id' in df.columns:
            station_data = df[df['station_id'] == station_id]
        else:
            return pd.DataFrame()
        
        # Filter by well number if specified
        if well_number and 'well_number' in df.columns:
            station_data = station_data[station_data['well_number'] == well_number]
        
        return station_data
    
    def get_survival_data_for_chart(self, station_id: str, well_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Get survival data formatted for charting.
        
        Args:
            station_id: Station identifier
            well_number: Well number (optional)
            
        Returns:
            Dictionary with years and survival rates
        """
        station_data = self.get_station_data(station_id, well_number)
        
        if station_data.empty:
            return {"years": [], "survival_rates": [], "error": "No data found"}
        
        data = self.load_data()
        year_columns = data["survival_years"]
        
        # Get survival data
        years = []
        survival_rates = []
        
        for year in year_columns:
            year_col = str(year)
            if year_col in station_data.columns:
                # If multiple wells, take the average
                avg_rate = station_data[year_col].mean()
                if not pd.isna(avg_rate):
                    years.append(year)
                    survival_rates.append(float(avg_rate))
        
        return {
            "years": years,
            "survival_rates": survival_rates,
            "station_info": {
                "station_id": station_id,
                "well_number": well_number,
                "location": station_data['location'].iloc[0] if 'location' in station_data.columns and not station_data.empty else "Unknown",
                "province": station_data['province'].iloc[0] if 'province' in station_data.columns and not station_data.empty else "Unknown"
            }
        }
