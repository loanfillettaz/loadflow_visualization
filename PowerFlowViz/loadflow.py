import pandas as pd
import pandapower as pp
from typing import Dict
from dataclasses import dataclass, field

@dataclass
class LoadFlow:
    xls: pd.DataFrame
    Sb: float  # Base apparent power in VA
    Vb: float  # Base voltage in V
    f: float   # Grid frequency in Hz
    name: str  # Network name
    node_df: pd.DataFrame  # DataFrame with at least column 'ID'
    columns: Dict[str, str]  # Mapping of column names used in xls

    buses: Dict[str, int] = field(default_factory=dict)

    def _create_buses(self, net: pp.pandapowerNet) -> None:
        """
        Create buses in the pandapower network based on node_df.
        Each bus is created at the specified base voltage (Vb), converted to kV.
        Adds an external grid on the first created bus.
        """
        for bus_id in self.node_df["ID"].astype(str):
            self.buses[bus_id] = pp.create_bus(net, vn_kv=self.Vb / 1000, name=bus_id)
        if self.buses:
            first_bus = next(iter(self.buses.values()))
            pp.create_ext_grid(net, bus=first_bus, vm_pu=1.0, name="Grid")

    def _create_lines(self, net: pp.pandapowerNet) -> None:
        """
        Create lines in the pandapower network based on the xls DataFrame.
        Required columns: from, to, r (ohm/km), x (ohm/km), length (m), ampacity (A), line name.
        Lines with missing r, x, or length are skipped.
        """
        for _, row in self.xls.iterrows():
            fb = str(row[self.columns["from"]])
            tb = str(row[self.columns["to"]])
            r = float(row[self.columns["r"]])
            x = float(row[self.columns["x"]])
            length = float(row[self.columns["length"]])
            max_i = float(row[self.columns["ampacity"]])
            name_l = str(row[self.columns["line"]])
            if not (r and x and length):
                continue
            pp.create_line_from_parameters(
                net,
                from_bus=self.buses[fb],
                to_bus=self.buses[tb],
                length_km=length / 1000,
                r_ohm_per_km=r,
                x_ohm_per_km=x,
                c_nf_per_km=0,
                max_i_ka=max_i / 1000,
                name=name_l
            )

    def create_net_empty(self) -> pp.pandapowerNet:
        """
        Build and return an empty pandapower network with buses, external grid, and lines.
        """
        net = pp.create_empty_network(sn_mva=self.Sb / 1e6, name=self.name)
        self._create_buses(net)
        self._create_lines(net)
        return net

    def _clear_loads(self, net: pp.pandapowerNet) -> None:
        """Remove all existing loads from the network."""
        net.load.drop(index=net.load.index, inplace=True)

    def _clear_generators(self, net: pp.pandapowerNet) -> None:
        """Remove all existing generators from the network."""
        net.gen.drop(index=net.gen.index, inplace=True)

    def _create_loads(self, net: pp.pandapowerNet, loads: pd.DataFrame) -> None:
        """
        Add loads from a DataFrame with columns ['bus', 'p_mw', 'q_mvar'].
        Rows with unknown buses are skipped.
        """
        for _, row in loads.iterrows():
            bus_key = str(row['bus'])
            if bus_key not in self.buses:
                continue
            pp.create_load(
                net,
                bus=self.buses[bus_key],
                p_mw=row['p_mw'],
                q_mvar=row['q_mvar']
            )

    def _create_generators(self, net: pp.pandapowerNet, generation: pd.DataFrame) -> None:
        """
        Add generators to the network from a DataFrame with columns
        ['bus', 'p_mw', 'vm_pu', 'scaling_factor', 'in_service', 'ID'].
        Negative p_mw indicates production.
        """
        self._clear_generators(net)
        for _, row in generation.iterrows():
            bus_key = str(row['bus'])
            if bus_key not in self.buses:
                continue
            pp.create_gen(
                net,
                bus=self.buses[bus_key],
                p_mw=-row['p_mw'],
                vm_pu=row['vm_pu'],
                scaling=row['scaling_factor'],
                in_service=row['in_service'],
                name=row['ID']
            )

    def set_hourly_loads(self, net: pp.pandapowerNet, hour: str, P_df: pd.DataFrame, Q_df: pd.DataFrame, PV_df: pd.DataFrame) -> None:
        """
        Set network loads based on profile DataFrames for a specific hour.
        Inputs: P_df, Q_df, PV_df with ['Bus_ID', hour] columns.
        PV generation is treated as negative load.
        """
        self._clear_loads(net)
        active = P_df[['Bus_ID', hour]].rename(columns={hour: 'p_kw'})
        active['q_kvar'] = 0
        active['sign'] = 1

        reactive = Q_df[['Bus_ID', hour]].rename(columns={hour: 'q_kvar'})
        reactive['p_kw'] = 0
        reactive['sign'] = 1

        prod = PV_df[['Bus_ID', hour]].rename(columns={hour: 'p_kw'})
        prod['q_kvar'] = 0
        prod['sign'] = -1

        df = pd.concat([active, reactive, prod], ignore_index=True)
        df['p_mw'] = df['p_kw'] * df['sign'] / 1000
        df['q_mvar'] = df['q_kvar'] / 1000
        df = df.rename(columns={'Bus_ID': 'bus'})
        self._create_loads(net, df[['bus', 'p_mw', 'q_mvar']])

    def set_loads_mw(self, net: pp.pandapowerNet, loads: pd.DataFrame) -> None:
        """
        Set loads from a DataFrame with columns ['Bus_ID', 'active_power_mw', 'reactive_power_mvar'].
        """
        self._clear_loads(net)
        df = loads.rename(columns={
            'Bus_ID': 'bus',
            'active_power_mw': 'p_mw',
            'reactive_power_mvar': 'q_mvar'
        })
        self._create_loads(net, df[['bus', 'p_mw', 'q_mvar']])

    def set_generation_mw(self, net: pp.pandapowerNet, production: pd.DataFrame) -> None:
        """
        Set generator production from a DataFrame with columns:
        ['Bus_ID', 'active_power_mw', 'voltage_pu', 'scaling', 'in_service', 'name'].
        """
        df = production.rename(columns={
            'Bus_ID': 'bus',
            'active_power_mw': 'p_mw',
            'scaling': 'scaling_factor',
            'voltage_pu': 'vm_pu',
            'in_service': 'in_service',
            'name': 'ID'
        })
        self._create_generators(net, df[['bus', 'p_mw', 'vm_pu', 'scaling_factor', 'in_service', 'ID']])

    def run(self, net: pp.pandapowerNet) -> None:
        """
        Execute the power flow calculation using the default Newton-Raphson method.
        """
        pp.runpp(net)
