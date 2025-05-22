# main.py
from loadflow import loadflow
from data_prepare import DataPrepare
import pandas as pd
from datetime import datetime
from plot_on_map_folium import PlotOnMapFolium
from daily_profile_generator import DailyLoadProfileGenerator
import folium 


# 1. Définitions de base
Sb = 1e6   # [VA]
Vb = 400     # [V]
f  = 50      # [Hz]
name = "OIKEN_2025_92423_MT_BT_92423"# + str(datetime.today())

# 2. Chargement de l'Excel
fichier_excel = "Copie de Research_OIKEN_XY_2025_92423.xlsx"
xls = pd.read_excel(fichier_excel, sheet_name="MT_BT_92423")

# 3. Préparation des données
prep = DataPrepare(xls)
load_df = prep.make_load_df()
node_df = prep.make_node_df()
line_df = prep.make_line_df()

# 4. Création des matrices P et Q de profil journalier
dpgenerator = DailyLoadProfileGenerator(load_df)
P_df = dpgenerator.active_profile_df
Q_df = dpgenerator.reactive_profile_df

# 5. Création du net
netbuilder = loadflow(xls, Sb, Vb, f, name, P_df, Q_df, node_df)
net = netbuilder.create_net_empty()

# 6. Création de la carte 

lat0 = node_df.iloc[0]["latitude"]
lon0 = node_df.iloc[0]["longitude"]
map = PlotOnMapFolium(node_df,load_df,line_df,lat0,lon0)
map.create_map()

today = datetime.today().strftime("%Y-%m-%d")
# 5. Création et exécution du réseau
for i in range(24):
    hour_str = f"{i:02d}:00"
    timestamp = f"{today}T{hour_str}"
    netbuilder.set_hourly_loads(net,hour_str)
    netbuilder.exec(net)
    layer = map.plot_results(net,hour_str)
    layer.add_to(map.m)

map.add_control()

map.save_map(name)
