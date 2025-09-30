"""
Page module for the Badan geological dashboard.
Each page is a separate module for better organization.
"""

from .main_dashboard import render_main_dashboard
from .water_survival import render_water_survival
from .discovery import render_discovery
from .ai_assistant import render_ai_assistant

__all__ = [
    "render_main_dashboard",
    "render_water_survival",
    "render_discovery",
    "render_ai_assistant",
]