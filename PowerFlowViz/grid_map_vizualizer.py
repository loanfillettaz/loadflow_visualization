import matplotlib
matplotlib.use('Agg')
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from folium import Element
import branca
import pandas as pd
import io
import base64
from dataclasses import dataclass

@dataclass
class GridMapVisualizer:
    node_df: pd.DataFrame
    load_df: pd.DataFrame
    line_df: pd.DataFrame
    lat0: float
    lon0: float

    def __post_init__(self):
        """
        Initialize internal map and color attributes.
        """
        self.m = None
        self.colormap = None
        self.colormap2 = None

    def create_map_slider(self,anonymous: bool = None) -> None:
        """
        Create a time-slider map with standard tile layers and styling.
        """
        self._create_base_map_black() if anonymous else self._create_base_map()
        self._add_tile_layers() if not anonymous else None
        self._add_colormaps()
        self._add_css()
        self._add_slider()
        self._add_visibility_controls()

    def create_map_graphical(self, anonymous: bool = None) -> None:
        """
        Create a static graphical map with custom base layers and legends.
        """
        self._create_base_map_black() if  anonymous else self._create_base_map()
        self._add_tile_layers() if not anonymous else None
        self._add_colormaps()
        self._add_css()
        self._add_visibility_controls()

    def _create_base_map_white(self) -> None:
        """
        Create a fully white base map without tile layers.
        """
        self.m = folium.Map(
            location=[self.lat0, self.lon0],
            zoom_start=18,
            tiles=None,
            max_zoom=20,
        )
        css = """
            <style>
                .leaflet-container {
                    background-color: white !important;
                }
            </style>
        """
        self.m.get_root().html.add_child(Element(css))

    def _create_base_map_black(self) -> None:
        """
        Create a fully black base map without tile layers.
        """
        self.m = folium.Map(
            location=[self.lat0, self.lon0],
            zoom_start=18,
            tiles=None,
            max_zoom=20,
        )
        css = """
            <style>
                .leaflet-container {
                    background-color: black !important;
                }
            </style>
        """
        self.m.get_root().html.add_child(Element(css))

    def _create_base_map(self) -> None:
        """
        Create a dark-themed base map centered on the provided latitude and longitude.
        """
        self.m = folium.Map(
            location=[self.lat0, self.lon0],
            zoom_start=18,
            tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attr="© CartoDB",
            name="CartoDB Dark Matter",
            max_zoom=20
        )

    def _add_tile_layers(self) -> None:
        """
        Add Swisstopo orthophoto tile layer to the map.
        """
        folium.TileLayer(
            tiles="https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg",
            attr="© swisstopo",
            name="Swisstopo Swissimage (Ortho)",
            overlay=True,
            control=False,
            max_zoom=20,
            opacity=0.6
        ).add_to(self.m)

    def _style_colormap(self, cmap: branca.colormap.LinearColormap) -> None:
        """
        Apply consistent CSS styling to colormap legends.
        """
        cmap.caption_style = {'font-size': '14px', 'font-weight': 'bold'}
        cmap.style = {
            'background-color': 'rgba(255, 255, 255, 1)',
            'padding': '6px',
            'border-radius': '6px',
            'box-shadow': '2px 2px 5px rgba(0, 0, 0, 0.3)'
        }

    def _add_colormaps(self) -> None:
        """
        Add and style the colorbars for line loading and voltage magnitude.
        Also includes a JS-based legend to explain overload and reference symbols.
        """
        self.colormap = branca.colormap.LinearColormap(
            [mcolors.to_hex(c) for c in sns.color_palette("RdYlGn_r")],
            vmin=0, vmax=100, caption="Line loading [%]"
        )
        self._style_colormap(self.colormap)
        self.colormap.add_to(self.m)

        colors2 = sns.diverging_palette(200, 200, s=100, l=50, center="light", n=256)
        self.colormap2 = branca.colormap.LinearColormap(
            [mcolors.to_hex(c) for c in colors2],
            vmin=0.9, vmax=1.1, caption="Voltage value [p.u.]"
        )
        self._style_colormap(self.colormap2)
        self.colormap2.add_to(self.m)

        overload_note = """
            <script>
                setTimeout(function() {
                    const legends = document.querySelectorAll('.legend');
                    legends.forEach(legend => {
                        const label = legend.textContent || "";
                        if (label.includes("Line loading [%]") && !legend.innerHTML.includes("Line Overload")) {
                            const combinedDiv = document.createElement("div");
                            combinedDiv.style.marginTop = "6px";
                            combinedDiv.style.display = "flex";
                            combinedDiv.style.alignItems = "center";
                            combinedDiv.style.gap = "14px";

                            // Line Overload
                            const overloadItem = document.createElement("div");
                            overloadItem.style.display = "flex";
                            overloadItem.style.alignItems = "center";
                            overloadItem.innerHTML = `
                                <div style="width: 14px; height: 14px; background-color: #EE82EE; margin-right: 6px; border-radius: 2px;"></div>
                                <strong>Line Overload</strong>`;

                            // Bus Reference (limegreen triangle)
                            const busRefItem = document.createElement("div");
                            busRefItem.style.display = "flex";
                            busRefItem.style.alignItems = "center";
                            busRefItem.innerHTML = `
                                <div style="
                                    width: 0;
                                    height: 0;
                                    border-left: 7px solid transparent;
                                    border-right: 7px solid transparent;
                                    border-bottom: 12px solid limegreen;
                                    margin-right: 6px;
                                "></div>
                                <strong>Bus reference</strong>`;

                            // Voltage Alert (red triangle)
                            const voltageAlertItem = document.createElement("div");
                            voltageAlertItem.style.display = "flex";
                            voltageAlertItem.style.alignItems = "center";
                            voltageAlertItem.innerHTML = `
                                <div style="
                                    width: 0;
                                    height: 0;
                                    border-left: 7px solid transparent;
                                    border-right: 7px solid transparent;
                                    border-bottom: 12px solid red;
                                    margin-right: 6px;
                                "></div>
                                <strong>Voltage alert</strong>`;

                            combinedDiv.appendChild(overloadItem);
                            combinedDiv.appendChild(busRefItem);
                            combinedDiv.appendChild(voltageAlertItem);

                            legend.appendChild(combinedDiv);
                        }
                    });
                }, 500);
            </script>
            """
        self.m.get_root().html.add_child(Element(overload_note))

    def _add_css(self) -> None:
        """
        Inject custom CSS styles for legends, popups, and colorbars.
        This enhances the visual presentation of map elements.
        """
        css =  """
            <style>
            .legend {
                position: relative !important;
                display: grid !important;
                margin-bottom: 12px;
                padding: 8px 12px;
                background: rgba(255, 255, 255, 0.9);
                border-radius: 8px;
                font-family: 'Segoe UI', Tahoma, sans-serif;
                font-size: 13px;
                color: #222;
                width: fit-content;
                z-index: 1000;
            }

            .leaflet-control {
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 10px;
                padding: 5px;
                z-index: 1000;
            }

            .legend .caption {
                font-weight: 600;
                margin-bottom: 6px;
                display: block;
            }

            .colorbar {
                border-radius: 8px !important;
                overflow: hidden;
                height: 14px !important;
            }

            .leaflet-popup-content-wrapper {
                background: rgba(255, 255, 255, 1) !important;
                border-radius: 10px !important;
                max-width: none !important;
                min-width: 300px !important;
                width: fit-content !important;
                box-shadow: 3px 3px 10px rgba(0,0,0,0.3) !important;
                padding: 12px 16px !important;
                font-family: "Segoe UI", Tahoma, sans-serif !important;
                font-size: 15px !important;
                color: #222 !important;
                line-height: 1.8 !important;
            }

            .leaflet-popup-content-wrapper br {
                display: block;
                margin-bottom: 4px;
            }
            .leaflet-popup-content-wrapper ul {
                padding-left: 18px;
                margin: 0;
            }

            .leaflet-popup-content-wrapper li {
                margin-bottom: 4px;
            }
            .leaflet-popup-content {
                width: fit-content !important;
                min-width: 300px !important;
                max-width: none !important;
            }
            </style>
            """
        self.m.get_root().html.add_child(Element(css))

    def _add_slider(self) -> None:
        """
        Add a custom HTML/JS slider to the map allowing users to select the hour.
        This slider toggles visibility of hourly FeatureGroups based on their label.
        """
        slider_html = """
            <div id="hour-slider-container" style="
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background-color: rgba(255, 255, 255, 0.7);
                padding: 5px 10px;
                border-radius: 10px;
                z-index: 9999;
                font-family: sans-serif;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);
            ">
                <label for="hourSlider"><strong>Hour:</strong> <span id="hourLabel">00:00</span></label><br>
                <input type="range" min="0" max="23" value="0" class="slider" id="hourSlider" step="1">
            </div>

            <script>
            document.getElementById('hourSlider').addEventListener('input', function(e) {
                var hour = String(e.target.value).padStart(2, '0') + ":00";
                document.getElementById('hourLabel').textContent = hour;

                var layers = document.querySelectorAll('.leaflet-control-layers-overlays input[type=checkbox]');
                layers.forEach(function(layer) {
                    if (layer.nextSibling.textContent.trim() === hour) {
                        if (!layer.checked) layer.click();
                    } else {
                        if (layer.checked) layer.click();
                    }
                });
            });
            </script>
            """
        self.m.get_root().html.add_child(Element(slider_html))

    def _add_visibility_controls(self) -> None:
        """
        Add visibility checkboxes to control display of nodes and lines on the map.
        Includes embedded JS logic for toggling map element visibility by class.
        """
        visibility_controls = """
            <div id="visibility-controls" style="
                position: absolute;
                top: 150px;
                right: 10px;
                background: rgba(255, 255, 255, 0.9);
                padding: 10px 14px;
                border-radius: 10px;
                z-index: 9999;
                font-family: sans-serif;
                font-size: 14px;
                max-width: 200px;
            ">
                <strong style="margin-bottom: 6px; display: block;">Éléments à afficher</strong>
                <label><input type="checkbox" id="toggleNodes" checked> Nodes</label><br>
                <label><input type="checkbox" id="toggleLines" checked> Lines</label><br>
            </div>

            <script>
            function toggleClassVisibility(checkboxId, className) {
                document.getElementById(checkboxId).addEventListener("change", function(e) {
                    var show = e.target.checked;
                    document.querySelectorAll("." + className).forEach(function(el) {
                        el.style.display = show ? "block" : "none";
                    });
                });
            }
            toggleClassVisibility("toggleNodes", "bus-marker");
            toggleClassVisibility("toggleLines", "line-polyline");
            </script>
            """
        self.m.get_root().html.add_child(Element(visibility_controls))

    def _get_line_color(self, loading: float) -> str:
        """Return color for a line based on loading percentage."""
        return "#EE82EE" if loading > 100 else self.colormap(min(max(loading, 0), 100))

    def _get_bus_color(self, voltage: float, bus_id: str = "") -> str:
        """Return color for a bus based on voltage."""
        if "BT" in bus_id:
            return "#07FF30"  # green triangle
        elif voltage < 0.9 or voltage > 1.1:
            return "#FF0707"  # red warning
        return self.colormap2(min(max(voltage, 0.8), 1.2))
    
    def _draw_line(self, name: str, coords: list, loading: float, popup_values: list = None, group: folium.FeatureGroup = None) -> None:
        """
        Draw a single line (PolyLine) on the map.

        Args:
            name (str): Line ID.
            coords (list): Coordinates [from, to].
            loading (float): Loading %.
            popup_values (list, optional): Hourly values for popup plot.
        """
        color = self._get_line_color(loading)
        popup = self._make_popup_plot(popup_values, ID=name) if popup_values else folium.Popup(
            f"<b>Line {name}</b><br>Loading: {loading:.1f} %", max_width=250)
        folium.PolyLine(
            locations=coords,
            color=color,
            weight=7 if loading > 100 else 4,
            popup=popup,
            **{'className': 'line-polyline'}
        ).add_to(self.m if popup_values else group)

    def _draw_bus(self, name: str, lat: float, lon: float, vpu: float, va_deg: float = None, p_kw: float = None, q_kvar: float = None, popup_values: list = None, group: folium.FeatureGroup = None) -> None:
        """
        Draw a single bus (marker) on the map.

        Args:
            name (str): Bus ID.
            lat (float): Latitude.
            lon (float): Longitude.
            voltage (float): Voltage in p.u.
            popup_values (list, optional): Hourly voltage values for popup plot.
        """
        color = self._get_bus_color(vpu, bus_id=name)
        popup = self._make_popup_plot(popup_values, ID=name, flag="voltage") if popup_values else (
                    f"<b>Bus {name}</b><ul>"
                    f"<li>Voltage : {vpu:.3f} [ p.u. ]</li>"
                    f"<li>Phase shift : {va_deg:.2f} [ ° ]</li>"
                    f"<li>Power : {p_kw:.1f} [ kW ] / {q_kvar:.1f} [ kVar ]</li>"
                    f"</ul>"
                )
        folium.RegularPolygonMarker(
                    location =[float(lat), float(lon)],
                    color = color,
                    fill_color = color,
                    fill = True,
                    fill_opacity = 1,
                    number_of_sides = 3,
                    radius = 6 if vpu < 1 else 8,
                    popup = popup,
                    **{'className': 'bus-marker'}
                ).add_to(self.m if popup_values else group)
        
    def _match_line_and_buses(self, name: str):
        """
        Trouve la ligne et les deux bus correspondants à partir du nom de la ligne.
        """
        match_line = self.line_df[self.line_df["ID"] == name]
        if match_line.empty:
            print(f"Warning: No matching line found for {name}.")
            return None, None, None

        line_row = match_line.iloc[0]
        from_bus = line_row["From_Bus_ID"]
        to_bus = line_row["To_Bus_ID"]

        match_bus_from = self.node_df[self.node_df["ID"] == from_bus]
        match_bus_to = self.node_df[self.node_df["ID"] == to_bus]

        if match_bus_from.empty or match_bus_to.empty:
            print(f"Warning: No matching bus found for line {name}.")
            return None, None

        return match_bus_from.iloc[0], match_bus_to.iloc[0]

    def _add_lines(self, group, net):
        """
        Add power lines to the given group based on loading percent.
        Highlights overloads and adds informative popups.
        """
        df_lines = net.res_line.copy()
        df_lines['name'] = net.line['name'].astype(str)
        df_lines = df_lines[pd.notna(df_lines["loading_percent"])]

        for _, row in df_lines.iterrows():
            name = row["name"]
            loading = row["loading_percent"]
            match_bus_from, match_bus_to = self._match_line_and_buses(name)

            f_lat, f_lon = match_bus_from[["latitude", "longitude"]]
            t_lat, t_lon = match_bus_to[["latitude", "longitude"]]

            self._draw_line(
                name=name,
                coords=[[f_lat, f_lon], [t_lat, t_lon]],
                loading=loading,
                group=group
            )

    def _prepare_coordinates_for_plot(self, net):        
        """
        If power is flowing through the bus, use original coordinates for plotting.
        """
        df_bus = net.res_bus.copy()
        df_bus["name"] = net.bus["name"].astype(str)
        for _, row in df_bus.iterrows():
            name = row["name"]
            p_kw = row["p_mw"] * 1000
            q_kvar = row["q_mvar"] * 1000
            if p_kw != 0 or q_kvar != 0:
                self.node_df.loc[self.node_df["ID"] == name, "latitude"] = self.node_df.loc[self.node_df["ID"] == name, "latitude_original"]
                self.node_df.loc[self.node_df["ID"] == name, "longitude"] = self.node_df.loc[self.node_df["ID"] == name, "longitude_original"]

    def _add_buses(self, group, net, node_with_power: pd.Series):
        """
        Add visible markers for buses with power injections.
        Voltage coloring and shape customization included.
        """
        df_bus = net.res_bus.copy()
        df_bus["name"] = net.bus["name"].astype(str)
        df_bus = df_bus[pd.notna(df_bus["vm_pu"])]

        for _, row in df_bus.iterrows():
            name = row["name"]
            vpu = row["vm_pu"]
            va_deg = row["va_degree"]
            p_kw = row["p_mw"] * 1000
            q_kvar = row["q_mvar"] * 1000
            if row["name"] in node_with_power:
                match = self.node_df[self.node_df["ID"] == name]
                if match.empty:
                    continue
                lat, lon = match.iloc[0][["latitude", "longitude"]]
                self._draw_bus(
                    name=name,
                    lat=lat,
                    lon=lon,
                    vpu=vpu,
                    va_deg=va_deg,
                    p_kw=p_kw,
                    q_kvar=q_kvar,
                    group=group
                )

    def _add_generators(self, group, net):
        """
        Placeholder for generator plotting (to be implemented).
        """
        df_gen = net.res_gen.copy()
        df_gen["Bus_id"] = net.gen["bus"].astype(str)
        df_gen = df_gen[pd.notna(df_gen["p_"])]

    def plot_results(self, net, hour_label: str, node_with_power: pd.Series):
        """
        Create a folium FeatureGroup for a given hour, including buses and lines.
        Updates node coordinates based on load before plotting.
        """
        group = folium.FeatureGroup(name=hour_label, show=False)
        self._prepare_coordinates_for_plot(net)
        self._add_lines(group, net)
        self._add_buses(group, net, node_with_power)
        if not net.gen.empty:
            self._add_generators(group, net)
        return group

    def _make_popup_plot(self, values, ID, flag=None):
        """
        Create a mini static line plot (loading or voltage vs hour) embedded in a folium popup.

        Args:
            values (list or np.array): 24 hourly values.
            ID (str): Identifier for the line or bus.
            flag (str): 'voltage' or None for y-axis labeling and coloring.

        Returns:
            folium.Popup: A popup object with embedded image.
        """
        fig, ax = plt.subplots(figsize=(4, 2))
        ax.step(range(24), values, where="post")
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xlabel("Hour")
        ax.set_ylabel("Voltage [p.u.]") if flag == "voltage" else ax.set_ylabel("Loading [%]")
        ax.set_title(f"Bus {ID}" if flag == "voltage" else f"Line {ID}")
        ax.grid(True)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        html = f'<img src="data:image/png;base64,{encoded}" width="300" style="background: rgba(255, 255, 255, 0.95);" />'
        return folium.Popup(html, max_width=310)

    def plot_static_results(self, line_df, node_df, max_loading, max_voltage,
                            loading_series, voltage_series):
        """
        Create a static map with pre-aggregated max loading and voltage per element.

        Args:
            line_df (DataFrame): Line coordinates.
            node_df (DataFrame): Node coordinates.
            max_loading (dict): Max loading per line.
            max_voltage (dict): Max voltage per node.
            loading_series (dict): Hourly loading series per line.
            voltage_series (dict): Hourly voltage series per node.
        """
        max_loading = {k: v for k, v in max_loading.items() if pd.notna(v)}
        loading_series = {k: v for k, v in loading_series.items() if pd.notna(v).all()}

        max_voltage = {k: v for k, v in max_voltage.items() if pd.notna(v)}
        voltage_series = {k: v for k, v in voltage_series.items() if pd.notna(v).all()}

        for _, row in line_df.iterrows():
            name = str(row["ID"])
            match_bus_from, match_bus_to = self._match_line_and_buses(name)
            f_lat, f_lon = match_bus_from[["latitude", "longitude"]]
            t_lat, t_lon = match_bus_to[["latitude", "longitude"]]
            coords = [[f_lat, f_lon], [t_lat, t_lon]]

            loading = max_loading.get(name, None)
            if loading is None:
                continue
            self._draw_line(name, coords, loading, popup_values=loading_series.get(name))

        for _, row in node_df.iterrows():
            if row["ID"] not in max_voltage:
                continue
            name = str(row["ID"])
            lat, lon = row["latitude"], row["longitude"]
            value = max_voltage.get(name, None)
            if value is None:
                continue
            self._draw_bus(name, lat, lon, value, popup_values=voltage_series.get(name))

    def add_control(self):
        """
        Add the interactive layer control panel to the top-left of the map.
        Allows toggling layers on/off.
        """
        folium.LayerControl(collapsed=True, draggable=True, position="topleft").add_to(self.m)

    def save_map(self, name: str) -> None:
        """
        Save the map to the ../result/ directory as an HTML file.
        """
        if ".html" in name:
            self.m.save(name)
        else:
            self.m.save(f"../result/{name}.html")
            print(f"Carte enregistrée dans {name}.html")

    def save_map_anonymous(self, name: str) -> None:
        """
        Save the anonymized map under a prefixed name.
        """
        self.m.save(f"../result/Anonymous_{name}.html")
        print(f"Carte enregistrée dans Anonymous_{name}.html")