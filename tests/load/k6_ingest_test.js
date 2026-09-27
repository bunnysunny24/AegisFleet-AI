import http from 'k6/http';
import { check, sleep } from 'k6';

// k6 Load Test Configuration per Section 11 & 12:
// Simulates sustained throughput and 3x burst traffic spikes up to 100,000 events/sec
export const options = {
  stages: [
    { duration: '30s', target: 50 },    // Warm up: Ramp to 50 concurrent virtual users
    { duration: '1m', target: 200 },    // Sustained load: 200 VUs (~25,000 - 50,000 events/min)
    { duration: '30s', target: 600 },   // 3x Burst spike (Shift change / network recovery)
    { duration: '1m', target: 600 },    // Sustained 3x burst
    { duration: '30s', target: 50 },    // Ramp down
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<200', 'p(99)<500'], // Case study NFR: API p95 < 200ms, p99 < 500ms
    http_req_failed: ['rate<0.001'],               // < 0.1% error rate (99.9% availability)
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

export default function () {
  const batchSize = 25;
  const batch = [];

  for (let i = 0; i < batchSize; i++) {
    batch.push({
      vin: `1HGCM82633A0043${Math.floor(Math.random() * 90 + 10)}`,
      ts: new Date().toISOString(),
      lat: 37.7749 + (Math.random() - 0.5) * 0.2,
      lon: -122.4194 + (Math.random() - 0.5) * 0.2,
      speed_kmh: Math.floor(Math.random() * 110),
      soc_pct: Math.floor(Math.random() * 85 + 15),
      odo_km: 15420.5 + i,
      engine_temp_c: 90.0 + (Math.random() * 20),
      oil_pressure_psi: 42.0 + (Math.random() * 10),
      dtc: Math.random() < 0.05 ? ['P0301'] : [],
      evt: 'PERIODIC_HEARTBEAT',
      seq: Math.floor(Math.random() * 100000),
    });
  }

  const payload = JSON.stringify(batch);
  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(`${BASE_URL}/api/v1/telemetry/ingest/batch`, payload, params);

  check(res, {
    'status is 202': (r) => r.status === 202,
    'latency under 200ms': (r) => r.timings.duration < 200,
  });

  sleep(0.05); // Rapid streaming interval
}
