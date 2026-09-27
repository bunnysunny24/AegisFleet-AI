"""
Multi-OEM Telemetry Normalization Adapter.
Implements the Adapter Design Pattern (Section 6.3) to translate diverse OEM payload schemas
(Volvo nested structure, Stellantis Mobilisights epoch format, and Standard format)
into a unified CanonicalTelemetryEvent.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator
from simulator.vin_generator import validate_vin

class CanonicalTelemetryEvent(BaseModel):
    """Unified canonical vehicle telemetry representation across all 25+ automotive brands."""
    vin: str = Field(..., min_length=17, max_length=17, description="ISO 3779 17-char VIN")
    timestamp: datetime = Field(..., description="UTC ISO8601 timestamp")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    speed_kmh: float = Field(..., ge=0.0, le=250.0)
    soc_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Battery State of Charge")
    odometer_km: float = Field(..., ge=0.0)
    engine_temp_c: Optional[float] = Field(None, ge=-40.0, le=160.0)
    oil_pressure_psi: Optional[float] = Field(None, ge=0.0, le=120.0)
    dtc_codes: List[str] = Field(default_factory=list)
    event_type: str = Field(default="HEARTBEAT")
    sequence_id: int = Field(..., ge=0)
    oem_source: str = Field(default="GENERIC")

    @field_validator("vin")
    @classmethod
    def check_valid_vin(cls, v: str) -> str:
        if not validate_vin(v):
            raise ValueError(f"Invalid VIN checksum or format: {v}")
        return v.upper()

class OEMAdapter:
    """Normalizes arbitrary raw OEM payloads into CanonicalTelemetryEvent."""

    @staticmethod
    def normalize(payload: Dict[str, Any]) -> CanonicalTelemetryEvent:
        # 1. Volvo OEM nested format
        if "header" in payload and "oem" in payload.get("header", {}):
            hdr = payload["header"]
            pos = payload.get("position", {})
            metrics = payload.get("metrics", {})
            ts_str = hdr.get("timestampUtc")
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else datetime.now(timezone.utc)

            return CanonicalTelemetryEvent(
                vin=hdr["vin"],
                timestamp=ts,
                latitude=pos.get("latitude", 0.0),
                longitude=pos.get("longitude", 0.0),
                speed_kmh=metrics.get("speed", 0.0),
                soc_pct=metrics.get("batteryStateOfCharge"),
                odometer_km=metrics.get("odometer", 0.0),
                engine_temp_c=metrics.get("engineCoolantTemp"),
                dtc_codes=metrics.get("activeDtcCodes", []),
                event_type=payload.get("eventType", "HEARTBEAT"),
                sequence_id=hdr.get("sequenceId", 0),
                oem_source="Volvo"
            )

        # 2. Stellantis / Mobilisights format
        elif "epoch_time_ms" in payload and "gps" in payload:
            epoch_sec = payload["epoch_time_ms"] / 1000.0
            ts = datetime.fromtimestamp(epoch_sec, tz=timezone.utc)
            gps = payload.get("gps", [0.0, 0.0])

            return CanonicalTelemetryEvent(
                vin=payload["vin"],
                timestamp=ts,
                latitude=gps[0],
                longitude=gps[1],
                speed_kmh=payload.get("kph", 0.0),
                soc_pct=payload.get("soc"),
                odometer_km=payload.get("distance_km", 0.0),
                engine_temp_c=payload.get("coolant_c"),
                dtc_codes=payload.get("faults", []),
                event_type=payload.get("event_name", "HEARTBEAT"),
                sequence_id=payload.get("msg_seq", 0),
                oem_source="Stellantis"
            )

        # 3. Canonical / Standard format
        else:
            ts_raw = payload.get("ts")
            if isinstance(ts_raw, str):
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            else:
                ts = datetime.now(timezone.utc)

            return CanonicalTelemetryEvent(
                vin=payload["vin"],
                timestamp=ts,
                latitude=payload.get("lat", 0.0),
                longitude=payload.get("lon", 0.0),
                speed_kmh=payload.get("speed_kmh", 0.0),
                soc_pct=payload.get("soc_pct"),
                odometer_km=payload.get("odo_km", 0.0),
                engine_temp_c=payload.get("engine_temp_c"),
                oil_pressure_psi=payload.get("oil_pressure_psi"),
                dtc_codes=payload.get("dtc", []),
                event_type=payload.get("evt", "HEARTBEAT"),
                sequence_id=payload.get("seq", 0),
                oem_source="Standard"
            )
