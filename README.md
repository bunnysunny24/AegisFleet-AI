# AegisFleet AI

Connected-vehicle operations prototype for fleet telemetry ingestion, anomaly detection, predictive diagnostics, maintenance routing, and an operator dashboard.

[Live application](https://aegisfleet-api.onrender.com/) | [API documentation](https://aegisfleet-api.onrender.com/docs) | [Health endpoint](https://aegisfleet-api.onrender.com/health) | [CI workflow](https://github.com/bunnysunny24/AegisFleet-AI/actions)

## What this project demonstrates

AegisFleet receives normalized telemetry from simulated vehicles, validates and deduplicates events, stores the accepted telemetry history, detects operational anomalies, and exposes the results to a React operations dashboard. Critical alerts can create a maintenance work order and select a compatible service centre using a Dijkstra-based router.

All vehicle and telemetry data in this repository is synthetic.

## Implementation at a glance

```text
Simulator / API client
        |
        v
FastAPI batch ingestion endpoint
        |
        +-- OEM normalizers -> canonical telemetry event
        +-- VIN validation + Bloom-filter duplicate pre-filter
        +-- stream anomaly rules + sequence checks
        |
        v
SQLAlchemy relational store (SQLite locally / PostgreSQL in Compose)
        |
        +-- vehicle current state and append-only telemetry history
        +-- alerts, work orders, service centres, audit records
        |
        v
React operations UI + FastAPI OpenAPI documentation
```

The application uses HTTP request/response APIs and in-process stream state. Redis, Kafka, a vector database, and WebSocket transport are not part of the running implementation; they remain scale-out design options rather than features to claim as delivered.

## Features and where they live

| Capability | Implementation |
| --- | --- |
| Multi-OEM telemetry adaptation | `services/ingestion/normalizer.py` converts Volvo, Stellantis, and standard payload shapes to a canonical event. |
| VIN validation | `simulator/vin_generator.py` creates and validates 17-character VIN check digits. |
| Duplicate and sequence handling | `services/ingestion/bloom_filter.py` and `services/analytics/stream_processor.py` pre-filter duplicate event IDs and record out-of-order sequence signals. |
| Persistent telemetry | `services/core_api/models.py` defines `TelemetryEvent`; accepted events are appended by `services/core_api/main.py`. |
| Anomaly detection | `services/analytics/stream_processor.py` evaluates DTC, thermal, pressure, and harsh-event conditions. |
| Work-order routing | `services/analytics/service_router.py` chooses a compatible service centre while considering location and capacity. |
| Predictive diagnostics | `services/ml_engine/predictive_model.py` supplies a breakdown-risk and remaining-useful-life estimate. |
| Guarded copilot | `services/ml_engine/fleet_agent.py` exposes selected diagnostic and fleet tools through `/api/v1/copilot/query` and writes audit records. |
| Dashboard | `frontend/src/App.jsx` reads the live API for KPIs, fleet records, alerts, work orders, vehicle diagnostics, copilot results, and query measurements. |

## Dashboard behaviour

The UI intentionally has no fabricated loading values. Until the API answers, metrics show `--`; if it cannot be reached, the header reports that state. The dashboard polls the API every 10 seconds and supports a manual refresh.

The **Inject telemetry** control sends a 50-event batch to the currently selected VIN. This is a demonstrator control: it causes the normal ingestion, persistence, anomaly, alert, and work-order path to run. It does not constitute a 100,000 events-per-second benchmark.

The **Data evidence** screen renders timing values returned by `/api/v1/analytics/query-benchmark` at request time. It does not display invented before/after results.

## API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness check. |
| `POST /api/v1/telemetry/ingest/batch` | Validate, process, persist, and score a batch of telemetry events. |
| `GET /api/v1/vehicles` | Paginated fleet catalog with filters. |
| `GET /api/v1/vehicles/{vin}` | Vehicle diagnostics, recent alerts, and predictive-risk response. |
| `GET /api/v1/alerts` | Open alert queue, optionally filtered. |
| `GET /api/v1/work-orders` | Generated maintenance work orders. |
| `GET /api/v1/analytics/overview` | Live dashboard totals and in-process ingestion counters. |
| `GET /api/v1/analytics/query-benchmark` | Current measured SQL-query timings and configured optimization descriptions. |
| `POST /api/v1/copilot/query` | Copilot query using a guarded set of fleet tools. |

The full OpenAPI contract is served by FastAPI at `/docs` when the API is running.

## Run locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop, for the Compose path

### Application with Docker Compose

```powershell
Copy-Item .env.example .env
# Set POSTGRES_PASSWORD in .env to a non-default local secret.
docker compose up --build
```

Open:

- Dashboard: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

Compose seeds the catalog according to `SEED_VEHICLE_COUNT` (default: `100000`) and starts the simulator using `SIMULATOR_EPS` (default: `1000`). Reduce these for a quick laptop demo.

### Backend and frontend development

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python simulator/seed_vehicles.py 1000

cd frontend
npm install
npm run dev
```

The Vite development server prints its local URL. Configure `VITE_API_BASE` when the frontend should talk to an API on a different origin.

## Verification

Run the checks from the repository root:

```powershell
.\.venv\Scripts\pytest.exe tests\unit -q --cov=services --cov-fail-under=80
.\.venv\Scripts\ruff.exe check services simulator tests

cd frontend
npm run build
cd ..

docker compose config -q
```

The last local verification before this UI refresh reported 13 passing unit tests, 83.88% service coverage, a clean Ruff result, a successful Vite production build, and a valid Compose configuration. The GitHub Actions workflow runs the repository's configured checks for each push.

### Load test target

`tests/load/k6_ingest_test.js` holds the k6 scenario for the requested sustained-ingestion and burst exercise:

```powershell
k6 run tests/load/k6_ingest_test.js
```

Capture the k6 output and environment details before claiming any throughput or latency result. The repository currently defines a 100,000-event-per-second target; it does not contain a reproducible 100,000 EPS proof run.

## Project layout

```text
services/
  core_api/        FastAPI routes, SQLAlchemy models, database setup
  ingestion/       OEM payload normalizers and Bloom filter
  analytics/       Stream anomaly rules and service-centre router
  ml_engine/       Predictive-risk helper and copilot implementation
simulator/         VIN generator, catalog seeder, event stream generator
frontend/          React + Vite + Tailwind operations dashboard
tests/unit/        Unit and integration-oriented API tests
tests/load/        k6 load-test scenario
docs/              ADRs and the written solution-document source
infra/             Docker, Kubernetes manifests, and Terraform blueprint
```

## Architecture decisions

- [Telemetry deduplication](docs/adrs/ADR-002-telemetry-deduplication-bloom-filters.md)
- [Consistency and availability trade-offs](docs/adrs/ADR-003-cap-pacelc-tradeoff-telemetry-vs-billing.md)
- [Copilot guardrails and audit trail](docs/adrs/ADR-004-agentic-copilot-guardrails-and-audit.md)
- [Persistence strategy](docs/adrs/ADR-001-polyglot-persistence-strategy.md)

Some ADRs describe a future scale-out architecture. Treat the source code and this README's implementation notes as the authoritative record of currently executable behaviour.

## Submission evidence checklist

For the hackathon package, include these artifacts alongside the repository:

- The completed solution document rendered to PDF from `AegisFleet_Solution_Document.docx`.
- A 5-minute-or-shorter demo video showing health, telemetry injection, alert/work-order creation, vehicle diagnostics, API docs, and test results.
- A recorded k6 result if throughput or latency is claimed.
- The deployed URL and a screenshot or recording made after the final GitHub deployment completes.

## Scope and limits

This is a working prototype, not a production-certified fleet platform. It does not yet provide distributed event streaming, durable shared deduplication state, user authentication/RBAC, rate limiting, mTLS, a vector store, or a completed high-scale performance proof. The availability, p95/p99 latency, and 100,000 EPS requirements are therefore objectives to test and document, not achieved metrics.

## Demo sequence

1. Open `/health` and `/docs` to establish that the API is reachable and inspect the contract.
2. Open the dashboard and select a vehicle from the fleet catalog.
3. Use **Inject telemetry**, then refresh the operations view.
4. Inspect an alert and the corresponding vehicle health record.
5. Show the work-order queue and the current query-evidence view.
6. Run the unit tests and frontend build; show the output in the recording.

## License

Apache-2.0. See [LICENSE](LICENSE).
