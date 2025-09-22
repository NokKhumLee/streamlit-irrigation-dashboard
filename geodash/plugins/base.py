from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol

import streamlit as st


class DashboardPlugin(Protocol):
    name: str

    def render(self) -> None:  # pragma: no cover - streamlit side-effect
        ...


@dataclass
class PluginRegistry:
    _plugins: Dict[str, DashboardPlugin] = field(default_factory=dict)

    def register(self, plugin: DashboardPlugin) -> None:
        key = str(plugin.name)
        if key in self._plugins:
            st.warning(f"Plugin '{key}' already registered. Overwriting.")
        self._plugins[key] = plugin

    def render_all(self) -> None:
        for name, plugin in self._plugins.items():
            with st.expander(f"Plugin: {name}", expanded=False):
                plugin.render()



