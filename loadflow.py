import numpy as np
import pandapower as pp
import pandapower.plotting.plotly as plotly
import pandas as pd

class loadflow:
    def __init__(self,xls,Sb,Vb,f,name,P_df,Q_df,node_df):
        self.xls = xls
        self.Sb = Sb
        self.Vb = Vb
        self.f = f
        self.name = name
        self.P_df = P_df
        self.Q_df = Q_df
        self.node_df = node_df


    def create_net_empty(self):
        net = pp.create_empty_network(sn_mva=self.Sb / 1e6, name=self.name)
        self.buses = {}

        for _, row in self.node_df.iterrows():
            bus_id = str(row["ID"])
            self.buses[bus_id] = pp.create_bus(net, vn_kv=self.Vb / 1000, name=bus_id)

        # Ext grid
        first_id = str(self.node_df.iloc[0]["ID"])
        pp.create_ext_grid(net, bus=self.buses[first_id], vm_pu=1.0, name=first_id)

        # Lignes
        for _, row in self.xls.iterrows():
            from_bus = str(row["From"])
            to_bus = str(row["To"])
            length = float(row["Length(m)"])
            params_r1 = float(row["R(Ohm/km)"])
            params_x1 = float(row["X(Ohm/km)"])
            max_i = float(row["Ampacity (A)"])
            name_l = str(row["Line"])
            if length ==0 or params_r1==0 or params_x1 ==0:
                pass
            else:
                pp.create_line_from_parameters(
                    net,
                    from_bus=self.buses[from_bus],
                    to_bus=self.buses[to_bus],
                    length_km=length/1000,
                    r_ohm_per_km=params_r1,
                    x_ohm_per_km=params_x1,
                    c_nf_per_km=0,
                    max_i_ka=max_i / 1000,
                    name=name_l,
                )
        return net

    def set_hourly_loads(self, net, hour):

        # Supprimer les anciennes charges
        net.load.drop(net.load.index, inplace=True)

        # Ajouter charges actives
        for _, row in self.P_df.iterrows():
            node_id = str(row["ID"])
            if node_id not in self.buses:
                continue
            pp.create_load(net, bus=self.buses[node_id], p_mw=row[hour] / 1000, q_mvar=0)

        # Ajouter charges réactives
        for _, row in self.Q_df.iterrows():
            node_id = str(row["ID"])
            if node_id not in self.buses:
                continue
            pp.create_load(net, bus=self.buses[node_id], p_mw=0, q_mvar=row[hour] / 1000)


    def exec(self,net):
        # 8. Calculer le flux de charge
        pp.runpp(net)
        """ 
        # 9. Afficher les résultats
        print("\nRésultats de tension par bus :")
        print(net.res_bus[["vm_pu", "va_degree"]])

        print("\nRésultats de ligne :")
        print(net.res_line[["p_from_mw", "q_from_mvar", "loading_percent"]])
                # 10. Afficher les résultats de la charge
        try:
            fig = plotly.simple_plotly(net)

            fig.show()

        except Exception as e:
            print("Erreur d'affichage graphique :", e) """

