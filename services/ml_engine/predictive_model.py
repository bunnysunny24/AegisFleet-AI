"""
AegisFleet Predictive Maintenance Machine Learning Engine.
Predicts 7-Day Unplanned Breakdown Probability and Remaining Useful Life (RUL).
Includes feature engineering, baseline heuristic comparison, and evaluation metrics (ROC-AUC, F1, Recall).
"""
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split


class FailureRiskPredictor:
    """
    Predictive maintenance classifier using gradient boosted decision trees.
    Calculates breakdown risk score (0.0 - 1.0) for every connected vehicle.
    """
    def __init__(self):
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.08,
            max_depth=4,
            random_state=42
        )
        self.is_trained = False
        self.feature_names = [
            "odometer_km",
            "vehicle_age_years",
            "mean_engine_temp_c",
            "temp_variance",
            "min_oil_pressure_psi",
            "battery_soc_pct",
            "dtc_fault_count",
            "harsh_braking_events_per_100km"
        ]

    def _generate_synthetic_training_data(self, samples: int = 25000) -> tuple[np.ndarray, np.ndarray]:
        """
        Generates grounded physics telemetry samples for training.
        Simulates mechanical wear patterns (elevated thermal variance, drop in oil pressure, high mileage).
        """
        np.random.seed(42)
        # Features
        odo = np.random.uniform(5000, 220000, samples)
        age = np.random.uniform(0.5, 8.0, samples)
        temp_mean = np.random.normal(90.0, 7.0, samples)
        temp_var = np.random.exponential(4.0, samples)
        oil_press = np.random.normal(45.0, 8.0, samples)
        soc = np.random.uniform(15.0, 95.0, samples)
        dtc_count = np.random.poisson(0.3, samples)
        harsh_brakes = np.random.poisson(1.2, samples)

        X = np.column_stack([odo, age, temp_mean, temp_var, oil_press, soc, dtc_count, harsh_brakes])

        # Underlying ground-truth breakdown probability function
        log_odds = (
            -5.5 +
            0.000015 * odo +
            0.25 * age +
            0.08 * (temp_mean - 90.0) +
            0.15 * temp_var -
            0.12 * (oil_press - 40.0) +
            1.8 * dtc_count +
            0.3 * harsh_brakes
        )
        probs = 1.0 / (1.0 + np.exp(-log_odds))
        y = (np.random.rand(samples) < probs).astype(int)

        return X, y

    def train_and_evaluate(self) -> dict[str, Any]:
        """Trains model and benchmarks against simple rule-based baseline."""
        X, y = self._generate_synthetic_training_data(samples=20000)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

        # 1. Train Gradient Boosting Model
        self.model.fit(X_train, y_train)
        self.is_trained = True

        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba >= 0.5).astype(int)

        # 2. Benchmark Baseline: Naive threshold rule (breakdown if DTC count > 0 OR temp > 105)
        # index 6 is dtc_count, index 2 is temp_mean
        baseline_pred = ((X_test[:, 6] > 0) | (X_test[:, 2] > 105.0)).astype(int)

        metrics = {
            "model": {
                "roc_auc": round(float(roc_auc_score(y_test, y_pred_proba)), 4),
                "f1_score": round(float(f1_score(y_test, y_pred)), 4),
                "precision": round(float(precision_score(y_test, y_pred)), 4),
                "recall": round(float(recall_score(y_test, y_pred)), 4),
            },
            "baseline_heuristic": {
                "f1_score": round(float(f1_score(y_test, baseline_pred)), 4),
                "precision": round(float(precision_score(y_test, baseline_pred)), 4),
                "recall": round(float(recall_score(y_test, baseline_pred)), 4),
            },
            "feature_importance": {
                name: round(float(imp), 4)
                for name, imp in zip(self.feature_names, self.model.feature_importances_, strict=True)
            }
        }
        return metrics

    def predict_vehicle_risk(self, feature_vector: dict[str, float]) -> dict[str, Any]:
        """Infers 7-day failure risk score and estimated remaining useful life (RUL)."""
        if not self.is_trained:
            self.train_and_evaluate()

        vec = np.array([[
            feature_vector.get("odometer_km", 50000.0),
            feature_vector.get("vehicle_age_years", 2.0),
            feature_vector.get("mean_engine_temp_c", 90.0),
            feature_vector.get("temp_variance", 2.0),
            feature_vector.get("min_oil_pressure_psi", 45.0),
            feature_vector.get("battery_soc_pct", 75.0),
            feature_vector.get("dtc_fault_count", 0.0),
            feature_vector.get("harsh_braking_events_per_100km", 1.0)
        ]])

        risk_prob = float(self.model.predict_proba(vec)[0, 1])

        # RUL estimation based on risk profile
        if risk_prob > 0.75:
            risk_tier = "CRITICAL"
            estimated_rul_days = round(max(0.5, (1.0 - risk_prob) * 4.0), 1)
        elif risk_prob > 0.40:
            risk_tier = "ELEVATED"
            estimated_rul_days = round(max(2.0, (1.0 - risk_prob) * 12.0), 1)
        else:
            risk_tier = "HEALTHY"
            estimated_rul_days = round(max(14.0, (1.0 - risk_prob) * 90.0), 1)

        return {
            "breakdown_risk_score": round(risk_prob, 3),
            "risk_tier": risk_tier,
            "estimated_rul_days": estimated_rul_days,
            "recommended_inspection_window_days": 1 if risk_tier == "CRITICAL" else (7 if risk_tier == "ELEVATED" else 30),
            "estimated_avoided_cost_usd": 2800.0 if risk_tier == "CRITICAL" else (650.0 if risk_tier == "ELEVATED" else 0.0)
        }

# Global singleton predictor
global_predictor = FailureRiskPredictor()
