import pandas as pd
import ast
from pyproj import Geod
from dataclasses import dataclass
from typing import Dict, Any
from daily_profile_generator import DailyLoadProfileGenerator

@dataclass
class DataPrepare:
    xls: pd.DataFrame
    columns: Dict[str, str]
    stochastic: bool = True

    def _split_xy(self, xy: Any) -> tuple[float | None, float | None]:
        """
        Safely parse coordinate tuple from string or tuple.
        Returns (lat, lon) as floats or (None, None) if invalid.
        """
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

    def _get_latlon(self, row: pd.Series, col_name: str) -> tuple[float | None, float | None]:
        """Extracts and parses coordinate (lat, lon) from a row column."""
        xy = row.get(col_name)
        return self._split_xy(xy)

    def _check_required_columns(self, *required: str) -> None:
        """Ensure all required columns exist in the DataFrame."""
        missing = [col for col in required if col not in self.xls.columns]
        if missing:
            raise ValueError(f"Missing columns in Excel: {missing}")

    def make_load_df(self, df_stats: pd.DataFrame=None) -> pd.DataFrame:
        """
        Create a DataFrame of loads from the Excel input.
        Filters rows where any of PLmax, QLmax, or Pg are non-zero.
        """
        self._check_required_columns(
            self.columns["plmax"], self.columns["qlmax"], self.columns["pg"],
            self.columns["to"]
        )
        load_data = []
        for _, row in self.xls.iterrows():
            if row[self.columns["plmax"]] != 0 or row[self.columns["pg"]] != 0 or row[self.columns["qlmax"]] != 0:
                load_data.append({
                    "Bus_ID": row[self.columns["to"]],
                    "PLmax(kW)": row[self.columns["plmax"]],
                    "QLmax(kVar)": row[self.columns["qlmax"]],
                    "Pg(kW)": row[self.columns["pg"]]
                })
        df = pd.DataFrame(load_data)
        df["Bus_ID"] = df["Bus_ID"].astype(str)
      
        gen = DailyLoadProfileGenerator(df=df, df_stats=df_stats, stochastic=self.stochastic)
        load = {}
        load["active_profile_df"] = gen.active_profile_df
        load["reactive_profile_df"] = gen.reactive_profile_df
        load["pv_profile_df"] = gen.pv_profile_df
        load["load_df"] = df
        node_with_power = []
        node_with_power = []
        for _, x in load.items():
            node_with_power.extend(x["Bus_ID"].tolist())
        node_with_power_unique = pd.Series(node_with_power).unique()

        return(load,node_with_power_unique)

    def _extract_unique_nodes(self, add_direction: bool = False) -> pd.DataFrame:
        """
        Extract unique node entries from both 'from' and 'to' directions.
        Includes coordinate parsing and optional direction tagging.
        """
        seen = set()
        node_data = []
        for _, row in self.xls.iterrows():
            for direction_key, node_col, xy_col in [
                ("from", self.columns["from"], self.columns["from_xy"]),
                ("to", self.columns["to"], self.columns["to_xy"])
            ]:
                node_id = row[node_col]
                if node_id not in seen:
                    seen.add(node_id)
                    lat, lon = self._get_latlon(row, xy_col)
                    node_entry = {
                        "ID": node_id,
                        "XY": row.get(xy_col),
                        "latitude": lat,
                        "longitude": lon
                    }
                    if add_direction:
                        node_entry["direction"] = direction_key
                    node_data.append(node_entry)
        node_df = pd.DataFrame(node_data)
        node_df["ID"] = node_df["ID"].astype(str)
        return node_df

    def _correct_bt_proximity(self, node_df: pd.DataFrame) -> pd.DataFrame:
        """
        Adjust coordinates of nodes that are within 7 meters of a 'BT' node.
        Used to fix GPS noise by snapping close nodes to the same BT reference.
        """
        node_df["latitude_original"] = node_df["latitude"]
        node_df["longitude_original"] = node_df["longitude"]

        bt_nodes = node_df[node_df["ID"].str.contains("BT", case=False, na=False)]
        geod = Geod(ellps="WGS84")

        for idx, row in node_df.iterrows():
            if pd.isna(row["latitude"]) or pd.isna(row["longitude"]):
                continue
            for _, bt_row in bt_nodes.iterrows():
                az12, az21, dist = geod.inv(
                    row["longitude"], row["latitude"],
                    bt_row["longitude"], bt_row["latitude"]
                )
                if dist < 7.0:
                    node_df.at[idx, "latitude"] = bt_row["latitude"]
                    node_df.at[idx, "longitude"] = bt_row["longitude"]
                    node_df.at[idx, "XY"] = (bt_row["latitude"], bt_row["longitude"])
                    break
        return node_df

    def make_node_df(self, add_direction: bool = False, proximity: bool = True) -> pd.DataFrame:
        """
        Create node DataFrame with coordinates and optional direction tag.
        Also applies correction for GPS jitter near BT nodes.
        """
        self._check_required_columns(
            self.columns["from"], self.columns["to"],
            self.columns["from_xy"], self.columns["to_xy"]
        )
        node_df = self._extract_unique_nodes(add_direction=add_direction)
        node_df = self._correct_bt_proximity(node_df) if proximity else node_df
        return node_df

    def make_line_df(self) -> pd.DataFrame:
        """
        Create a line DataFrame from the Excel input.
        Includes 'ID', 'From_Bus_ID', and 'To_Bus_ID' fields.
        """
        self._check_required_columns(
            self.columns["line"], self.columns["from"], self.columns["to"],
            self.columns["from_xy"], self.columns["to_xy"]
        )
        line_data = []
        for _, row in self.xls.iterrows():
            line_data.append({
                "ID": row[self.columns["line"]],
                "From_Bus_ID": row[self.columns["from"]],
                "To_Bus_ID": row[self.columns["to"]],
            })
        df = pd.DataFrame(line_data)
        df["ID"] = df["ID"].astype(str)
        df["From_Bus_ID"] = df["From_Bus_ID"].astype(str)
        df["To_Bus_ID"] = df["To_Bus_ID"].astype(str)
        return df

    def prepare_all(self, df_stats) -> Dict[str, pd.DataFrame]:
        """
        Prepare all data components: load_df, node_df, and line_df.
        Useful as a one-shot full preprocessing pipeline.
        """
        return {
            "load_df": self.make_load_df(df_stats=df_stats),
            "node_df": self.make_node_df(),
            "line_df": self.make_line_df()
        }
