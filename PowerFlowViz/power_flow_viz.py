from typing import Tuple, Dict, List
import pandas as pd
from dataclasses import dataclass, field
from loadflow import LoadFlow
from data_prepare import DataPrepare
from grid_map_vizualizer import GridMapVisualizer

@dataclass
class PowerFlowViz:
    xls: pd.DataFrame
    Sb: int
    Vb: int
    f: int
    name_of_files: str
    
    df_stats: pd.DataFrame = pd.read_csv("../data/weekday_quantiles_winter.csv", sep=";")
    stochastic: bool = True
    from_col: str = "From"
    to_col: str = "To"
    line_col: str = "Line"
    length_col: str = "Length(m)"
    r_col: str = "R(Ohm/km)"
    x_col: str = "X(Ohm/km)"
    ampacity_col: str = "Ampacity (A)"
    plmax_col: str = "PLmax(kW)"
    qlmax_col: str = "QLmax(kVar)"
    pg_col: str = "Pg(kW)"
    from_xy_col: str = "From_XY"
    to_xy_col: str = "To_XY"

    columns: Dict[str, str] = field(init=False)
    node_df: pd.DataFrame = field(init=False)
    load_df: pd.DataFrame = field(init=False)
    line_df: pd.DataFrame = field(init=False)
    netbuilder: LoadFlow = field(init=False)
    net: object = field(init=False)

    def __post_init__(self):
        """Initialize column mapping after dataclass creation."""
        self.columns = {
            "from": self.from_col,
            "to": self.to_col,
            "line": self.line_col,
            "length": self.length_col,
            "r": self.r_col,
            "x": self.x_col,
            "ampacity": self.ampacity_col,
            "plmax": self.plmax_col,
            "qlmax": self.qlmax_col,
            "pg": self.pg_col,
            "from_xy": self.from_xy_col,
            "to_xy": self.to_xy_col
        }
        self._set_net()
        
    def _set_net(self) -> None:
        """
        Prepare dataframes and build the pandapower network.
        This initializes the node, load, and line data using DataPrepare,
        and constructs the network with buses, lines, and ext_grid.
        """
        dp = DataPrepare(self.xls, self.columns,stochastic=self.stochastic)
        prepared = dp.prepare_all(df_stats=self.df_stats)
        self.node_df = prepared["node_df"]
        self.load_list, self.node_with_power_unique = prepared["load_df"]
        self.line_df = prepared["line_df"]
        self.load_df = self.load_list["load_df"]

        builder = LoadFlow(
            xls=self.xls,
            Sb=self.Sb,
            Vb=self.Vb,
            f=self.f,
            name=self.name_of_files,
            columns=self.columns,
            node_df=self.node_df
        )
        self.netbuilder = builder
        self.net = builder.create_net_empty()

    def _map_center(self) -> Tuple[float, float]:
        """
        Compute central latitude and longitude for map centering.
        """
        lat = self.node_df["latitude"].mean()
        lon = self.node_df["longitude"].mean()
        return lat, lon

    def _iterate_hours(
        self,
        apply_fn,
        hours: List[int] = list(range(24))
    ) -> None:
        """
        Execute hourly loadflow and apply a callback function at each hour.
        Useful for visualization or data extraction per hour.
        """
        p_df = self.load_list["active_profile_df"]
        q_df = self.load_list["reactive_profile_df"]
        pv_df = self.load_list["pv_profile_df"]
        
        for hr in hours:
            hr_str = f"{hr:02d}:00"
            self.netbuilder.set_hourly_loads(self.net, hr_str, p_df, q_df, pv_df)
            self.netbuilder.run(self.net)
            apply_fn(hr_str)

    def generate_time_slider_map(
        self,
        hour_start: int = 0,
        hour_end: int = 24,
        save: bool = True,
        anonymous: bool = False
    ) -> GridMapVisualizer:
        """
        Visualize network performance over a daily range (e.g., 8h–18h).
        Uses folium to create a time-slider map, optionally anonymized.
        """
        center = self._map_center()
        viz = GridMapVisualizer(
            self.node_df,
            self.load_df,
            self.line_df,
            *center
        )
        viz.create_map_slider(anonymous=anonymous)

        def _plot(hr_str: str):
            layer = viz.plot_results(
                self.net,
                hr_str,
                self.node_with_power_unique
            )
            layer.add_to(viz.m)

        self._iterate_hours(
            _plot,
            hours=list(range(hour_start, hour_end))
        )
        viz.add_control()
        if save:
            fname = f"{self.name_of_files}_from_{hour_start}h_to_{hour_end}h"
            if anonymous:
                viz.save_map_anonymous(fname)
            else:
                viz.save_map(fname)
        return viz

    def generate_static_summary_map(
        self,
        save: bool = True,
        anonymous: bool = False
    ) -> GridMapVisualizer:
        """
        Generate a static map showing the max line loading and min voltage per bus
        across the 24h period, based on hourly loadflow results.
        """
        center = self._map_center()
        viz = GridMapVisualizer(
            self.node_df,
            self.load_df,
            self.line_df,
            *center
        )
        viz.create_map_graphical(anonymous=anonymous)

        line_hist: Dict[str, List[float]] = {}
        bus_hist: Dict[str, List[float]] = {}

        def _collect(hr_str: str):
            rl = self.net.res_line.copy()
            rl["name"] = self.net.line["name"].astype(str)
            rb = self.net.res_bus.copy()
            rb["name"] = self.net.bus["name"].astype(str)

            for _, r in rl.iterrows():
                line_hist.setdefault(r["name"], []).append(r["loading_percent"])
                
            for _, r in rb.iterrows():
                bus_hist.setdefault(r["name"], []).append(r["vm_pu"]) if r["name"] in self.node_with_power_unique else None

        self._iterate_hours(_collect)

        max_load = {n: max(v) for n, v in line_hist.items()}
        min_volt = {n: min(v) for n, v in bus_hist.items()}

        viz.plot_static_results(
            self.line_df,
            self.node_df,
            max_load,
            min_volt,
            line_hist,
            bus_hist
        )
        viz.add_control()
        if save:
            if anonymous:
                viz.save_map_anonymous(f"{self.name_of_files}_static_max_view")
            else:
                viz.save_map(f"{self.name_of_files}_static_max_view")
        return viz

    def export_net(self) -> object:
        """
        Return the internal pandapower network (pp.pandapowerNet) object.
        Useful for inspection or export.
        """
        return self.net
