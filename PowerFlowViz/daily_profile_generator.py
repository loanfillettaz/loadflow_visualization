import numpy as np
import pandas as pd

class DailyLoadProfileGenerator:
    def __init__(self, df, df_stats, pv_profile_type="summer", profile_type='residential_weekday', 
                add_noise=False, noise_level=0.1, stochastic=False, seed=0):
        self.df = df
        self.df_stats = df_stats
        self.profile_type = profile_type
        self.pv_profile_type = pv_profile_type
        self.add_noise = add_noise
        self.noise_level = noise_level
        self.stochastic = stochastic
        self.seed = seed
        self.hours = [f"{h:02d}:00" for h in range(24)]
        self.profile = self._select_profile() if not stochastic else None
        self.pv_profile = self._select_pv_profile()
        self.active_profile_df = self._generate_profile_df("PLmax(kW)")
        if not stochastic:
            self.reactive_profile_df = self._generate_profile_df("QLmax(kVar)")
        else:
            df_copy = self.active_profile_df.copy()
            cols = [col for col in df_copy.columns if col != "Bus_ID"]
            df_copy[cols] = df_copy[cols] * 0.3
            self.reactive_profile_df = df_copy        
        self.pv_profile_df = self._generate_pv_profile_df()

    def _select_profile(self):
        # Profils réalistes (normalisés à 1)
        profiles = {
            "residential_weekday": [
                0.25, 0.2, 0.15, 0.12, 0.15, 0.4, 0.6, 0.8,
                0.6, 0.4, 0.35, 0.3, 0.3, 0.4, 0.5, 0.6,
                0.8, 1.0, 0.9, 0.7, 0.5, 0.4, 0.35, 0.3
            ],
            "residential_weekend": [
                0.35, 0.3, 0.25, 0.2, 0.25, 0.4, 0.6, 0.8,
                0.9, 1.0, 0.95, 0.85, 0.75, 0.8, 0.9, 0.95,
                1.0, 0.95, 0.85, 0.7, 0.5, 0.4, 0.35, 0.3
            ],
            "office": [
                0.0, 0.0, 0.0, 0.0, 0.05, 0.2, 0.5, 0.7,
                0.9, 1.0, 1.0, 0.95, 0.95, 0.9, 0.8, 0.6,
                0.4, 0.2, 0.1, 0.05, 0.0, 0.0, 0.0, 0.0
            ],
            "industry": [
                0.1, 0.1, 0.1, 0.1, 0.2, 0.4, 0.6, 0.8,
                1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
                1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.1, 0.1
            ],
            "hospital": [
                0.7, 0.7, 0.7, 0.7, 0.75, 0.8, 0.85, 0.9,
                0.95, 1.0, 1.0, 0.95, 0.95, 0.9, 0.9, 0.9,
                0.9, 0.95, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7
            ]
        }

        if self.profile_type not in profiles:
            raise ValueError(f"Profil inconnu : {self.profile_type}")

        return np.array(profiles[self.profile_type])

    def _generate_profile_df(self, power_col):
        base = self.df[["Bus_ID", power_col]].copy()
        np.random.seed(self.seed)

        if self.stochastic:
            np.random.seed(self.seed)
            quantile_probs = np.array([0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95])
            hours_ref = self.df_stats["hour"].tolist()
            n_profiles = len(base)

            # Tirages aléatoires uniformes
            U = np.random.uniform(0.0, 1.0, size=(n_profiles, len(hours_ref)))

            # Génération profils
            base_hours = pd.DataFrame(0.0, index=range(n_profiles), columns=hours_ref)

            for j, h in enumerate(hours_ref):
                row = self.df_stats[self.df_stats["hour"] == h].iloc[0]
                q_vals = row[["Q5","Q10","Q25","Q50","Q75","Q90","Q95"]].to_numpy(dtype=float)
                for i in range(n_profiles):
                    value = np.interp(U[i, j], quantile_probs, q_vals)
                    base_hours.at[i, h] = np.clip(value, 0, None)

            # Copier dans base[h]
            for h in hours_ref:
                base[h] = base_hours[h]

        else:
            for i, h in enumerate(self.hours):
                hour_profile = self.profile[i]
                if self.add_noise:
                    noise = np.random.normal(loc=1.0, scale=self.noise_level, size=len(base))
                    hour_profile = np.clip(hour_profile * noise, 0, 1)
                base[h] = base[power_col] * hour_profile

        base["Bus_ID"] = base["Bus_ID"].astype(int).astype(str)
        return base[["Bus_ID"] + self.hours]
    
    def _select_pv_profile(self):
        pv_profile = {
            "summer": [
                0.00, 0.00, 0.00, 0.00, 0.01, 0.05, 0.15, 0.35,
                0.60, 0.80, 0.95, 1.00, 0.98, 0.90, 0.75, 0.55,
                0.35, 0.15, 0.05, 0.01, 0.00, 0.00, 0.00, 0.00
            ],
            "winter": [round(v * 0.35, 4) for v in [
                0.00, 0.00, 0.00, 0.00, 0.01, 0.05, 0.15, 0.35,
                0.60, 0.80, 0.95, 1.00, 0.98, 0.90, 0.75, 0.55,
                0.35, 0.15, 0.05, 0.01, 0.00, 0.00, 0.00, 0.00
            ]],
            "night": [0.0] * 24
        }

        if self.pv_profile_type not in pv_profile:
            raise ValueError(f"Profil inconnu : {self.pv_profile_type}")

        return np.array(pv_profile[self.pv_profile_type])
        

    def _generate_pv_profile_df(self):

        base = self.df[["Bus_ID", "Pg(kW)"]].copy()
        for i, hour in enumerate(self.hours):
            hour_profile = self.pv_profile[i]
            if self.add_noise:
                noise = np.random.normal(loc=1.0, scale=self.noise_level, size=len(base))
                hour_profile = np.clip(hour_profile * noise, 0, 1)
            base[hour] = base["Pg(kW)"] * hour_profile
        base["Bus_ID"] = base["Bus_ID"].astype(int).astype(str)
        return base[["Bus_ID"] + self.hours ]