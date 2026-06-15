import json
from pathlib import Path

PREFS_FILE = "photopicker_prefs.json"


class PreferenceTracker:
    def __init__(self, folder: str):
        self.folder = folder
        self.prefs_path = Path(folder) / ".photopicker_cache" / PREFS_FILE
        self.data = self._load()

    def _load(self) -> dict:
        if self.prefs_path.exists():
            try:
                return json.loads(self.prefs_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "decisions": 0,
            "pref_brightness": 0.0,
            "pref_sharpness": 0.0,
            "pref_contrast": 0.0,
            "pref_saturation": 0.0,
        }

    def _save(self):
        self.prefs_path.parent.mkdir(parents=True, exist_ok=True)
        self.prefs_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def record_choice(self, winner_stats: dict, loser_stats: dict):
        """Record a PK choice to update preferences."""
        self.data["decisions"] += 1

        for key in ["brightness", "sharpness", "contrast", "saturation"]:
            w = winner_stats.get(key, 0)
            l = loser_stats.get(key, 0)
            if w > l:
                self.data[f"pref_{key}"] += 1
            elif w < l:
                self.data[f"pref_{key}"] -= 1

        self._save()

    def get_weights(self) -> dict:
        """Get preference weights for ranking."""
        if self.data["decisions"] < 3:
            return {}
        d = self.data["decisions"]
        return {
            "brightness": self.data["pref_brightness"] / d,
            "sharpness": self.data["pref_sharpness"] / d,
            "contrast": self.data["pref_contrast"] / d,
            "saturation": self.data["pref_saturation"] / d,
        }

    def adjust_score(self, base_score: int, stats: dict) -> int:
        """Adjust aesthetic score based on learned preferences."""
        weights = self.get_weights()
        if not weights:
            return base_score
        adjustment = 0.0
        for key, weight in weights.items():
            value = stats.get(key, 0)
            adjustment += weight * (value / 100.0) * 5
        return max(0, min(100, int(base_score + adjustment)))
