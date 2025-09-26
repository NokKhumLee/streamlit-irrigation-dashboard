# BaDan (บาดาล)

Interactive ground water management dashboard with multi-page navigation and analytics.

## Project Structure

```
├── app.py                    # Main application
├── geodash/
│   ├── data/                 # Data loading & processing
│   ├── ui/                   # Maps, charts, widgets
│   └── plugins/              # Extensible plugin system
└── requirements.txt
```

## Features

**🏠 Main Dashboard**
- Interactive map with field polygons and well locations
- Cost estimation and metadata analysis
- CSV export functionality

**💧 Water Survival Analysis** 
- Time series water level charts
- Success/failure rate visualization
- Well performance tracking

**🔍 Underground Water Discovery**
- Probability heatmap for optimal drilling locations
- Success prediction by depth analysis
- Discovery zone recommendations

**🤖 AI Assistant**
- Chat interface for geological queries
- Notes plugin system
- Extensible plugin architecture

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**
   ```bash
   streamlit run app.py
   ```

3. **Open browser** → `http://localhost:8501`

## Tech Stack

Streamlit + Folium mapping + Altair charts + Pandas

## Adding Real Data

1. **Well Data**: Place `gov_groundwater_scope.csv` in `geodash/data/groundwater/`
2. **Field Polygons**: Place GeoJSON/Shapefile in `geodash/data/RDC_Fields/`
3. **Automatic Detection**: System loads real data when available, falls back to mock data otherwise