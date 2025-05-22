import numpy as np
import pandas as pd

class DailyLoadProfileGenerator:
    def __init__(self, df, profile_type='residential_weekday', add_noise=False, noise_level=0.05):
        self.df = df
        self.profile_type = profile_type
        self.add_noise = add_noise
        self.noise_level = noise_level
        self.hours = [f"{h:02d}:00" for h in range(24)]
        self.profile = self._select_profile()
        self.active_profile_df = self._generate_profile_df("PLmax(kW)")
        self.reactive_profile_df = self._generate_profile_df("QLmax(kVar)")

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
        base = self.df[["ID", power_col, "latitude", "longitude"]].copy()
        for i, hour in enumerate(self.hours):
            hour_profile = self.profile[i]
            if self.add_noise:
                noise = np.random.normal(loc=1.0, scale=self.noise_level, size=len(base))
                hour_profile = np.clip(hour_profile * noise, 0, 1)
            base[hour] = base[power_col] * hour_profile
            base["ID"] = base["ID"].astype(int).astype(str)
        return base[["ID"] + self.hours + ["latitude", "longitude"]]
