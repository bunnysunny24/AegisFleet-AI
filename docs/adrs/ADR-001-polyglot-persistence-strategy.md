# ADR-001: Polyglot Persistence Architecture for 100K Telemetry Scale

## Status
Accepted

## Context
A fleet of 100,000 connected vehicles generates ~100,000 events/second (~8.6 TB/day). Writing this volume directly into a single relational database causes write amplification, B-tree index contention, and lock starvation on transactional queries. Conversely, a pure NoSQL store lacks ACID guarantees needed for fleet subscriptions, vehicle ownership, billing, and work orders.

## Options Considered
1. **Single Monolithic PostgreSQL Instance**: Inadequate write throughput at 100K events/sec; B-tree write amplification collapses query responsiveness.
2. **Pure MongoDB / Cassandra Store**: High write throughput, but lacks relational integrity and foreign-key consistency required for billing, maintenance audits, and multi-tenant isolation.
3. **Polyglot Hybrid Architecture (Selected)**:
   - **PostgreSQL (3NF Core)**: Fleets, Vehicles, Drivers, DTC Catalog, Alerts, Work Orders, and Compliance Audit Logs.
   - **Redis (In-Memory Hot Layer)**: Live vehicle position cache, geohashing, Bloom Filter deduplication bitsets.
   - **TimescaleDB / Parquet Cold Storage**: Hypertable-partitioned long-term telemetry for historical analytics and ML training.

## Decision
Adopt the Polyglot Hybrid Architecture. Relational entities adhere strictly to Third Normal Form (3NF) to prevent anomalies. High-velocity telemetry is ingested asynchronously into Redis and compressed partitioned blocks.

## Consequences
- **Positive**: Write latency reduced to <5ms; read queries for dashboard alerts execute in <3ms using composite indexes.
- **Negative**: Requires operational maintenance of two storage engines and careful cache invalidation.
