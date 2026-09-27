"""
Real-time Stream Analytics and Anomaly Detection Engine.
Performs sliding-window telemetry evaluation, DTC fault code extraction,
threshold boundary checks, and automated maintenance work-order generation.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from services.analytics.service_router import ServiceCenterRouter
from services.core_api.models import AlertSeverity, AlertStatus, WorkOrderStatus
from services.ingestion.normalizer import CanonicalTelemetryEvent


class AnomalyProcessor:
    def __init__(self, service_centers: list[dict[str, Any]] | None = None):
        self.router = ServiceCenterRouter(service_centers or [])
        # In-memory sliding window history: vin -> list of last N events
        self.sliding_windows: dict[str, list[CanonicalTelemetryEvent]] = {}
        self.max_window_size = 10

    def process_event(self, event: CanonicalTelemetryEvent) -> list[dict[str, Any]]:
        """
        Analyzes an incoming canonical event.
        Returns a list of generated alert dictionaries (if any threshold or fault is breached).
        """
        alerts = []
        vin = event.vin

        # Maintain sliding window per VIN
        if vin not in self.sliding_windows:
            self.sliding_windows[vin] = []
        win = self.sliding_windows[vin]
        win.append(event)
        if len(win) > self.max_window_size:
            win.pop(0)

        # 1. Critical DTC Diagnostic Codes
        for code in event.dtc_codes:
            alerts.append({
                "id": str(uuid.uuid4()),
                "vin": vin,
                "dtc_code": code,
                "alert_type": "DTC_FAULT_TRIGGERED",
                "severity": AlertSeverity.CRITICAL if code in ("P0301", "P0A80", "U0100") else AlertSeverity.WARNING,
                "description": f"Active Diagnostic Trouble Code detected: {code}",
                "metric_value": None,
                "threshold_value": None,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "triggered_at": event.timestamp,
                "status": AlertStatus.OPEN
            })

        # 2. Engine Coolant Temperature Spike (> 105 C is Warning, > 115 C is Critical)
        if event.engine_temp_c is not None:
            if event.engine_temp_c >= 115.0:
                alerts.append({
                    "id": str(uuid.uuid4()),
                    "vin": vin,
                    "dtc_code": "P0128",
                    "alert_type": "CRITICAL_COOLANT_OVERHEAT",
                    "severity": AlertSeverity.CRITICAL,
                    "description": f"Engine coolant temperature dangerous level: {event.engine_temp_c} deg C",
                    "metric_value": event.engine_temp_c,
                    "threshold_value": 115.0,
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "triggered_at": event.timestamp,
                    "status": AlertStatus.OPEN
                })
            elif event.engine_temp_c >= 105.0:
                alerts.append({
                    "id": str(uuid.uuid4()),
                    "vin": vin,
                    "dtc_code": "P0128",
                    "alert_type": "COOLANT_TEMP_ELEVATED",
                    "severity": AlertSeverity.WARNING,
                    "description": f"Engine coolant temperature elevated: {event.engine_temp_c} deg C",
                    "metric_value": event.engine_temp_c,
                    "threshold_value": 105.0,
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "triggered_at": event.timestamp,
                    "status": AlertStatus.OPEN
                })

        # 3. Critical Low Oil Pressure (< 25 PSI)
        if event.oil_pressure_psi is not None and event.oil_pressure_psi < 25.0 and event.speed_kmh > 10.0:
            alerts.append({
                "id": str(uuid.uuid4()),
                "vin": vin,
                "dtc_code": None,
                "alert_type": "LOW_ENGINE_OIL_PRESSURE",
                "severity": AlertSeverity.CRITICAL,
                "description": f"Low engine oil pressure during operation: {event.oil_pressure_psi} PSI (Min Safe: 25.0 PSI)",
                "metric_value": event.oil_pressure_psi,
                "threshold_value": 25.0,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "triggered_at": event.timestamp,
                "status": AlertStatus.OPEN
            })

        # 4. EV Battery State of Charge Depletion (< 15%)
        if event.soc_pct is not None and event.soc_pct < 15.0:
            alerts.append({
                "id": str(uuid.uuid4()),
                "vin": vin,
                "dtc_code": None,
                "alert_type": "LOW_BATTERY_CHARGE",
                "severity": AlertSeverity.WARNING if event.soc_pct >= 8.0 else AlertSeverity.CRITICAL,
                "description": f"EV traction battery depleted: {event.soc_pct}% SoC remaining",
                "metric_value": event.soc_pct,
                "threshold_value": 15.0,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "triggered_at": event.timestamp,
                "status": AlertStatus.OPEN
            })

        # 5. Sliding-Window Harsh Deceleration Detection (Harsh Brake)
        if len(win) >= 2:
            prev = win[-2]
            time_delta = (event.timestamp - prev.timestamp).total_seconds()
            if 0.5 <= time_delta <= 2.5:
                speed_drop = prev.speed_kmh - event.speed_kmh
                if speed_drop >= 28.0: # ~8 m/s^2 deceleration
                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "vin": vin,
                        "dtc_code": None,
                        "alert_type": "HARSH_BRAKE_EVENT",
                        "severity": AlertSeverity.WARNING,
                        "description": f"Harsh deceleration detected: -{round(speed_drop, 1)} km/h in {round(time_delta, 1)}s",
                        "metric_value": round(speed_drop, 1),
                        "threshold_value": 28.0,
                        "latitude": event.latitude,
                        "longitude": event.longitude,
                        "triggered_at": event.timestamp,
                        "status": AlertStatus.OPEN
                    })

        return alerts

    def create_work_order_for_alert(self, alert: dict[str, Any], vehicle_info: dict[str, Any]) -> dict[str, Any]:
        """
        Automatically prescribes a maintenance work order, assigning the nearest compatible service depot.
        """
        is_ev = vehicle_info.get("powertrain") == "EV"
        dest_center = self.router.find_optimal_service_center(
            vehicle_lat=alert.get("latitude", 37.7749),
            vehicle_lon=alert.get("longitude", -122.4194),
            is_ev=is_ev,
            remaining_range_km=vehicle_info.get("estimated_range_km", 150.0)
        )

        center_id = dest_center["id"] if dest_center else None
        center_name = dest_center["name"] if dest_center else "Unassigned Depot"

        dtc = alert.get("dtc_code")
        title = f"Automated Work Order: {alert.get('alert_type')}"
        if dtc:
            title += f" ({dtc})"

        return {
            "id": str(uuid.uuid4()),
            "vin": alert["vin"],
            "alert_id": alert["id"],
            "service_center_id": center_id,
            "title": title,
            "recommended_action": f"Dispatch vehicle to {center_name}. Perform diagnostic scan and remedy {alert.get('description')}.",
            "priority": alert.get("severity", AlertSeverity.WARNING),
            "status": WorkOrderStatus.PENDING,
            "estimated_cost_usd": 450.0 if alert.get("severity") == AlertSeverity.CRITICAL else 175.0,
            "created_at": datetime.now(timezone.utc)
        }
