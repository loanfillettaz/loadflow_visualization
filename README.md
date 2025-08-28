# Loadflow Visualizer

An open-source interactive tool for visualizing the results of multiperiod loadflow simulation of electrical networks, combining **geographical** and **temporal** dimensions.

## Objective

This tool allows the computation and visualization of multiperiod loadflow results along two dimensions:

- **Spatial representation**: visualization of bus and line locations on an interactive map.  
- **Temporal representation**: hourly navigation with a time slider.  

It offers an open-source and customizable alternative to commercial softwares such as *PowerFactory* or *Neplan* to visualize this kind of information.

## Features

- Display of bus voltages (magnitude and angle) and power (injected/consumed).  
- Display of line loading percentages.
- Interactive hourly time slider (`TimestampedGeoJson`).
- Support for multiple basemaps (`CartoDB`, `Swisstopo`).
- Export and storage of processed results.
- Modular and extensible architecture.
- Stochastic generation of load curves based on Swiss consumption data.  

## Libraries

- **Python** – core implementation and data processing  
- **PandaPower** – loadflow simulations and grid modeling  
- **Pandas** – structured data handling  
- **Folium / Leaflet.js** – interactive map visualization  

## Applications

- Educational support for teaching power systems and grid behavior  
- Decision-making aid for grid operators and planners  
- Research tool for analyzing the impact of DERs or load variability

---

This tool was developed as a part of the Bachelor's final project of Loan Fillettaz at HES-SO Valais-Wallis in Energy and Enviromental Engineering carried out at the [GridLab at HES-SO Valais-Wallis](https://gridlab.hevs.ch/).