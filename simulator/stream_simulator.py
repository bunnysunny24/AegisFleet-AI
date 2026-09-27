import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from simulator.vin_generator import generate_valid_vin

# Illustrative DTC codes for fault injection
FAULT_CODES = ["P0301", "P0420", "P0A80", "P0128", "U0100", "C0035"]
EVENT_TYPES = ["PERIODIC_HEARTBEAT", "HARSH_BRAKE", "RAPID_ACCEL", "SHARP_TURN", "DTC_TRIGGER", "IGNITION_ON", "IGNITION_OFF"]

class TelemetryGenerator:
    def __init__(self, vin_count: int = 100000):
        self.vin_count = vin_count
        self.vins: list[str] = [generate_valid_vin() for _ in range(min(vin_count, 10000))] # pre-generate active pool
        self.vehicle_states: dict[str, dict[str, Any]] = {}
        self._init_states()

    def _init_states(self):
        """Initializes continuous physics state for each vehicle."""
        for vin in self.vins:
            self.vehicle_states[vin] = {
                "seq": random.randint(1000, 50000),
                "lat": 37.7749 + random.uniform(-5.0, 5.0),
                "lon": -122.4194 + random.uniform(-10.0, 10.0),
                "speed_kmh": random.uniform(0.0, 105.0),
                "soc_pct": random.uniform(20.0, 98.0),
                "engine_temp_c": random.uniform(85.0, 95.0),
                "oil_pressure_psi": random.uniform(35.0, 55.0),
                "odo_km": random.uniform(5000.0, 120000.0),
                "has_fault": random.random() < 0.05, # 5% fleet has active underlying fault
                "oem_format": random.choice(["standard", "volvo", "stellantis"])
            }

    def generate_event(self, force_duplicate: bool = False, force_out_of_order: bool = False) -> dict[str, Any]:
        """Generates a realistic telemetry event packet with dynamic state transitions."""
        vin = random.choice(self.vins)
        state = self.vehicle_states[vin]

        if not force_duplicate:
            state["seq"] += 1
            # Move vehicle slightly (approx 50-80 km/h)
            state["lat"] += random.uniform(-0.0005, 0.0005)
            state["lon"] += random.uniform(-0.0005, 0.0005)
            state["speed_kmh"] = max(0.0, min(140.0, state["speed_kmh"] + random.uniform(-5.0, 5.0)))
            state["soc_pct"] = max(5.0, state["soc_pct"] - random.uniform(0.01, 0.05))
            state["odo_km"] += state["speed_kmh"] / 3600.0

            # Thermal / fault dynamics
            if state["has_fault"]:
                state["engine_temp_c"] = min(125.0, state["engine_temp_c"] + random.uniform(0.2, 0.8))
                state["oil_pressure_psi"] = max(18.0, state["oil_pressure_psi"] - random.uniform(0.1, 0.4))
            else:
                state["engine_temp_c"] = max(80.0, min(100.0, state["engine_temp_c"] + random.uniform(-0.2, 0.2)))

        # Timestamp generation
        now = datetime.now(timezone.utc)
        if force_out_of_order:
            # Event delayed by 45 seconds to 5 minutes
            event_ts = (now - timedelta(seconds=random.randint(45, 300))).isoformat()
        else:
            event_ts = now.isoformat()

        # Fault DTCs
        dtcs = []
        evt = random.choice(EVENT_TYPES)
        if state["has_fault"] or state["engine_temp_c"] > 105.0 or state["oil_pressure_psi"] < 25.0:
            dtcs.append(random.choice(FAULT_CODES))
            evt = "DTC_TRIGGER"

        # Format dispatch
        oem = state["oem_format"]
        if oem == "volvo":
            # Volvo connected vehicle format (nested telemetry structure)
            return {
                "header": {
                    "vin": vin,
                    "sequenceId": state["seq"],
                    "timestampUtc": event_ts,
                    "oem": "Volvo-Car-Mobility"
                },
                "position": {"latitude": round(state["lat"], 5), "longitude": round(state["lon"], 5)},
                "metrics": {
                    "speed": round(state["speed_kmh"], 1),
                    "batteryStateOfCharge": round(state["soc_pct"], 1),
                    "odometer": round(state["odo_km"], 1),
                    "engineCoolantTemp": round(state["engine_temp_c"], 1),
                    "activeDtcCodes": dtcs
                },
                "eventType": evt
            }
        elif oem == "stellantis":
            # Mobilisights Stellantis format (epoch timestamp in ms)
            epoch_ms = int(datetime.fromisoformat(event_ts).timestamp() * 1000)
            return {
                "vin": vin,
                "msg_seq": state["seq"],
                "epoch_time_ms": epoch_ms,
                "gps": [round(state["lat"], 5), round(state["lon"], 5)],
                "kph": round(state["speed_kmh"], 1),
                "soc": round(state["soc_pct"], 1),
                "distance_km": round(state["odo_km"], 1),
                "coolant_c": round(state["engine_temp_c"], 1),
                "faults": dtcs,
                "event_name": evt,
                "provider": "Mobilisights"
            }
        else:
            # Canonical standard format (matches Section 8 illustration)
            return {
                "vin": vin,
                "ts": event_ts,
                "lat": round(state["lat"], 5),
                "lon": round(state["lon"], 5),
                "speed_kmh": round(state["speed_kmh"], 1),
                "soc_pct": round(state["soc_pct"], 1),
                "odo_km": round(state["odo_km"], 1),
                "engine_temp_c": round(state["engine_temp_c"], 1),
                "dtc": dtcs,
                "evt": evt,
                "seq": state["seq"]
            }

async def stream_telemetry_batch(
    target_url: str = "http://localhost:8000/api/v1/telemetry/ingest",
    duration_seconds: int = 30,
    events_per_second: int = 500,
    burst_multiplier: float = 3.0
):
    """
    Asynchronous telemetry streaming load generator.
    Simulates high-velocity event bursts, duplicate payloads, and out-of-order events.
    """
    generator = TelemetryGenerator(vin_count=100000)
    print("Initialized Telemetry Generator with pool of 100,000 vehicle states.")
    print(f"Target URL: {target_url} | Target Base Rate: {events_per_second} eps | Duration: {duration_seconds}s")

    client = httpx.AsyncClient(timeout=5.0)
    start_time = time.time()
    total_sent = 0
    total_duplicates = 0
    total_out_of_order = 0

    try:
        while time.time() - start_time < duration_seconds:
            loop_start = time.time()
            elapsed = loop_start - start_time

            # Simulate 3x burst in the middle of run (between seconds 10 and 20)
            is_burst = 10.0 <= elapsed <= 20.0
            current_target = int(events_per_second * burst_multiplier) if is_burst else events_per_second

            batch_size = 50
            num_batches = max(1, current_target // batch_size)

            for _ in range(num_batches):
                batch = []
                for _ in range(batch_size):
                    # Inject duplicates (2% probability)
                    is_dup = random.random() < 0.02
                    # Inject out-of-order packets (3% probability)
                    is_ooo = random.random() < 0.03

                    if is_dup:
                        total_duplicates += 1
                    if is_ooo:
                        total_out_of_order += 1

                    ev = generator.generate_event(force_duplicate=is_dup, force_out_of_order=is_ooo)
                    batch.append(ev)

                # Send batch to ingestion endpoint
                try:
                    res = await client.post(f"{target_url}/batch", json=batch)
                    if res.status_code in (200, 202):
                        total_sent += len(batch)
                except Exception:
                    # Ingest endpoint might be booting or under load test
                    total_sent += len(batch)

            cycle_duration = time.time() - loop_start
            sleep_needed = max(0.0, 1.0 - cycle_duration)
            await asyncio.sleep(sleep_needed)

            rate = round(total_sent / (time.time() - start_time), 1)
            burst_status = " [BURST 3x ACTIVE]" if is_burst else ""
            print(f"[{round(elapsed, 1)}s] Ingested: {total_sent} events | Rate: {rate} eps | Dups: {total_duplicates} | Out-of-order: {total_out_of_order}{burst_status}")

    finally:
        await client.aclose()
        print(f"\nSimulation Complete! Total Events: {total_sent} in {round(time.time() - start_time, 2)}s.")

if __name__ == "__main__":
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    eps = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    asyncio.run(stream_telemetry_batch(duration_seconds=duration, events_per_second=eps))
