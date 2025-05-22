import folium
import branca
import pandas as pd
import seaborn as sns
import matplotlib.colors as mcolors
from folium import Element

class PlotOnMapFolium:
    def __init__(self, node_df, load_df, line_df, lat0, lon0):
        self.node_df = node_df     # Coordonnées géographiques des nœuds
        self.load_df = load_df     # Données de charge (non utilisées ici)
        self.line_df = line_df     # Coordonnées géo des lignes
        self.lat0 = lat0           # Latitude de centrage
        self.lon0 = lon0           # Longitude de centrage

    def create_map(self):
        # Création de la carte de base avec fond sombre CartoDB
        self.m = folium.Map(
            location=[self.lat0, self.lon0],
            zoom_start=18,
            tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attr="© CartoDB",
            name="CartoDB Dark Matter",
            max_zoom=20
        )

        # Ajout d'une couche satellite Swisstopo (en overlay désactivé par défaut)
        folium.TileLayer(
            tiles="https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg",
            attr="© swisstopo",
            name="Swisstopo Swissimage (Ortho)",
            overlay=True,
            control=False,
            max_zoom=20,
            opacity=0.4
        ).add_to(self.m)

        # Palette seaborn pour les charges (dégradé rocket)
        colors_charges = [mcolors.to_hex(c) for c in sns.color_palette("rocket_r", n_colors=5)]

        # Colormap des charges
        self.colormap = branca.colormap.LinearColormap(
            colors=colors_charges,
            index=[0, 25, 50, 75, 100],
            vmin=0,
            vmax=100,
            caption='Charge de ligne [%]'
        )
        self.colormap.caption_style = {'font-size': '14px', 'font-weight': 'bold'}
        self.colormap.style = {
            'background-color': 'rgba(255, 255, 255, 0.85)',
            'padding': '6px',
            'border-radius': '6px',
            'box-shadow': '2px 2px 5px rgba(0, 0, 0, 0.3)'
        }
        self.colormap.add_to(self.m)

        # Palette seaborn pour la tension (bleu clair → bleu saturé)
        colors_tension = [mcolors.to_hex(c) for c in sns.color_palette("light:blue", n_colors=2)]

        # Colormap des tensions
        self.colormap2 = branca.colormap.LinearColormap(
            colors=colors_tension,
            vmin=0.8,
            vmax=1,
            caption='Valeure de tension p.u.'
        )
        self.colormap2.caption_style = {'font-size': '14px', 'font-weight': 'bold'}
        self.colormap2.style = {
            'background-color': 'rgba(255, 255, 255, 0.85)',
            'padding': '6px',
            'border-radius': '6px',
            'box-shadow': '2px 2px 5px rgba(0, 0, 0, 0.3)'
        }
        self.colormap2.add_to(self.m)

        # CSS pour style global des légendes + ajustement z-index
        overlay_css = """
            <style>
            .leaflet-tile-pane::before {
                content: "";
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0, 0, 0, 0.65);
                z-index: 1;
                pointer-events: none;
            }

            .legend {
                position: relative !important;
                display: block !important;
                margin-bottom: 12px;
                padding: 8px 12px;
                background: rgba(255, 255, 255, 0.5);
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
            </style>
            """
        self.m.get_root().html.add_child(Element(overlay_css))
        slider_html = """
            <div id="hour-slider-container" style="
                position: fixed;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                background-color: rgba(255, 255, 255, 0.5);
                padding: 5px 10px;
                border-radius: 10px;
                z-index: 9999;
                font-family: sans-serif;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);
            ">
                <label for="hourSlider"><strong>Heure :</strong> <span id="hourLabel">00:00</span></label><br>
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

    def plot_results(self, net, hour_label):

        group = folium.FeatureGroup(name=f"{hour_label}", show=False)

        # Chargement des résultats de ligne et nettoyage
        df_lines = net.res_line.copy()
        df_lines['name'] = net.line['name'].astype(str)
        df_lines = df_lines[pd.notna(df_lines["loading_percent"])]

        # Chargement des résultats de tension aux bus
        df_bus = net.res_bus.copy()
        df_bus["name"] = net.bus["name"].astype(str)
        df_bus = df_bus[pd.notna(df_bus["vm_pu"])]

        # Conversion des IDs en string pour jointure
        self.line_df["ID"] = self.line_df["ID"].astype(str)
        self.node_df["ID"] = self.node_df["ID"].astype(str)

        # Affichage des lignes avec chargement coloré
        for _, row in df_lines.iterrows():
            name = row["name"]
            loading = row["loading_percent"]
            color = self.colormap(min(max(loading, 0), 100))
            match = self.line_df[self.line_df["ID"] == name]
            if match.empty:
                continue

            f_lat = match.iloc[0]["From_latitude"]
            f_lon = match.iloc[0]["From_longitude"]
            t_lat = match.iloc[0]["To_latitude"]
            t_lon = match.iloc[0]["To_longitude"]

            folium.PolyLine(
                locations=[[f_lat, f_lon], [t_lat, t_lon]],
                color=color,
                weight=4,
                popup=f"Line {name}: {loading:.1f} %"
            ).add_to(group)

        # Affichage des bus avec code couleur selon la tension
        for _, row in df_bus.iterrows():
            name = row["name"]
            self.node_df["ID"] = self.node_df["ID"].astype(str)
            vpu = row["vm_pu"]
            va_deg = row["va_degree"]
            color = self.colormap2(min(max(vpu, 0), 1))
            match = self.node_df[self.node_df["ID"] == name]
            if match.empty:
                continue

            lat = match.iloc[0]["latitude"]
            lon = match.iloc[0]["longitude"]

            folium.CircleMarker(
                location=[lat, lon],
                radius=6,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=f"Bus {name}: {vpu:.3f} p.u., {va_deg:.1f}°"
            ).add_to(group)
        return group
        
    def add_control(self):
        folium.LayerControl(collapsed=True).add_to(self.m)

    def save_map(self, name):
        # Sauvegarde HTML de la carte
        self.m.save(f"{name}.html")
        print(f"Carte enregistrée dans {name}.html")
