import pandas as pd
import ast

class DataPrepare:
    def __init__(self, xls):
        self.xls = xls
        self.load_df = pd.DataFrame(columns=["ID", "PLmax(kW)", "QLmax(kVar)", "Pg(kW)", "XY", "latitude", "longitude"])
        self.node_df = pd.DataFrame(columns=["ID", "XY", "latitude", "longitude"])
        self.line_df = pd.DataFrame(columns=["ID", "From_XY", "From_latitude", "From_longitude", "To_XY", "To_latitude", "To_longitude"])

    def split_xy(self, xy):
        if isinstance(xy, str):
            try:
                xy = ast.literal_eval(xy)
            except (ValueError, SyntaxError, TypeError):
                return None, None

        if isinstance(xy, tuple) and len(xy) == 2:
            try:
                return float(xy[0]), float(xy[1])
            except (ValueError, TypeError):
                return None, None
        return None, None

    def make_load_df(self):
        load_data = []
        for _, row in self.xls.iterrows():
            if row["PLmax(kW)"] != 0 or row["Pg(kW)"] != 0 or row["QLmax(kVar)"] != 0:
                xy = row.get("To_XY")
                lat, lon = self.split_xy(xy)

                load_data.append({
                    "ID": row["To"],
                    "PLmax(kW)": row["PLmax(kW)"],
                    "QLmax(kVar)": row["QLmax(kVar)"],
                    "Pg(kW)": row["Pg(kW)"],
                    "XY": xy,
                    "latitude": lat,
                    "longitude": lon
                })

        self.load_df = pd.DataFrame(load_data)
        return self.load_df

    def make_node_df(self):
        seen = set()
        node_data = []

        for _, row in self.xls.iterrows():
            for direction in ["From", "To"]:
                node_id = row[direction]
                if node_id not in seen:
                    seen.add(node_id)
                    xy = row.get(f"{direction}_XY")
                    lat, lon = self.split_xy(xy)

                    node_data.append({
                        "ID": node_id,
                        "XY": xy,
                        "latitude": lat,
                        "longitude": lon
                    })

        self.node_df = pd.DataFrame(node_data)
        return self.node_df

    def make_line_df(self):
        line_data = []

        for _, row in self.xls.iterrows():
            name = row["Line"]

            from_xy = row.get("From_XY")
            from_lat, from_lon = self.split_xy(from_xy)

            to_xy = row.get("To_XY")
            to_lat, to_lon = self.split_xy(to_xy)

            line_data.append({
                "ID": name,
                "From_XY": from_xy,
                "From_latitude": from_lat,
                "From_longitude": from_lon,
                "To_XY": to_xy,
                "To_latitude": to_lat,
                "To_longitude": to_lon
            })

        self.line_df = pd.DataFrame(line_data)
        return self.line_df
