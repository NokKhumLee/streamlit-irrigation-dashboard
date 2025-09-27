"""
Rain data service for fetching historical rainfall data from Open-Meteo API.
Provides functionality to get rain statistics for specific coordinates and time periods.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import streamlit as st

try:
    import openmeteo_requests
    import requests_cache
    from retry_requests import retry
except ImportError:
    st.error("Missing required packages for rain data. Please install: openmeteo-requests, requests-cache, retry-requests")
    openmeteo_requests = None
    requests_cache = None
    retry = None


class RainDataService:
    """Service for fetching and processing historical rain data from Open-Meteo API."""
    
    def __init__(self):
        """Initialize the rain data service with API client setup."""
        if openmeteo_requests is None:
            self.client = None
            return
            
        # Setup the Open-Meteo API client with cache and retry on error
        cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.client = openmeteo_requests.Client(session=retry_session)
    
    def get_rain_data(
        self, 
        latitude: float, 
        longitude: float, 
        days_back: int = 365,
        timezone: str = "Asia/Bangkok"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical rain data for specified coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate  
            days_back: Number of days to look back (default: 365 for 1 year)
            timezone: Timezone for the data (default: Asia/Bangkok)
            
        Returns:
            DataFrame with rain data or None if error
        """
        if self.client is None:
            st.error("Rain data service not available. Missing required packages.")
            return None
            
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for API
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            # API parameters
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "hourly": "rain",
                "timezone": timezone,
            }
            
            # Make API request
            responses = self.client.weather_api(url, params=params)
            response = responses[0]
            
            # Process hourly data
            hourly = response.Hourly()
            hourly_rain = hourly.Variables(0).ValuesAsNumpy()
            
            # Create DataFrame
            hourly_data = {
                "date": pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left"
                )
            }
            hourly_data["rain"] = hourly_rain
            
            hourly_dataframe = pd.DataFrame(data=hourly_data)
            
            # Convert to Bangkok timezone
            hourly_dataframe['date'] = hourly_dataframe['date'].dt.tz_convert(timezone)
            
            return hourly_dataframe
            
        except Exception as e:
            st.error(f"Error fetching rain data: {str(e)}")
            return None
    
    def get_monthly_rain_summary(self, rain_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get monthly rain summary from hourly data.
        
        Args:
            rain_df: DataFrame with hourly rain data
            
        Returns:
            DataFrame with monthly rain totals
        """
        if rain_df is None or rain_df.empty:
            return pd.DataFrame()
            
        try:
            # Resample to monthly and sum rain
            monthly_data = rain_df.resample('M', on='date')['rain'].sum().reset_index()
            monthly_data['month'] = monthly_data['date'].dt.strftime('%Y-%m')
            monthly_data['rain_mm'] = monthly_data['rain']
            
            return monthly_data[['month', 'rain_mm']]
            
        except Exception as e:
            st.error(f"Error processing monthly rain data: {str(e)}")
            return pd.DataFrame()
    
    def get_rain_statistics(self, rain_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate rain statistics from the data.
        
        Args:
            rain_df: DataFrame with rain data
            
        Returns:
            Dictionary with rain statistics
        """
        if rain_df is None or rain_df.empty:
            return {}
            
        try:
            stats = {
                'total_rain_mm': float(rain_df['rain'].sum()),
                'avg_daily_rain_mm': float(rain_df['rain'].mean()),
                'max_daily_rain_mm': float(rain_df['rain'].max()),
                'rainy_days': int((rain_df['rain'] > 0).sum()),
                'total_days': len(rain_df),
                'rain_frequency': float((rain_df['rain'] > 0).mean())
            }
            
            return stats
            
        except Exception as e:
            st.error(f"Error calculating rain statistics: {str(e)}")
            return {}
    
    def get_farm_center_coordinates(self, farm_coordinates: List[List[float]]) -> Tuple[float, float]:
        """
        Calculate center coordinates from farm polygon coordinates.
        
        Args:
            farm_coordinates: List of [lat, lon] coordinate pairs
            
        Returns:
            Tuple of (center_lat, center_lon)
        """
        if not farm_coordinates:
            return 0.0, 0.0
            
        try:
            lats = [coord[0] for coord in farm_coordinates]
            lons = [coord[1] for coord in farm_coordinates]
            
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            
            return center_lat, center_lon
            
        except Exception as e:
            st.error(f"Error calculating farm center coordinates: {str(e)}")
            return 0.0, 0.0


# Global instance for caching
_rain_service = None

def get_rain_service() -> RainDataService:
    """Get or create the global rain service instance."""
    global _rain_service
    if _rain_service is None:
        _rain_service = RainDataService()
    return _rain_service
