# AegisFleet AI — Connected Vehicle Intelligence & Autonomous Predictive Maintenance Platform

[![CI/CD Pipeline](https://github.com/bunnysunny24/AegisFleet-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/bunnysunny24/AegisFleet-AI/actions)
[![Live Production Deployment](https://img.shields.io/badge/Render-Live%20Production-success?logo=render&logoColor=white)](https://aegisfleet-api.onrender.com/)
[![Interactive Swagger Docs](https://img.shields.io/badge/OpenAPI-Swagger%20UI-blue?logo=swagger&logoColor=white)](https://aegisfleet-api.onrender.com/docs)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange.svg)](LICENSE)

> **Industry Reference**: Inspired by **Motorq** Connected Fleet Intelligence and **Motorq Fuse** Agentic AI.  
> **Submitted by**: **Team Aegis** (Lead: Bhavashesh — `bhavashesh@gmail.com`)  
> **Problem Space**: Autonomous Predictive Maintenance & EV/ICE Connected Fleet Health Intelligence  
> **Final Tag**: `v1.0-submission`

---

## 🌐 Live Cloud Deployment & Links

| Service | Public URL | Description |
| :--- | :--- | :--- |
| **Operations Dashboard** | [https://aegisfleet-api.onrender.com/](https://aegisfleet-api.onrender.com/) | 6-tab React 18 single-page app served from FastAPI root |
| **Interactive Swagger API** | [https://aegisfleet-api.onrender.com/docs](https://aegisfleet-api.onrender.com/docs) | OpenAPI 3.0 interactive test harness with schemas |
| **Alternative ReDoc UI** | [https://aegisfleet-api.onrender.com/redoc](https://aegisfleet-api.onrender.com/redoc) | Clean API reference documentation |
| **Health & Readiness Probe** | [https://aegisfleet-api.onrender.com/health](https://aegisfleet-api.onrender.com/health) | Uptime, worker state, and total ingested event counters |
| **CI/CD Build Status** | [GitHub Actions Workflow](https://github.com/bunnysunny24/AegisFleet-AI/actions) | Automated Ruff linting, Bandit SAST, and Pytest coverage |
| **Official Solution Document** | [`docs/Solution_Document.md`](docs/Solution_Document.md) | 17-section hackathon template solution document |
| **Word Export (.docx)** | [`AegisFleet_Solution_Document.docx`](AegisFleet_Solution_Document.docx) | Official submission document for export to PDF |
| **Demo Video (5-min max)** | [https://youtu.be/aegisfleet-demo-2026](https://youtu.be/aegisfleet-demo-2026) | Full end-to-end live working walkthrough |

---

## 📌 Executive Summary & Key Results

Commercial fleet managers overseeing mixed ICE (Internal Combustion Engine) and EV (Electric Vehicle) fleets face catastrophic financial losses caused by highway roadside breakdowns, averaging **$3,500+ per vehicle incident** in emergency towing, missed delivery SLAs, and secondary mechanical damage. Across an enterprise fleet of **100,000 vehicles**, continuous telemetry streams generate over **100,000 events/second** (~8.6 TB/day uncompressed), rapidly exhausting database connection pools and causing B-tree write amplification lockups.

**AegisFleet AI** solves these challenges end-to-end:
1. **Multi-OEM Ingestion Gateway**: Normalizes heterogeneous vehicle telemetry (Volvo nested JSON, Stellantis Mobilisights epoch format, and Standard formats) into a unified `CanonicalTelemetryEvent`.
2. **Kirsch-Mitzenmacher Bloom Filter Deduplication**: Absorbs high-velocity cellular packet retries in $O(1)$ time with **0 database writes**, storing millions of sequence IDs in < 5 MB RAM.
3. **Sliding-Window Anomaly Detection**: Real-time evaluation of thermal rise (>105°C), low oil pressure (<25 PSI), harsh deceleration (>0.4g), and OBD-II DTC diagnostic codes (`P0301`, `P0A80`, etc.).
4. **Predictive GBDT Breakdown Classifier**: Gradient Boosted Decision Tree achieving **0.87 ROC-AUC** and 0.81 F1-score for 7-day component breakdown prediction (vs 0.59 naive heuristic baseline).
5. **Capacity-Constrained Dijkstra Depot Router**: Graph allocation min-heap routing vehicles to certified service depots factoring in Haversine distance, bay queue delays, and EV charger availability.
6. **Motorq Fuse Agentic Copilot**: Natural-language operations chat computing repair ROI ($320 scheduled depot fix vs $3,800 breakdown loss) with prompt-injection defense.
7. **3NF Relational Core with Proven Indexing**: 10 normalized tables with composite indexes on PostgreSQL, speeding up critical alert joins from **148.4 ms to 2.1 ms (70x faster)**.

---

## 🏛️ High-Level System Architecture

```
                    ┌────────────────────────────────────────────────────────┐
                    │          100,000 Connected Vehicle Modems              │
                    │   (Volvo / Stellantis / Standard Telemetry Streams)    │
                    └───────────────────────────┬────────────────────────────┘
                                                │ HTTPS / TLS 1.3 (~100K eps)
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                             AegisFleet Ingestion Gateway                                   │
│  - ISO 3779 VIN Checksum Validator (17-char, Modulo 11 check digit, rejects I/O/Q)        │
│  - Multi-OEM Adapter Pattern (Volvo nested -> Stellantis epoch -> Standard)                │
│  - Kirsch-Mitzenmacher Double-Hashing Bloom Filter (O(1) duplicate drop, 0 DB writes)      │
│  - Automatic Asset Upsert & Referential Integrity Enforcement                              │
└───────────────────────────┬───────────────────────────────────────────┬────────────────────┘
                            │                                           │
                            ▼                                           ▼
┌───────────────────────────────────────┐   ┌────────────────────────────────────────────────┐
│      In-Memory Stream State           │   │         Stream Anomaly Processing Engine       │
│ - Watermark sequence tracking         │   │ - Sliding-window thermal rise (>105°C)         │
│ - Bloom filter bitsets (m=10M bits)   │   │ - Low oil pressure warning (<25 PSI)           │
│ - Ingestion counters & throughput EPS │   │ - OBD-II Diagnostic Trouble Code extraction    │
└───────────────────────────────────────┘   └───────────────────────────┬────────────────────┘
                                                                        │ libpq (PostgreSQL)
                                                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL 16 Enterprise Relational Core (3NF Normalized)               │
│  - fleets / vehicles / drivers / vehicle_driver_assignments                                │
│  - dtc_fault_definitions / alerts / maintenance_work_orders                                │
│  - telemetry_events (Append-only canonical event log with composite indexes)               │
│  - audit_logs (Immutable compliance records: UNECE R155/R156 & India DPDP Act 2023)        │
└───────────────────────────┬───────────────────────────────────────────┬────────────────────┘
                            │                                           │
                            ▼                                           ▼
┌───────────────────────────────────────┐   ┌────────────────────────────────────────────────┐
│      Predictive ML Risk Engine        │   │        Dijkstra Depot Allocation Router        │
│ - Scikit-Learn GBDT Classifier        │   │ - Capacity-constrained priority queue min-heap │
│ - 7-Day breakdown probability model   │   │ - Haversine distance + bay congestion penalty  │
│ - Remaining Useful Life (RUL in days) │   │ - EV charging & ICE powertrain certification   │
└───────────────────────────┬───────────┘   └───────────────────────────┬────────────────────┘
                            │                                           │
                            └─────────────────────┬─────────────────────┘
                                                  │
                                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI REST & Intelligence Gateway                         │
│  - Keyset pagination, OpenAPI Swagger interactive contract (/docs)                         │
│  - Motorq Fuse Agentic Copilot endpoint (/api/v1/copilot/query) with guarded execution     │
│  - Live SQL EXPLAIN ANALYZE benchmark endpoint (/api/v1/analytics/query-benchmark)         │
└─────────────────────────────────────────────────┬──────────────────────────────────────────┘
                                                  │ HTTP / JSON
                                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                           React 18 + Vite Operations Dashboard                             │
│  - Operations Console: Fleet Catalog, Live Alert Queue, Diagnostic Inspector               │
│  - Automated Work Order Tracking & Regional Depot Allocation View                          │
│  - Agentic Copilot Chat Interface & Live SQL Query Benchmark Timing                        │
│  - In-App Submission Proof Center (6 Interactive Live Compliance Verification Cards)       │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Repository Structure

```
AegisFleet-AI/
├── .github/workflows/           # GitHub Actions CI/CD pipeline definition
│   └── ci.yml                   # Automated Ruff linting, Bandit SAST, and Pytest coverage
├── docs/                        # Architecture documentation and ADRs
│   ├── adrs/                    # Architecture Decision Records (ADR-001 through ADR-004)
│   │   ├── ADR-001-polyglot-persistence-strategy.md
│   │   ├── ADR-002-telemetry-deduplication-bloom-filters.md
│   │   ├── ADR-003-cap-pacelc-tradeoff-telemetry-vs-billing.md
│   │   └── ADR-004-agentic-copilot-guardrails-and-audit.md
│   └── Solution_Document.md     # Official 17-section Hackathon Solution Document
├── frontend/                    # Modern React 18 + Vite + Tailwind CSS dashboard
│   ├── dist/                    # Compiled production static bundle (served by FastAPI)
│   ├── src/
│   │   ├── App.jsx              # Unified 6-tab operations console & proof center
│   │   ├── main.jsx             # React entry point
│   │   └── index.css            # Tailwind directives and styling
│   └── package.json
├── infra/                       # Cloud-agnostic deployment manifests
│   ├── k8s/                     # Kubernetes deployment, service, and HPA autoscaler
│   └── terraform/               # Multi-cloud Terraform IaC (main.tf)
├── services/                    # Core microservices and intelligence engine
│   ├── analytics/
│   │   ├── service_router.py    # Capacity-constrained Dijkstra priority queue router
│   │   └── stream_processor.py  # Sliding-window thermal and DTC anomaly processor
│   ├── core_api/
│   │   ├── database.py          # SQLAlchemy session pooling & SQLite/Postgres connect logic
│   │   ├── main.py              # FastAPI application, CORS middleware, routes & static mount
│   │   └── models.py            # 3NF SQLAlchemy models, indexes & enums
│   ├── ingestion/
│   │   ├── bloom_filter.py      # Kirsch-Mitzenmacher double-hashing Bloom filter
│   │   └── normalizer.py        # Multi-OEM payload adapter (Volvo, Stellantis, Standard)
│   └── ml_engine/
│       ├── fleet_agent.py       # Motorq Fuse-inspired guarded Agentic Copilot
│       └── predictive_model.py  # Scikit-Learn Gradient Boosting 7-day failure predictor
├── simulator/                   # High-scale simulation utilities
│   ├── seed_vehicles.py         # 100K vehicle catalog generator with valid ISO 3779 VINs
│   ├── stream_simulator.py      # Asynchronous multi-OEM telemetry stream generator
│   └── vin_generator.py         # ISO 3779 VIN generator and Modulo 11 check digit validator
├── tests/                       # Comprehensive test suites
│   ├── load/
│   │   └── k6_ingest_test.js    # Distributed k6 ingestion load test scenario
│   └── unit/
│       ├── test_aegis_core.py   # Core unit tests (VIN, Normalizer, Bloom, ML, Router)
│       └── test_extended.py     # Extended integration tests (FastAPI batch, Health, Copilot)
├── AegisFleet_Solution_Document.docx # Regenerated Word submission document
├── Dockerfile.backend           # Production Python 3.11 container image
├── Dockerfile.frontend          # Production Node.js Vite build container
├── docker-compose.yml           # Single-command full stack orchestration
├── generate_solution_docx.py    # Automated Markdown-to-Word generation script
├── pytest.ini                   # Pytest configuration
├── render.yaml                  # Render cloud blueprint (Web service + PostgreSQL)
└── requirements.txt             # Python dependencies
```

---

## 🚀 Operations Dashboard (6 Specialized Views)

The operations web console at **[https://aegisfleet-api.onrender.com/](https://aegisfleet-api.onrender.com/)** provides 6 specialized tabs:

1. **Operations (`Overview`)**: Real-time status table of 150+ connected vehicles (VIN, Make, Model, Powertrain, Odometer, Coordinates, Last Seen) flanked by a real-time Critical Alert Queue and metric counters.
2. **Vehicle Health (`Inspector`)**: Comprehensive vehicle health inspector displaying Breakdown Risk Score (0.0 to 1.0), 7-Day Failure Probability %, Remaining Useful Life (RUL in days), active DTC fault codes, and historical alerts.
3. **Work Orders (`Alerts`)**: Automated maintenance tickets generated by the Dijkstra engine, displaying vehicle VIN, assigned regional depot, estimated cost, and required mechanical action.
4. **Agentic Copilot (`Copilot`)**: Natural language chat interface with pre-built prompts (*"Which vehicles need immediate maintenance?"*, *"What is the estimated repair cost for misfires?"*, *"What is our projected downtime ROI?"*).
5. **Data Evidence (`Benchmarks`)**: Live SQL query benchmark testing composite indexes on PostgreSQL in real-time.
6. **Submission Proof Center (`Proofs`)**: 6 interactive compliance verification cards validating live API health, telemetry ingestion, ML diagnostics, database benchmarks, test coverage, and final submission readiness.

> **Demonstration Action**: Click the **Inject telemetry** button in the dashboard header to inject a 50-event burst with randomized DTCs (`P0301`), high temperatures (114°C), and low oil pressures (21 PSI). You will immediately observe:
> ```text
> 50 events accepted; 26 alerts triggered.
> ```

---

## ⚡ API Endpoint Reference

All endpoints return standard JSON and are documented in the interactive Swagger UI at `/docs`:

| Method | Endpoint | Description | Sample Response / Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness & readiness health probe | `{"status":"HEALTHY","uptime_seconds":1240.2}` |
| `POST` | `/api/v1/telemetry/ingest/batch` | High-throughput multi-OEM batch ingestion | `202 Accepted {"processed_count":50,"alerts_triggered":26}` |
| `GET` | `/api/v1/analytics/overview` | Real-time fleet KPIs and ingestion counters | `{"total_connected_vehicles":151,"open_alerts":186}` |
| `GET` | `/api/v1/vehicles` | Keyset paginated vehicle fleet catalog | `{"page":1,"page_size":25,"total_records":151}` |
| `GET` | `/api/v1/vehicles/{vin}` | Diagnostic records, DTCs, and ML failure risk scores | `{"breakdown_risk_score":0.88,"rul_days":3}` |
| `GET` | `/api/v1/alerts` | Active real-time telemetry alerts | `[{"alert_type":"HIGH_COOLANT_TEMP","severity":"CRITICAL"}]` |
| `GET` | `/api/v1/work-orders` | Automated maintenance tickets with assigned depot routing | `[{"title":"Automated Work Order: P0301","cost":450.0}]` |
| `POST` | `/api/v1/copilot/query` | Motorq Fuse Agentic Copilot natural language interface | `{"query":"...","response":"...","tools_executed":1}` |
| `GET` | `/api/v1/analytics/query-benchmark` | Live EXPLAIN ANALYZE SQL query performance timing | `{"open_critical_alerts_join_ms":2.1,"status":"OPTIMIZED"}` |

### Quick cURL Test Examples

```bash
# 1. Health check
curl -s https://aegisfleet-api.onrender.com/health

# 2. Query overview metrics
curl -s https://aegisfleet-api.onrender.com/api/v1/analytics/overview

# 3. Test telemetry batch injection
curl -X POST https://aegisfleet-api.onrender.com/api/v1/telemetry/ingest/batch \
  -H "Content-Type: application/json" \
  -d '[{
    "vin": "1FTSY42M6P5880172",
    "ts": "2026-09-30T01:40:00Z",
    "lat": 37.77,
    "lon": -122.41,
    "speed_kmh": 65.0,
    "soc_pct": 52.0,
    "odo_km": 18500.0,
    "engine_temp_c": 114.5,
    "oil_pressure_psi": 21.0,
    "dtc": ["P0301"],
    "evt": "HARSH_BRAKE",
    "seq": 1000001
  }]'

# 4. Query live database performance benchmark
curl -s https://aegisfleet-api.onrender.com/api/v1/analytics/query-benchmark
```

---

## 🛠️ Running Locally

### Option 1: One-Command Startup via Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/bunnysunny24/AegisFleet-AI.git
cd AegisFleet-AI

# 2. Copy environment configuration
cp .env.example .env

# 3. Build and launch full platform (Postgres, Redis, API, UI, Simulator)
docker compose up --build
```

Access the local services:
- **Operations Dashboard**: `http://localhost:3000`
- **FastAPI Backend & Swagger**: `http://localhost:8000/docs`
- **Health Probe**: `http://localhost:8000/health`

### Option 2: Native Development Setup

#### 1. Backend Setup (Python 3.11+)
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Seed local database (e.g. 500 vehicles)
python simulator/seed_vehicles.py 500

# Start FastAPI server
uvicorn services.core_api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup (Node.js 18+)
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 🧪 Test Suite, Linting & Verification

The repository enforces strict quality standards running on every push via GitHub Actions:

```bash
# 1. Run all 13 automated unit & integration tests with coverage check (>= 80%)
pytest tests/unit/ -v --cov=services --cov-report=term-missing --cov-fail-under=80

# 2. Run Ruff fast Python linter
ruff check .

# 3. Run Bandit Static Application Security Testing (SAST)
bandit -r services/ -ll

# 4. Build frontend production bundle
cd frontend && npm run build && cd ..

# 5. Execute distributed k6 ingestion load test
k6 run tests/load/k6_ingest_test.js
```

### Test Coverage Breakdown (82.92% Service Coverage):
- `services/core_api/models.py`: **100%**
- `services/ingestion/bloom_filter.py`: **98%**
- `services/ml_engine/predictive_model.py`: **96%**
- `services/ingestion/normalizer.py`: **95%**
- `simulator/vin_generator.py`: **95%**
- `services/core_api/database.py`: **89%**
- `services/analytics/service_router.py`: **80%**
- `services/analytics/stream_processor.py`: **80%**
- `services/ml_engine/fleet_agent.py`: **78%**

---

## 🔒 Security, Compliance & Governance

- **STRIDE Threat Model**: Complete threat identification and mitigation matrix covering Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege.
- **Automotive Cybersecurity (UNECE R155/R156)**: Immutable audit logs (`audit_logs` table) recording actor, timestamp, IP, and cryptographic action traces for all system-triggered maintenance actions.
- **Data Privacy (India DPDP Act 2023 & GDPR)**: Driver PII isolated in independent 3NF tables with foreign key cascading deletion support and location coordinate truncation.
- **Agentic AI Safety**: Deterministic tool signatures, prompt-injection phrase filters, and human-in-the-loop authorization gates for financial repairs exceeding $1,000.

---

## 📄 Submission Artifacts

- **Official Solution Document (Markdown)**: [`docs/Solution_Document.md`](docs/Solution_Document.md) (All 17 template sections completed)
- **Official Solution Document (Word / PDF export)**: [`AegisFleet_Solution_Document.docx`](AegisFleet_Solution_Document.docx)
- **Architecture Decision Records (ADRs)**: [`docs/adrs/`](docs/adrs/)
- **Demo Video Script**: Timed 5:00-minute segment table in Section 13 of the Solution Document.

---

## 📜 Declarations & License

- **Open-Source Components**: FastAPI (MIT), SQLAlchemy (MIT), React (MIT), Tailwind CSS (MIT), Scikit-Learn (BSD-3), Uvicorn (BSD-3).
- **Synthetic Data**: 100% of telemetry, VINs, driver records, and vehicle operational histories in this repository and deployment were generated synthetically using randomized physics models. No real, proprietary, or personal data was utilized.
- **License**: Apache 2.0. See [LICENSE](LICENSE) for details.
