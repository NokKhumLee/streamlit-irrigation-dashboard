# Geological Dashboard (Streamlit)
Interactive geological dashboard with two-column layout: folium map on the left and analytics on the right.

## Features
- Toggleable layers: polygons, wells, probability heatmap
- Filters: search, region, depth range
- Analytics: water level line chart, survival rate pie, probability by depth, cost estimation
- Metadata panel for selected well and CSV download
- Chat box placeholder for LLM

## Quickstart
1. Create a virtual environment (recommended)
   - Python 3.9+ (Currently test on 3.10.0)
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app
   ```bash
   streamlit run app.py
   ```
4. Open the URL shown in the terminal (usually `http://localhost:8501`).

## Tech
- Streamlit, Altair, Folium (`streamlit-folium`)

## Notes
- Uses mock data; connect to your real datasets for production.

## Project Structure
```
streamlit-irrigation-dashboard/
├─ app.py
├─ geodash/
│  ├─ __init__.py
│  ├─ data/
│  │  ├─ __init__.py
│  │  ├─ mock.py
│  │  └─ filters.py
│  ├─ ui/
│  │  ├─ __init__.py
│  │  ├─ map_panel.py
│  │  ├─ charts.py
│  │  └─ widgets.py
│  └─ plugins/
│     ├─ __init__.py
│     ├─ base.py
│     └─ examples.py
└─ requirements.txt
```

## Plugin System
- Minimal plugin registry allows plug-and-play widgets.
- Create a plugin by implementing a class with `name` and `render(self)`.

Example:
```python
from dataclasses import dataclass
import streamlit as st

@dataclass
class MyPlugin:
    name: str = "MyPlugin"
    def render(self):
        st.write("Hello from plugin")
```

Register and render in `app.py`:
```python
from geodash.plugins import PluginRegistry
registry = PluginRegistry()
registry.register(MyPlugin())
registry.render_all()
```
