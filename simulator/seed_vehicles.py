import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random
import time
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from services.core_api.database import SessionLocal, init_db
from services.core_api.models import (
    AlertSeverity,
    DTCFaultDefinition,
    Fleet,
    PowertrainType,
    ServiceCenter,
    Vehicle,
    VehicleStatus,
)
from simulator.vin_generator import generate_valid_vin

STANDARD_DTCS = [
    {
        "code": "P0301",
        "subsystem": "Powertrain / Engine",
        "description": "Cylinder 1 Misfire Detected",
        "severity": AlertSeverity.CRITICAL,
        "standard_repair_action": "Replace ignition coil pack and spark plug; test fuel injector impedance.",
        "estimated_repair_cost_usd": 240.0,
        "urgency_days": 2
    },
    {
        "code": "P0420",
        "subsystem": "Emissions / Exhaust",
        "description": "Catalyst System Efficiency Below Threshold (Bank 1)",
        "severity": AlertSeverity.WARNING,
        "standard_repair_action": "Inspect downstream O2 sensor and exhaust manifold for leaks before catalytic converter replacement.",
        "estimated_repair_cost_usd": 850.0,
        "urgency_days": 7
    },
    {
        "code": "P0A80",
        "subsystem": "EV Battery Pack",
        "description": "Replace Hybrid / EV Traction Battery Pack Degradation",
        "severity": AlertSeverity.CRITICAL,
        "standard_repair_action": "Module-level voltage balancing check; replace degraded battery module cell cluster.",
        "estimated_repair_cost_usd": 3200.0,
        "urgency_days": 1
    },
    {
        "code": "P0128",
        "subsystem": "Cooling System",
        "description": "Coolant Thermostat Below Regulating Temperature",
        "severity": AlertSeverity.WARNING,
        "standard_repair_action": "Flush coolant system and replace engine coolant thermostat assembly.",
        "estimated_repair_cost_usd": 180.0,
        "urgency_days": 5
    },
    {
        "code": "U0100",
        "subsystem": "CAN Bus Communications",
        "description": "Lost Communication With Engine Control Module (ECM/PCM)",
        "severity": AlertSeverity.CRITICAL,
        "standard_repair_action": "Inspect CAN-High / CAN-Low terminating resistor (120 Ohm) and wiring harness.",
        "estimated_repair_cost_usd": 420.0,
        "urgency_days": 1
    },
    {
        "code": "C0035",
        "subsystem": "Braking & ABS",
        "description": "Left Front Wheel Speed Sensor Circuit Fault",
        "severity": AlertSeverity.CRITICAL,
        "standard_repair_action": "Check ABS tone ring; replace left front wheel speed sensor.",
        "estimated_repair_cost_usd": 210.0,
        "urgency_days": 3
    }
]

SERVICE_CENTERS = [
    {"name": "Metro Fleet Hub North", "lat": 40.7831, "lon": -73.9712, "ev": True, "bays": 20},
    {"name": "South Bay Express Maintenance", "lat": 37.3382, "lon": -121.8863, "ev": True, "bays": 16},
    {"name": "Midwest Fleet Care Chicago", "lat": 41.8781, "lon": -87.6298, "ev": True, "bays": 24},
    {"name": "Dallas Logistics Service Depot", "lat": 32.7767, "lon": -96.7970, "ev": False, "bays": 18},
    {"name": "Atlanta FastCharge & Service Hub", "lat": 33.7490, "lon": -84.3880, "ev": True, "bays": 22},
    {"name": "Seattle Fleet Technologies Depot", "lat": 47.6062, "lon": -122.3321, "ev": True, "bays": 15},
]

FLEETS = [
    {"name": "Apex Logistics Express", "code": "APEX-LOG", "region": "North America"},
    {"name": "VoltHaul EV Freight", "code": "VOLT-FRT", "region": "Pacific Northwest"},
    {"name": "Starlight Commercial Rentals", "code": "STAR-RENT", "region": "Southeast"},
    {"name": "Quantum Cold-Chain Delivery", "code": "QNTM-COLD", "region": "Midwest"},
]

MAKES_MODELS = [
    ("Volvo", "FH Electric", PowertrainType.EV, 540.0, None),
    ("Volvo", "VNL 860", PowertrainType.ICE, None, 450.0),
    ("Stellantis", "Ram ProMaster EV", PowertrainType.EV, 110.0, None),
    ("Stellantis", "Ram 3500 Heavy Duty", PowertrainType.ICE, None, 120.0),
    ("Freightliner", "eCascadia", PowertrainType.EV, 438.0, None),
    ("Ford", "E-Transit Cargo", PowertrainType.EV, 68.0, None),
    ("Ford", "F-550 Super Duty", PowertrainType.ICE, None, 150.0),
    ("Toyota", "Tundra Hybrid i-FORCE", PowertrainType.HYBRID, 1.87, 85.0),
]

def seed_static_metadata(db: Session):
    """Seeds Fleets, DTCs, and Service Centers."""
    print("Seeding Fleets, DTC Catalog, and Service Centers...")
    # 1. Fleets
    fleet_objs = []
    for f in FLEETS:
        existing = db.query(Fleet).filter(Fleet.company_code == f["code"]).first()
        if not existing:
            fleet_obj = Fleet(
                id=str(uuid.uuid4()),
                name=f["name"],
                company_code=f["code"],
                region=f["region"],
                contact_email=f"operations@{f['code'].lower()}.com"
            )
            db.add(fleet_obj)
            fleet_objs.append(fleet_obj)
        else:
            fleet_objs.append(existing)
    db.commit()

    # 2. DTC Definitions
    for d in STANDARD_DTCS:
        existing = db.query(DTCFaultDefinition).filter(DTCFaultDefinition.code == d["code"]).first()
        if not existing:
            dtc_obj = DTCFaultDefinition(
                code=d["code"],
                subsystem=d["subsystem"],
                description=d["description"],
                severity=d["severity"],
                standard_repair_action=d["standard_repair_action"],
                estimated_repair_cost_usd=d["estimated_repair_cost_usd"],
                urgency_days=d["urgency_days"]
            )
            db.add(dtc_obj)
    db.commit()

    # 3. Service Centers
    for sc in SERVICE_CENTERS:
        existing = db.query(ServiceCenter).filter(ServiceCenter.name == sc["name"]).first()
        if not existing:
            sc_obj = ServiceCenter(
                id=str(uuid.uuid4()),
                name=sc["name"],
                address=f"{sc['name']} Industrial Blvd",
                latitude=sc["lat"],
                longitude=sc["lon"],
                can_service_ev=sc["ev"],
                can_service_ice=True,
                max_bays=sc["bays"],
                current_active_orders=random.randint(1, 8)
            )
            db.add(sc_obj)
    db.commit()
    print("Static metadata seeded successfully.")
    return fleet_objs

def seed_vehicles(count: int = 100000, batch_size: int = 5000):
    """
    Seeds vehicles in batches with realistic ISO 3779 VINs and powertrain attributes.
    Supports total count up to 100,000.
    """
    init_db()
    db = SessionLocal()
    fleet_objs = seed_static_metadata(db)
    fleet_ids = [f.id for f in fleet_objs]

    current_count = db.query(Vehicle).count()
    if current_count >= count:
        print(f"Database already contains {current_count} vehicles (Target: {count}). Skipping generation.")
        db.close()
        return

    needed = count - current_count
    print(f"Starting generation of {needed} vehicles to reach {count} connected vehicle fleet target...")
    start_time = time.time()

    # Base coordinates (USA continental bounding envelope)
    base_lat = 37.0
    base_lon = -95.0

    generated = 0
    while generated < needed:
        current_batch_size = min(batch_size, needed - generated)
        vehicles_batch = []
        for _ in range(current_batch_size):
            make_info = random.choice(MAKES_MODELS)
            vin = generate_valid_vin()
            v = Vehicle(
                vin=vin,
                fleet_id=random.choice(fleet_ids),
                make=make_info[0],
                model=make_info[1],
                year=random.choice([2023, 2024, 2025, 2026]),
                powertrain=make_info[2],
                battery_capacity_kwh=make_info[3],
                fuel_capacity_liters=make_info[4],
                odometer_km=round(random.uniform(500.0, 180000.0), 1),
                current_status=VehicleStatus.ACTIVE,
                last_latitude=round(base_lat + random.uniform(-8.0, 8.0), 5),
                last_longitude=round(base_lon + random.uniform(-20.0, 20.0), 5),
                last_telemetry_at=datetime.utcnow() - timedelta(minutes=random.randint(1, 120))
            )
            vehicles_batch.append(v)

        db.bulk_save_objects(vehicles_batch)
        db.commit()
        generated += current_batch_size
        elapsed = time.time() - start_time
        print(f"Generated {generated}/{needed} vehicles ({round(generated/elapsed, 1)} vehicles/sec)...")

    db.close()
    print(f"Seeding completed in {round(time.time() - start_time, 2)} seconds. Total vehicles: {count}.")

if __name__ == "__main__":
    import sys
    count_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed_vehicles(count=count_arg)
