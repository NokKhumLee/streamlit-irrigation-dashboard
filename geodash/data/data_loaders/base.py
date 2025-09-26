"""
Base classes and interfaces for data loaders.
Provides common functionality and consistent patterns for all specialized loaders.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging
import warnings

# Try to import geospatial libraries with graceful fallback
try:
    import geopandas as gpd
    GEOSPATIAL_AVAILABLE = True
except ImportError:
    GEOSPATIAL_AVAILABLE = False
    warnings.warn("GeoPandas not available. Real geospatial data loading disabled.")


class BaseDataLoader(ABC):
    """
    Abstract base class for all data loaders.
    Provides common functionality and enforces consistent interface.
    """
    
    def __init__(self, data_dir: Union[str, Path] = "geodash/data"):
        self.data_dir = Path(data_dir)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Common data directories
        self.rdc_fields_dir = self.data_dir / "RDC_Fields"
        self.rdc_farms_dir = self.data_dir / "RDC_Farms"
        self.groundwater_dir = self.data_dir / "groundwater"
        
    @abstractmethod
    def load(self) -> Any:
        """
        Load the specific data type handled by this loader.
        Must be implemented by all concrete loaders.
        
        Returns:
            The loaded data in the appropriate format for this loader.
        """
        pass
    
    @abstractmethod
    def _load_fallback_data(self) -> Any:
        """
        Load fallback/mock data when real data is unavailable.
        Must be implemented by all concrete loaders.
        
        Returns:
            Mock data in the same format as real data.
        """
        pass
    
    def _file_exists(self, file_path: Union[str, Path]) -> bool:
        """Check if a file exists with proper error handling."""
        try:
            return Path(file_path).exists()
        except Exception as e:
            self.logger.warning(f"Error checking file existence {file_path}: {e}")
            return False
    
    def _find_files_with_extensions(self, directory: Path, extensions: List[str]) -> List[Path]:
        """Find all files in directory with given extensions."""
        if not directory.exists():
            return []
        
        files = []
        for ext in extensions:
            files.extend(directory.glob(f"*{ext}"))
            files.extend(directory.glob(f"*{ext.upper()}"))
        
        return files
    
    def _log_loading_attempt(self, data_type: str, file_path: Optional[Path] = None):
        """Log data loading attempts for debugging."""
        if file_path:
            self.logger.info(f"🔄 Loading {data_type} from {file_path}")
        else:
            self.logger.info(f"🔄 Loading {data_type}")
    
    def _log_success(self, data_type: str, count: int, source: str = "real"):
        """Log successful data loading."""
        emoji = "✅" if source == "real" else "🔄"
        self.logger.info(f"{emoji} Loaded {count} {data_type} items ({source} data)")
    
    def _log_fallback(self, data_type: str, reason: str):
        """Log fallback to mock data."""
        self.logger.warning(f"⚠️  {data_type}: {reason}. Using fallback data.")


class BaseGeospatialLoader(BaseDataLoader):
    """
    Base class for loaders that handle geospatial data.
    Provides common geospatial utilities and error handling.
    """
    
    def __init__(self, data_dir: Union[str, Path] = "geodash/data"):
        super().__init__(data_dir)
        
        if not GEOSPATIAL_AVAILABLE:
            self.logger.warning("GeoPandas not available. Geospatial features disabled.")
    
    def _load_geospatial_file(self, file_path: Path) -> Optional[gpd.GeoDataFrame]:
        """Load a geospatial file with error handling."""
        if not GEOSPATIAL_AVAILABLE:
            return None
        
        try:
            self._log_loading_attempt("geospatial file", file_path)
            gdf = gpd.read_file(file_path)
            
            # Convert to WGS84 if not already
            if gdf.crs is not None and gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            
            return gdf
            
        except Exception as e:
            self.logger.error(f"❌ Error loading {file_path}: {e}")
            return None
    
    def _extract_coordinates_from_geometry(self, geometry) -> List[List[float]]:
        """Extract coordinate pairs from Shapely geometry."""
        try:
            if geometry is None or geometry.is_empty:
                return []
            
            if geometry.geom_type == 'Polygon':
                coords = list(geometry.exterior.coords)[:-1]  # Remove closing coordinate
                return [[float(coord[1]), float(coord[0])] for coord in coords]  # lat, lon
            
            elif geometry.geom_type == 'MultiPolygon':
                geoms_list = list(geometry.geoms)
                if geoms_list:
                    first_polygon = geoms_list[0]
                    coords = list(first_polygon.exterior.coords)[:-1]
                    return [[float(coord[1]), float(coord[0])] for coord in coords]
            
        except Exception as e:
            self.logger.warning(f"⚠️  Error extracting coordinates: {e}")
            return []
        
        return []
    
    def _find_field_value(self, row, field_names: List[str], default: str = None) -> Optional[str]:
        """Find the first available field value from a list of possible field names."""
        for field in field_names:
            if field in row.index and row[field] is not None and str(row[field]).strip():
                return str(row[field]).strip()
        return default


class DataValidationMixin:
    """Mixin class providing common data validation utilities."""
    
    @staticmethod
    def _validate_coordinates(coords: List[List[float]]) -> bool:
        """Validate that coordinates are properly formatted."""
        if not coords or len(coords) < 3:
            return False
        
        for coord in coords:
            if len(coord) != 2:
                return False
            lat, lon = coord
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return False
        
        return True
    
    @staticmethod
    def _validate_wells_dataframe(df) -> bool:
        """Validate wells DataFrame has required columns and data."""
        if df is None or df.empty:
            return False
        
        required_columns = ['well_id', 'lat', 'lon', 'depth_m', 'region', 'survived']
        return all(col in df.columns for col in required_columns)
    
    @staticmethod
    def _clean_string_field(value: Any) -> str:
        """Clean and standardize string fields."""
        if value is None:
            return ""
        return str(value).strip()


class ColorManager:
    """Utility class for managing colors in visualizations."""
    
    FARM_COLORS = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
        "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
        "#F8C471", "#82E0AA", "#F1948A", "#85C1E9", "#F4D03F",
        "#D7BDE2", "#7FB3D3", "#A9DFBF", "#F9E79F", "#FADBD8"
    ]
    
    @classmethod
    def get_farm_color(cls, index: int) -> str:
        """Get a farm color by index (cycles through available colors)."""
        return cls.FARM_COLORS[index % len(cls.FARM_COLORS)]
    
    @classmethod
    def get_well_color(cls, survived: bool) -> str:
        """Get well color based on survival status."""
        return "#238b45" if survived else "#cb181d"


# Export all base classes and mixins
__all__ = [
    "BaseDataLoader",
    "BaseGeospatialLoader", 
    "DataValidationMixin",
    "ColorManager",
    "GEOSPATIAL_AVAILABLE"
]