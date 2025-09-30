"""
Wells data loader for government groundwater CSV files.
Handles loading, cleaning, and processing of well/groundwater data.
Updated to include distance_to_farm column and filtering.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')


class WellsLoader:
    """Loader for wells/groundwater data from CSV files."""
    
    def __init__(self, data_dir: str = "geodash/data"):
        self.data_dir = Path(data_dir)
        self.groundwater_dir = self.data_dir / "groundwater"
        # Updated CSV file path
        self.csv_file = self.groundwater_dir / "groundwater_completed.csv"
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def load(self, max_distance_to_farm_m: Optional[float] = None) -> pd.DataFrame:
        """
        Load wells data from CSV file or fallback to mock data.
        
        Args:
            max_distance_to_farm_m: Maximum distance to farm in meters (None = no filter, load all)
        
        Returns:
            DataFrame with columns: well_id, region, lat, lon, depth_m, survived, distance_to_farm
        """
        # Try to load real data first
        if self._file_exists(self.csv_file):
            try:
                self._log_loading_attempt("wells data", self.csv_file)
                df = pd.read_csv(self.csv_file, encoding='utf-8')
                wells_df = self._process_groundwater_csv(df)
                
                if self._validate_wells_dataframe(wells_df):
                    # Apply distance filter ONLY if specified
                    if max_distance_to_farm_m is not None:
                        filtered_wells_df = self._apply_distance_filter(wells_df, max_distance_to_farm_m)
                        self._log_data_summary("wells", len(filtered_wells_df), filtered_wells_df, "real")
                        self._log_distance_filter_summary(wells_df, filtered_wells_df, max_distance_to_farm_m)
                        return filtered_wells_df
                    else:
                        # No filter - return all wells
                        self._log_data_summary("wells", len(wells_df), wells_df, "real")
                        self.logger.info("📍 Loaded ALL wells (no distance filter applied)")
                        return wells_df
                else:
                    self._log_fallback("wells data", "Invalid data structure after processing")
                    
            except Exception as e:
                self._log_fallback("wells data", f"Error loading CSV: {e}")
        else:
            self._log_fallback("wells data", f"File not found: {self.csv_file}")
        
        # Fallback to mock data
        return self._load_fallback_data(max_distance_to_farm_m)
    
    def _file_exists(self, file_path: Path) -> bool:
        """Check if a file exists."""
        try:
            return file_path.exists()
        except Exception:
            return False
    
    def _log_loading_attempt(self, data_type: str, file_path: Path):
        """Log data loading attempts."""
        self.logger.info(f"🔄 Loading {data_type} from {file_path}")
    
    def _log_fallback(self, data_type: str, reason: str):
        """Log fallback to mock data."""
        self.logger.warning(f"⚠️  {data_type}: {reason}. Using fallback data.")
    
    def _log_data_summary(self, data_type: str, count: int, data, source: str):
        """Log data loading summary."""
        emoji = "✅" if source == "real" else "🔄"
        self.logger.info(f"{emoji} Loaded {count} {data_type} items ({source} data)")
    
    def _load_fallback_data(self, max_distance_to_farm_m: Optional[float]) -> pd.DataFrame:
        """Load mock wells data with distance_to_farm column."""
        from ..mockup import generate_mock_data
        
        mock_data = generate_mock_data()
        wells_df = mock_data["wells_df"]
        
        # Add mock distance column if not present (up to 30km range)
        if 'distance_to_farm' not in wells_df.columns:
            rng = np.random.default_rng(42)
            wells_df['distance_to_farm'] = rng.uniform(100, 30000, size=len(wells_df))
        
        # Apply filter ONLY if specified
        if max_distance_to_farm_m is not None:
            wells_df = self._apply_distance_filter(wells_df, max_distance_to_farm_m)
            self._log_distance_filter_summary(mock_data["wells_df"], wells_df, max_distance_to_farm_m)
        else:
            self.logger.info("📍 Loaded ALL mock wells (no distance filter)")
        
        self._log_data_summary("wells", len(wells_df), wells_df, "mock")
        return wells_df
    
    def _process_groundwater_csv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process and clean the government groundwater CSV data.
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
                'Longitude': 'lon',
                'distance_to_farm': 'distance_to_farm'  # Keep the new column as-is
            }
            
            # Clean and rename columns
            processed_df = self._clean_dataframe_columns(df, column_mapping)
            
            # Ensure required columns exist
            required_cols = ['well_id', 'lat', 'lon', 'distance_to_farm']
            missing_cols = [col for col in required_cols if col not in processed_df.columns]
            if missing_cols:
                self.logger.error(f"❌ Missing required columns: {missing_cols}")
                return pd.DataFrame()
            
            # Convert coordinates to numeric
            processed_df = self._convert_coordinates_to_numeric(processed_df)
            
            # Convert distance_to_farm to numeric
            processed_df['distance_to_farm'] = pd.to_numeric(processed_df['distance_to_farm'], errors='coerce')
            
            # Remove rows with invalid distance_to_farm
            initial_count = len(processed_df)
            processed_df = processed_df.dropna(subset=['distance_to_farm'])
            if len(processed_df) < initial_count:
                self.logger.warning(f"⚠️  Removed {initial_count - len(processed_df)} rows with invalid distance_to_farm values")
            
            # Generate well IDs if missing
            processed_df = self._generate_well_id_if_missing(processed_df)
            
            # Process depth data
            processed_df = self._process_depth_data(processed_df)
            
            # Create region from amphoe (district)
            processed_df = self._process_region_data(processed_df)
            
            # Generate survival status
            processed_df = self._process_survival_data(processed_df)
            
            # Select and validate final columns
            final_cols = ['well_id', 'region', 'lat', 'lon', 'depth_m', 'survived', 'distance_to_farm']
            processed_df = processed_df[final_cols]
            
            # Ensure data types
            processed_df['well_id'] = processed_df['well_id'].astype(str)
            processed_df['depth_m'] = processed_df['depth_m'].astype(int)
            processed_df['survived'] = processed_df['survived'].astype(bool)
            processed_df['distance_to_farm'] = processed_df['distance_to_farm'].astype(float)
            
            self._log_processing_summary(processed_df)
            return processed_df
            
        except Exception as e:
            self.logger.error(f"❌ Error processing groundwater CSV: {e}")
            return pd.DataFrame()
    
    def _clean_dataframe_columns(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """Clean DataFrame by renaming columns."""
        cleaned_df = df.copy()
        cleaned_df = cleaned_df.rename(columns=column_mapping)
        
        # Strip whitespace from string columns
        for col in cleaned_df.select_dtypes(include=['object']).columns:
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
        
        return cleaned_df
    
    def _convert_coordinates_to_numeric(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert coordinate columns to numeric."""
        df_clean = df.copy()
        
        # Convert to numeric
        df_clean['lat'] = pd.to_numeric(df_clean['lat'], errors='coerce')
        df_clean['lon'] = pd.to_numeric(df_clean['lon'], errors='coerce')
        
        # Remove rows with invalid coordinates
        df_clean = df_clean.dropna(subset=['lat', 'lon'])
        df_clean = df_clean[
            (df_clean['lat'].between(-90, 90)) & 
            (df_clean['lon'].between(-180, 180))
        ]
        
        return df_clean
    
    def _generate_well_id_if_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate well IDs for rows that are missing them."""
        df_with_ids = df.copy()
        
        if 'well_id' not in df_with_ids.columns:
            df_with_ids['well_id'] = [f"WELL-{i:03d}" for i in range(1, len(df_with_ids) + 1)]
        else:
            missing_mask = df_with_ids['well_id'].isna() | (df_with_ids['well_id'] == '')
            missing_count = missing_mask.sum()
            
            if missing_count > 0:
                start_idx = len(df_with_ids) - missing_count + 1
                generated_ids = [f"WELL-{i:03d}" for i in range(start_idx, start_idx + missing_count)]
                df_with_ids.loc[missing_mask, 'well_id'] = generated_ids
        
        return df_with_ids
    
    def _generate_realistic_depths(self, size: int) -> np.ndarray:
        """Generate realistic well depths."""
        rng = np.random.default_rng(42)
        beta_values = rng.beta(2, 2, size)
        depths = 40 + beta_values * (220 - 40)
        return depths.astype(int)
    
    def _calculate_success_probability(self, depth: float) -> float:
        """Calculate success probability based on depth."""
        if 80 <= depth <= 150:
            return 0.85 + np.random.normal(0, 0.05)
        elif depth < 80:
            factor = depth / 80
            return 0.6 * factor + np.random.normal(0, 0.1)
        else:
            factor = max(0.1, 1.0 - (depth - 150) / 100)
            return 0.7 * factor + np.random.normal(0, 0.1)
    
    def _apply_distance_filter(self, df: pd.DataFrame, max_distance_m: float) -> pd.DataFrame:
        """Apply distance to farm filter."""
        if 'distance_to_farm' not in df.columns:
            self.logger.warning("⚠️  distance_to_farm column not found, returning unfiltered data")
            return df
        
        filtered_df = df[df['distance_to_farm'] <= max_distance_m].copy()
        return filtered_df
    
    def _log_distance_filter_summary(self, original_df: pd.DataFrame, filtered_df: pd.DataFrame, max_distance_m: float) -> None:
        """Log summary of distance filtering operation."""
        if 'distance_to_farm' not in original_df.columns:
            return
        
        original_count = len(original_df)
        filtered_count = len(filtered_df)
        removed_count = original_count - filtered_count
        
        self.logger.info(f"🏚️  Distance Filter Applied:")
        self.logger.info(f"   • Max distance: {max_distance_m/1000:.1f} km")
        self.logger.info(f"   • Original wells: {original_count:,}")
        self.logger.info(f"   • Filtered wells: {filtered_count:,}")
        self.logger.info(f"   • Removed wells: {removed_count:,} ({100*removed_count/original_count:.1f}%)")
        
        if not filtered_df.empty:
            min_dist = filtered_df['distance_to_farm'].min()
            max_dist = filtered_df['distance_to_farm'].max()
            avg_dist = filtered_df['distance_to_farm'].mean()
            self.logger.info(f"   • Distance range: {min_dist:.0f}m - {max_dist:.0f}m (avg: {avg_dist:.0f}m)")
    
    def _process_depth_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process well depth information."""
        if 'depth_drilled' in df.columns:
            df['depth_m'] = pd.to_numeric(df['depth_drilled'], errors='coerce')
        elif 'depth_developed' in df.columns:
            df['depth_m'] = pd.to_numeric(df['depth_developed'], errors='coerce')
        else:
            df['depth_m'] = self._generate_realistic_depths(len(df))
            self.logger.warning("⚠️  No depth data found, using generated depths")
        
        # Fill missing depth values
        missing_depths = df['depth_m'].isna()
        if missing_depths.any():
            df.loc[missing_depths, 'depth_m'] = self._generate_realistic_depths(missing_depths.sum())
        
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
        df['region'] = df['region'].apply(lambda x: str(x).strip() if x is not None else "")
        
        return df
    
    def _process_survival_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process well survival/success status."""
        if 'water_volume' in df.columns:
            water_vol = pd.to_numeric(df['water_volume'], errors='coerce')
            df['survived'] = (water_vol > 1.0).fillna(False)
        else:
            df['survived'] = df['depth_m'].apply(
                lambda depth: np.random.random() < self._calculate_success_probability(depth)
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
        
        # Distance to farm statistics
        if 'distance_to_farm' in df.columns:
            dist_range = f"{df['distance_to_farm'].min():.0f}-{df['distance_to_farm'].max():.0f}m"
            avg_dist = f"{df['distance_to_farm'].mean():.0f}m"
            self.logger.info(f"🏚️  Distance to farm range: {dist_range} (avg: {avg_dist})")
        
        # Regional distribution
        region_counts = df['region'].value_counts().head(3)
        top_regions = ", ".join([f"{region} ({count})" for region, count in region_counts.items()])
        self.logger.info(f"🌍 Top regions: {top_regions}")
    
    def _validate_wells_dataframe(self, df) -> bool:
        """Validate wells DataFrame has required columns and data."""
        if df is None or df.empty:
            return False
        
        required_columns = ['well_id', 'lat', 'lon', 'depth_m', 'region', 'survived', 'distance_to_farm']
        return all(col in df.columns for col in required_columns)
    
    def get_distance_statistics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Get statistics about distance to farm values."""
        if df.empty or 'distance_to_farm' not in df.columns:
            return {}
        
        return {
            'min_distance_m': float(df['distance_to_farm'].min()),
            'max_distance_m': float(df['distance_to_farm'].max()),
            'mean_distance_m': float(df['distance_to_farm'].mean()),
            'median_distance_m': float(df['distance_to_farm'].median()),
            'std_distance_m': float(df['distance_to_farm'].std()),
            'count_within_1km': int((df['distance_to_farm'] <= 1000).sum()),
            'count_within_5km': int((df['distance_to_farm'] <= 5000).sum()),
            'count_within_10km': int((df['distance_to_farm'] <= 10000).sum()),
        }


# Export the loader class
__all__ = ["WellsLoader"]