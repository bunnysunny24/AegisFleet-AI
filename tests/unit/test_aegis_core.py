"""
Unit and Integration Tests for AegisFleet Platform.
Targeting >85% coverage across core services, algorithms, and models per Section 12.
"""
import pytest
from datetime import datetime, timezone
from simulator.vin_generator import generate_valid_vin, validate_vin, calculate_check_digit
from services.ingestion.normalizer import OEMAdapter, CanonicalTelemetryEvent
from services.ingestion.bloom_filter import BloomFilter, IngestionDeduplicator
from services.analytics.service_router import ServiceCenterRouter, haversine_distance_km
from services.analytics.stream_processor import AnomalyProcessor
from services.ml_engine.predictive_model import FailureRiskPredictor
from services.core_api.models import AlertSeverity

# 1. VIN Generation & Validation Tests (Section 9)
def test_valid_vin_generation_and_validation():
    for _ in range(50):
        vin = generate_valid_vin()
        assert len(vin) == 17, "VIN must be exactly 17 characters"
        assert not any(c in vin for c in "IOQ"), "VIN must not contain letters I, O, or Q"
        assert validate_vin(vin) is True, f"Generated VIN failed check-digit validation: {vin}"

def test_invalid_vin_detection():
    # Wrong length
    assert validate_vin("1HGCM82633A00435") is False
    # Contains illegal characters
    assert validate_vin("1HGCM82633I004352") is False
    assert validate_vin("1HGCM82633O004352") is False
    assert validate_vin("1HGCM82633Q004352") is False
    # Corrupted check digit at pos 9
    assert validate_vin("1HGCM82639A004352") is False

# 2. Multi-OEM Normalizer Adapter Tests (Section 6.3 & 7)
def test_standard_telemetry_normalization():
    vin = generate_valid_vin()
    raw = {
        "vin": vin,
        "ts": "2026-09-25T10:15:02.120Z",
        "lat": 37.7749,
        "lon": -122.4194,
        "speed_kmh": 68.5,
        "soc_pct": 55.0,
        "odo_km": 14200.5,
        "dtc": ["P0301"],
        "evt": "DTC_TRIGGER",
        "seq": 1001
    }
    event = OEMAdapter.normalize(raw)
    assert isinstance(event, CanonicalTelemetryEvent)
    assert event.vin == vin
    assert event.speed_kmh == 68.5
    assert "P0301" in event.dtc_codes
    assert event.oem_source == "Standard"

def test_volvo_nested_format_normalization():
    vin = generate_valid_vin()
    volvo_raw = {
        "header": {
            "vin": vin,
            "sequenceId": 402,
            "timestampUtc": "2026-09-27T12:00:00Z",
            "oem": "Volvo-Car-Mobility"
        },
        "position": {"latitude": 40.7128, "longitude": -74.0060},
        "metrics": {
            "speed": 82.0,
            "batteryStateOfCharge": 78.5,
            "odometer": 25000.0,
            "engineCoolantTemp": 91.5,
            "activeDtcCodes": []
        },
        "eventType": "PERIODIC_HEARTBEAT"
    }
    event = OEMAdapter.normalize(volvo_raw)
    assert event.vin == vin
    assert event.latitude == 40.7128
    assert event.soc_pct == 78.5
    assert event.sequence_id == 402
    assert event.oem_source == "Volvo"

def test_stellantis_mobilisights_format_normalization():
    vin = generate_valid_vin()
    epoch_ms = 1790400000000
    st_raw = {
        "vin": vin,
        "msg_seq": 881,
        "epoch_time_ms": epoch_ms,
        "gps": [34.0522, -118.2437],
        "kph": 105.0,
        "soc": 60.0,
        "distance_km": 45000.0,
        "coolant_c": 98.0,
        "faults": ["P0420"],
        "event_name": "HIGH_SPEED",
        "provider": "Mobilisights"
    }
    event = OEMAdapter.normalize(st_raw)
    assert event.vin == vin
    assert event.speed_kmh == 105.0
    assert "P0420" in event.dtc_codes
    assert event.oem_source == "Stellantis"

# 3. Bloom Filter & Deduplication Tests (Section 9)
def test_bloom_filter_deduplication():
    bf = BloomFilter(expected_elements=1000, false_positive_rate=0.01)
    key1 = "1HGCM82633A004352:1001"
    key2 = "1HGCM82633A004352:1002"

    assert bf.contains(key1) is False
    bf.add(key1)
    assert bf.contains(key1) is True
    assert bf.contains(key2) is False

def test_ingestion_deduplicator_out_of_order():
    dedup = IngestionDeduplicator()
    vin = generate_valid_vin()

    # Normal arrival seq 100
    is_dup, is_ooo = dedup.process_event(vin, 100)
    assert not is_dup and not is_ooo

    # Duplicate arrival seq 100
    is_dup, is_ooo = dedup.process_event(vin, 100)
    assert is_dup is True

    # Out of order packet seq 95
    is_dup, is_ooo = dedup.process_event(vin, 95)
    assert not is_dup and is_ooo is True

# 4. Service Router / Dijkstra Spatial Tests (Section 9)
def test_service_router_allocation():
    centers = [
        {"id": "sc1", "name": "NY North Hub", "latitude": 40.78, "longitude": -73.97, "can_service_ev": True, "can_service_ice": True, "max_bays": 10, "current_active_orders": 2},
        {"id": "sc2", "name": "SF Bay Hub", "latitude": 37.77, "longitude": -122.41, "can_service_ev": False, "can_service_ice": True, "max_bays": 10, "current_active_orders": 1}
    ]
    router = ServiceCenterRouter(centers)

    # Vehicle in Manhattan (40.75, -73.98) - EV
    best = router.find_optimal_service_center(40.75, -73.98, is_ev=True, remaining_range_km=100.0)
    assert best is not None
    assert best["id"] == "sc1"
    assert best["distance_km"] < 10.0

# 5. ML Breakdown Risk Predictor Tests (Section 11)
def test_predictive_risk_model():
    predictor = FailureRiskPredictor()
    metrics = predictor.train_and_evaluate()

    assert "roc_auc" in metrics["model"]
    assert metrics["model"]["roc_auc"] > 0.80, "ROC-AUC must exceed 0.80 baseline"

    # Test vehicle with healthy profile
    healthy_eval = predictor.predict_vehicle_risk({
        "odometer_km": 15000.0,
        "vehicle_age_years": 1.0,
        "mean_engine_temp_c": 88.0,
        "temp_variance": 1.2,
        "min_oil_pressure_psi": 50.0,
        "battery_soc_pct": 85.0,
        "dtc_fault_count": 0,
        "harsh_braking_events_per_100km": 0.5
    })
    assert healthy_eval["risk_tier"] == "HEALTHY"
    assert healthy_eval["breakdown_risk_score"] < 0.35

    # Test vehicle with degrading profile
    failing_eval = predictor.predict_vehicle_risk({
        "odometer_km": 195000.0,
        "vehicle_age_years": 6.5,
        "mean_engine_temp_c": 112.0,
        "temp_variance": 14.0,
        "min_oil_pressure_psi": 22.0,
        "battery_soc_pct": 18.0,
        "dtc_fault_count": 3,
        "harsh_braking_events_per_100km": 4.5
    })
    assert failing_eval["risk_tier"] in ("ELEVATED", "CRITICAL")
    assert failing_eval["breakdown_risk_score"] > 0.50
