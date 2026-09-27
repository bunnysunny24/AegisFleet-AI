"""
AegisFleet AI - Core Database Models (3NF Relational Core)
Normalized schema in Third Normal Form (3NF) with zero redundancy and strict foreign key integrity.
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class PowertrainType(str, Enum):
    ICE = "ICE"
    EV = "EV"
    HYBRID = "HYBRID"

class VehicleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"
    DECOMMISSIONED = "DECOMMISSIONED"

class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

class WorkOrderStatus(str, Enum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

# 1. Fleets Table (3NF Core)
class Fleet(Base):
    __tablename__ = "fleets"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    company_code = Column(String(50), nullable=False, unique=True)
    region = Column(String(50), nullable=False, default="North America")
    contact_email = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vehicles = relationship("Vehicle", back_populates="fleet", cascade="all, delete-orphan")
    drivers = relationship("Driver", back_populates="fleet", cascade="all, delete-orphan")

# 2. Vehicles Table (3NF: VIN validation standard, no composite repeating groups)
class Vehicle(Base):
    __tablename__ = "vehicles"

    vin = Column(String(17), primary_key=True)
    fleet_id = Column(String(36), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False, index=True)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    powertrain = Column(SQLEnum(PowertrainType), nullable=False, default=PowertrainType.ICE)
    battery_capacity_kwh = Column(Float, nullable=True) # Null for pure ICE
    fuel_capacity_liters = Column(Float, nullable=True) # Null for pure EV
    odometer_km = Column(Float, nullable=False, default=0.0)
    current_status = Column(SQLEnum(VehicleStatus), nullable=False, default=VehicleStatus.ACTIVE)
    last_latitude = Column(Float, nullable=True)
    last_longitude = Column(Float, nullable=True)
    last_telemetry_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("length(vin) = 17", name="valid_vin_length"),
        Index("idx_vehicles_fleet_status", "fleet_id", "current_status"),
    )

    fleet = relationship("Fleet", back_populates="vehicles")
    driver_assignments = relationship("VehicleDriverAssignment", back_populates="vehicle")
    alerts = relationship("Alert", back_populates="vehicle")
    work_orders = relationship("MaintenanceWorkOrder", back_populates="vehicle")

# 3. Drivers Table (3NF Core)
class Driver(Base):
    __tablename__ = "drivers"

    id = Column(String(36), primary_key=True)
    fleet_id = Column(String(36), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    license_number = Column(String(50), nullable=False, unique=True)
    phone = Column(String(25), nullable=True)
    safety_score = Column(Float, nullable=False, default=100.0) # 0 to 100
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fleet = relationship("Fleet", back_populates="drivers")
    assignments = relationship("VehicleDriverAssignment", back_populates="driver")

# 4. Driver-Vehicle Mapping (Normalizing M:N assignment with temporal bounds)
class VehicleDriverAssignment(Base):
    __tablename__ = "vehicle_driver_assignments"

    id = Column(String(36), primary_key=True)
    vin = Column(String(17), ForeignKey("vehicles.vin", ondelete="CASCADE"), nullable=False, index=True)
    driver_id = Column(String(36), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    unassigned_at = Column(DateTime, nullable=True)

    vehicle = relationship("Vehicle", back_populates="driver_assignments")
    driver = relationship("Driver", back_populates="assignments")

# 5. Diagnostic Trouble Code Catalog (3NF: Eliminates redundant DTC descriptions)
class DTCFaultDefinition(Base):
    __tablename__ = "dtc_fault_definitions"

    code = Column(String(10), primary_key=True) # e.g., P0301, P0420, U0100
    subsystem = Column(String(50), nullable=False) # Engine, Transmission, Battery, Hybrid, Chassis
    description = Column(String(255), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, default=AlertSeverity.WARNING)
    standard_repair_action = Column(Text, nullable=False)
    estimated_repair_cost_usd = Column(Float, nullable=False, default=150.0)
    urgency_days = Column(Integer, nullable=False, default=7)

# 6. Service Centers & Depots (Used in Dijkstra routing algorithm)
class ServiceCenter(Base):
    __tablename__ = "service_centers"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    can_service_ev = Column(Boolean, nullable=False, default=True)
    can_service_ice = Column(Boolean, nullable=False, default=True)
    max_bays = Column(Integer, nullable=False, default=10)
    current_active_orders = Column(Integer, nullable=False, default=0)

    work_orders = relationship("MaintenanceWorkOrder", back_populates="service_center")

# 7. Real-Time Telemetry Alerts (3NF: Linked to Vehicle and Fault Code)
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True)
    vin = Column(String(17), ForeignKey("vehicles.vin", ondelete="CASCADE"), nullable=False, index=True)
    dtc_code = Column(String(10), ForeignKey("dtc_fault_definitions.code", ondelete="SET NULL"), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False) # DTC_TRIGGER, HIGH_COOLANT_TEMP, LOW_BATTERY, HARSH_BRAKE
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=True) # e.g. 112.5 deg C
    threshold_value = Column(Float, nullable=True) # e.g. 105.0 deg C
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.OPEN, index=True)
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_alerts_vin_status_severity", "vin", "status", "severity"),
    )

    vehicle = relationship("Vehicle", back_populates="alerts")
    fault_def = relationship("DTCFaultDefinition")
    work_orders = relationship("MaintenanceWorkOrder", back_populates="alert")

# 8. Maintenance Work Orders (Automated Predictive Prescriptions)
class MaintenanceWorkOrder(Base):
    __tablename__ = "maintenance_work_orders"

    id = Column(String(36), primary_key=True)
    vin = Column(String(17), ForeignKey("vehicles.vin", ondelete="CASCADE"), nullable=False, index=True)
    alert_id = Column(String(36), ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True)
    service_center_id = Column(String(36), ForeignKey("service_centers.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(150), nullable=False)
    recommended_action = Column(Text, nullable=False)
    priority = Column(SQLEnum(AlertSeverity), nullable=False, default=AlertSeverity.WARNING)
    status = Column(SQLEnum(WorkOrderStatus), nullable=False, default=WorkOrderStatus.PENDING, index=True)
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)
    scheduled_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vehicle = relationship("Vehicle", back_populates="work_orders")
    alert = relationship("Alert", back_populates="work_orders")
    service_center = relationship("ServiceCenter", back_populates="work_orders")

# 9. Audit Trail Log (Compliance with GDPR, DPDP Act 2023, and Agentic AI operations)
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(String(100), nullable=False) # user_id, 'SYSTEM_STREAM_ENGINE', or 'AGENTIC_AI'
    action = Column(String(50), nullable=False) # READ, WRITE, EXPORT, MASK_DATA, DELETE_USER
    resource_type = Column(String(50), nullable=False) # Vehicle, Telemetry, Driver, WorkOrder
    resource_id = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
