from power_flow_viz import PowerFlowViz
import pandas as pd

# 1. Définitions de base
Sb = 1e6   # [VA]
Vb = 400     # [V]
f  = 50      # [Hz]
name = "save name"# + str(datetime.today())

# 2. Chargement de l'Excel
fichier_excel = "xls files"
xls = pd.read_excel(fichier_excel, sheet_name="sheet name")

# 3. Exécution de l'outil
visualization = PowerFlowViz(xls, Sb, Vb, f, name, stochastic=True)
visualization.generate_static_summary_map(save=True, anonymous=True)
visualization.generate_time_slider_map( hour_start=0, hour_end=24, save=True, anonymous=True)
# visualization.export_net()