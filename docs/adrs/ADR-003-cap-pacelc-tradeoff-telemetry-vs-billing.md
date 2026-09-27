# ADR-003: CAP & PACELC Trade-Offs: Raw Telemetry Stream (AP) vs. Fleet Accounting & Work Orders (CP)

## Status
Accepted

## Context
Section 10 of the Hackathon requirements specifies:
"CAP theorem: choose and justify consistency or availability for each kind of data. For example, billing may need CP (strong consistency) while raw telemetry can be AP (eventual consistency). Discuss PACELC latency trade-offs."

A connected vehicle platform ingests millions of data points every minute while concurrently managing critical legal agreements, subscriptions, vehicle recovery actions, and maintenance work orders. A monolithic consistency guarantee across all data paths is technically suboptimal.

## PACELC Trade-off Matrix

| Domain | CAP Classification | PACELC Classification | Justification |
| :--- | :--- | :--- | :--- |
| **Raw Telemetry Stream** (GPS, Speed, Battery, Temp) | **AP** (Available, Partition-Tolerant) | **PA/EL** (If Partition: Availability; Else: Latency over Consistency) | Telemetry is monotonic time-series. Dropping or delaying a single packet to enforce distributed consensus violates the <2s dashboard SLA. Eventual consistency is completely sufficient. |
| **Fleet Ownership & Billing** | **CP** (Consistent, Partition-Tolerant) | **PC/EC** (If Partition: Consistency; Else: Consistency over Latency) | Vehicle ownership, tenant lease agreements, and billing cannot tolerate dirty reads or split-brain double-billing. Strict linearizable ACID transactions required. |
| **Critical Safety Alerts & Work Orders** | **Hybrid Eventual CP** | **PA/EC** | Alerts must be accepted immediately (AP intake), but once persisted, work order dispatch to regional service centers adheres to strict atomic row locking. |

## Consequences
- Telemetry ingestion pipelines utilize non-blocking asynchronous workers and Redis caches to prioritize extreme write availability and low latency.
- PostgreSQL transactional tables enforce foreign key cascade restraints and row-level locks for work orders and audit logs.
