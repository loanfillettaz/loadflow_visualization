# Loadflow Visualizer

An interactive tool for visualizing loadflow simulation results in electrical networks, combining **geographical** and **temporal** dimensions.

## Objective
Most software such as *PowerFactory* or *Neplan* either provide static representations of loadflow results or allow temporal analysis without proper geographic visualization.  
This project bridges the gap by combining both:

- **Spatial representation**: visualization of bus and line locations on an interactive map.  
- **Temporal representation**: hourly navigation with a time slider.  

## Features
- Display of bus voltages (magnitude and angle) and power (injected/consumed).  
- Display of line loading percentages.  
- Interactive hourly time slider (`TimestampedGeoJson`).  
- Support for multiple basemaps (`CartoDB`, `Swisstopo`).  
- Export and storage of processed results.  
- Modular and extensible architecture.
- Stochastic generation of load curves based on Swiss consumption data.  

## Technologies
- **Python** – core implementation and data processing  
- **PandaPower** – loadflow simulations and grid modeling  
- **Pandas** – structured data handling  
- **Folium / Leaflet.js** – interactive map visualization  

## Applications
- Educational support for teaching power systems and grid behavior  
- Decision-making aid for grid operators and planners  
- Research tool for analyzing the impact of DERs or load variability  

## Author
**Loan Fillettaz** – Bachelor Thesis, HES-SO, 2025

