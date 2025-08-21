import numpy as np
from sklearn.ensemble import RandomForestClassifier

class MLGuard:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        X = np.array([
            [0.1, 1, 100, 0],
            [0.9, 3, 5000, 1],
            [0.2, 1, 200, 0],
            [0.8, 4, 10000, 1],
        ])
        y = [0, 1, 0, 1]  # 0 = safe, 1 = risky
        self.model.fit(X, y)

    def build_features(self, system_load, wait_depth, amount, hotspot):
        return np.array([[system_load, wait_depth, amount, hotspot]])

    def predict_risk(self, features):
        return self.model.predict_proba(features)[0][1]

def get_default_guard():
    return MLGuard()
