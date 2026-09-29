import React, { useEffect, useState } from 'react';
import {
  Activity, AlertTriangle, Bot, CheckCircle2, CircleAlert, Cpu, Database,
  Gauge, RefreshCw, Search, Send, ShieldCheck, Sparkles, Truck, Wrench, Zap
} from 'lucide-react';

const rawApi = import.meta.env.VITE_API_BASE || '';
const API_BASE = rawApi ? (rawApi.startsWith('http') ? rawApi : `https://${rawApi}`) : '';
const tabs = [
  ['overview', 'Operations', Activity], ['inspector', 'Vehicle health', Search],
  ['alerts', 'Work orders', Wrench], ['copilot', 'Copilot', Bot], ['benchmarks', 'Data evidence', Database]
];
const number = (value) => Number(value ?? 0).toLocaleString();
const money = (value) => `$${Number(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const vin = (value) => value ? `${value.slice(0, 8)}...${value.slice(-4)}` : '--';
const time = (value) => value ? new Date(value).toLocaleString() : 'No telemetry received';

function Metric({ label, value, detail, Icon, tone = 'text-cyan-300' }) {
  return <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4 shadow-sm">
    <div className="flex items-start justify-between gap-2"><p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">{label}</p><Icon className={`h-4 w-4 ${tone}`} /></div>
    <p className="mt-3 text-2xl font-semibold tabular-nums text-slate-100">{value}</p><p className="mt-1 min-h-4 text-xs text-slate-500">{detail}</p>
  </section>;
}

function Severity({ value }) {
  const critical = String(value).toUpperCase() === 'CRITICAL';
  return <span className={`inline-flex border px-2 py-0.5 text-[10px] font-bold tracking-wide ${critical ? 'border-rose-500/30 bg-rose-500/10 text-rose-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300'}`}>{value || 'UNKNOWN'}</span>;
}

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [vehicles, setVehicles] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [workOrders, setWorkOrders] = useState([]);
  const [benchmarks, setBenchmarks] = useState(null);
  const [selectedVin, setSelectedVin] = useState('');
  const [vehicleDetail, setVehicleDetail] = useState(null);
  const [connection, setConnection] = useState('loading');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [notice, setNotice] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);
  const [copilotInput, setCopilotInput] = useState('');
  const [copilotChat, setCopilotChat] = useState([{ sender: 'agent', text: 'Ask about the selected vehicle or fleet health. I will query the available AegisFleet tools.' }]);

  const refresh = async () => {
    setConnection('loading');
    try {
      const responses = await Promise.all([
        fetch(`${API_BASE}/api/v1/analytics/overview`),
        fetch(`${API_BASE}/api/v1/vehicles?page=1&page_size=15`),
        fetch(`${API_BASE}/api/v1/alerts?limit=20`),
        fetch(`${API_BASE}/api/v1/work-orders?limit=15`),
        fetch(`${API_BASE}/api/v1/analytics/query-benchmark`)
      ]);
      if (responses.some((response) => !response.ok)) throw new Error('Dashboard request failed');
      const [nextOverview, vehiclePage, nextAlerts, nextOrders, nextBenchmarks] = await Promise.all(responses.map((response) => response.json()));
      setOverview(nextOverview); setVehicles(vehiclePage.vehicles || []); setAlerts(nextAlerts || []); setWorkOrders(nextOrders || []); setBenchmarks(nextBenchmarks);
      setSelectedVin((current) => current || vehiclePage.vehicles?.[0]?.vin || '');
      setConnection('connected'); setLastUpdated(new Date());
    } catch (error) { console.warn(error); setConnection('offline'); }
  };

  useEffect(() => { refresh(); const timer = window.setInterval(refresh, 10000); return () => window.clearInterval(timer); }, []);

  const inspect = async (candidate = selectedVin) => {
    const nextVin = candidate.trim().toUpperCase();
    if (!nextVin) { setNotice('Choose a vehicle or enter a VIN before inspecting.'); return; }
    setSelectedVin(nextVin); setVehicleDetail(null);
    try {
      const response = await fetch(`${API_BASE}/api/v1/vehicles/${encodeURIComponent(nextVin)}`);
      if (!response.ok) throw new Error('Not found');
      setVehicleDetail(await response.json()); setActiveTab('inspector'); setNotice('Vehicle diagnostics loaded.');
    } catch { setNotice(`Could not load diagnostics for ${nextVin}.`); }
  };

  const injectTelemetry = async () => {
    if (!selectedVin) { setNotice('Load the fleet catalog first, then select a vehicle.'); return; }
    setIsSimulating(true); setNotice('Submitting a 50-event telemetry burst to the selected vehicle.');
    const events = Array.from({ length: 50 }, (_, index) => ({
      vin: selectedVin, ts: new Date().toISOString(), lat: 37.7749 + (Math.random() - 0.5) * 0.1, lon: -122.4194 + (Math.random() - 0.5) * 0.1,
      speed_kmh: Math.round(45 + Math.random() * 55), soc_pct: Math.round(15 + Math.random() * 75), odo_km: 18450 + index * 2,
      engine_temp_c: index % 5 === 0 ? 114 : 92, oil_pressure_psi: index % 8 === 0 ? 21 : 44,
      dtc: index % 6 === 0 ? ['P0301'] : [], evt: index % 7 === 0 ? 'HARSH_BRAKE' : 'PERIODIC_HEARTBEAT', seq: Date.now() + index
    }));
    try {
      const response = await fetch(`${API_BASE}/api/v1/telemetry/ingest/batch`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(events) });
      if (!response.ok) throw new Error('Ingestion failed');
      const result = await response.json(); setNotice(`${result.processed_count} events accepted; ${result.alerts_triggered} alerts triggered.`); await refresh();
    } catch { setNotice('The telemetry burst could not be sent. Confirm that the API is available.'); } finally { setIsSimulating(false); }
  };

  const sendCopilot = async (event) => {
    event.preventDefault(); const query = copilotInput.trim(); if (!query) return;
    setCopilotChat((items) => [...items, { sender: 'user', text: query }]); setCopilotInput('');
    try {
      const response = await fetch(`${API_BASE}/api/v1/copilot/query`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, vin: selectedVin || null }) });
      if (!response.ok) throw new Error('Copilot request failed'); const data = await response.json();
      setCopilotChat((items) => [...items, { sender: 'agent', text: data.response, toolData: data.tool_data }]);
    } catch { setCopilotChat((items) => [...items, { sender: 'agent', text: 'The copilot request could not reach the API.' }]); }
  };

  const risk = vehicleDetail?.predictive_risk;
  const statusClass = connection === 'connected' ? 'bg-emerald-400' : connection === 'offline' ? 'bg-rose-400' : 'animate-pulse bg-amber-400';
  const statusText = connection === 'connected' ? 'API connected' : connection === 'offline' ? 'API unavailable' : 'Checking API';

  return <div className="min-h-screen bg-[#08111d] text-slate-100">
    <header className="sticky top-0 z-30 border-b border-slate-800 bg-[#08111d]/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-3"><div className="grid h-9 w-9 shrink-0 place-items-center border border-cyan-400/40 bg-cyan-400/10 text-cyan-300"><Cpu className="h-5 w-5" /></div><div className="min-w-0"><h1 className="truncate text-base font-semibold tracking-wide text-white">AegisFleet <span className="text-cyan-300">AI</span></h1><p className="hidden text-xs text-slate-500 sm:block">Connected vehicle operations</p></div></div>
        <div className="flex items-center gap-2"><span className="hidden items-center gap-2 border border-slate-800 bg-slate-900 px-2.5 py-1.5 text-[11px] text-slate-400 sm:inline-flex"><i className={`h-1.5 w-1.5 ${statusClass}`} />{statusText}</span><button title="Refresh dashboard" onClick={refresh} className="grid h-8 w-8 place-items-center border border-slate-700 text-slate-300 hover:border-cyan-400 hover:text-cyan-300"><RefreshCw className="h-4 w-4" /></button><button onClick={injectTelemetry} disabled={isSimulating} className="inline-flex h-8 items-center gap-2 bg-cyan-300 px-3 text-xs font-bold text-slate-950 hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"><Zap className="h-3.5 w-3.5" />{isSimulating ? 'Sending...' : 'Inject telemetry'}</button></div>
      </div>
      <nav className="mx-auto flex max-w-[1440px] overflow-x-auto px-4 sm:px-6" aria-label="Application sections">{tabs.map(([id, label, Icon]) => <button key={id} onClick={() => setActiveTab(id)} className={`inline-flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-xs font-semibold ${activeTab === id ? 'border-cyan-300 text-cyan-300' : 'border-transparent text-slate-500 hover:text-slate-200'}`}><Icon className="h-3.5 w-3.5" />{label}</button>)}</nav>
    </header>
    {notice && <div className="border-b border-cyan-400/20 bg-cyan-400/5"><div className="mx-auto flex max-w-[1440px] items-center justify-between gap-3 px-4 py-2 text-xs text-cyan-100 sm:px-6"><span>{notice}</span><button title="Dismiss message" onClick={() => setNotice('')} className="text-cyan-300 hover:text-white">Close</button></div></div>}
    <main className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-cyan-300">Fleet control room</p><h2 className="mt-1 text-xl font-semibold text-white">Live operations</h2></div><p className="text-xs text-slate-500">Last refresh: {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Waiting for API'}</p></div>
      <section className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5"><Metric label="Fleet catalog" value={overview ? number(overview.total_connected_vehicles) : '--'} detail="Vehicles in the current database" Icon={Truck} /><Metric label="Events accepted" value={overview ? number(overview.telemetry_stream.total_ingested) : '--'} detail={overview ? `${overview.telemetry_stream.current_eps} events/sec since start` : 'Waiting for telemetry'} Icon={Activity} tone="text-emerald-300" /><Metric label="Open alerts" value={overview ? number(overview.open_alerts) : '--'} detail={overview ? `${overview.critical_alerts} critical` : 'Waiting for alerts'} Icon={CircleAlert} tone="text-amber-300" /><Metric label="Pending orders" value={overview ? number(overview.pending_work_orders) : '--'} detail="Auto-created for critical events" Icon={Wrench} tone="text-violet-300" /><Metric label="Projected savings" value={overview ? money(overview.projected_cost_savings_usd) : '--'} detail="Rule-based estimate from open work" Icon={Gauge} tone="text-emerald-300" /></section>

      {activeTab === 'overview' && <section className="grid gap-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(300px,0.9fr)]"><div className="overflow-hidden rounded-md border border-slate-800 bg-slate-900/60"><div className="flex items-center justify-between border-b border-slate-800 px-4 py-3"><div><h3 className="text-sm font-semibold">Fleet catalog</h3><p className="mt-0.5 text-xs text-slate-500">Choose any vehicle to open its diagnostics.</p></div><button onClick={refresh} className="inline-flex items-center gap-1.5 text-xs text-cyan-300 hover:text-cyan-100"><RefreshCw className="h-3.5 w-3.5" />Refresh</button></div><div className="overflow-x-auto"><table className="w-full min-w-[660px] text-left text-xs"><thead className="bg-slate-950/50 text-[10px] uppercase tracking-[0.08em] text-slate-500"><tr><th className="px-4 py-3">VIN</th><th className="px-4 py-3">Vehicle</th><th className="px-4 py-3">Powertrain</th><th className="px-4 py-3">Last update</th><th className="px-4 py-3 text-right">View</th></tr></thead><tbody className="divide-y divide-slate-800">{vehicles.length ? vehicles.map((vehicle) => <tr key={vehicle.vin} className="hover:bg-slate-800/40"><td className="px-4 py-3 font-mono text-cyan-200">{vin(vehicle.vin)}</td><td className="px-4 py-3"><p className="font-medium text-slate-200">{vehicle.make} {vehicle.model}</p><p className="mt-0.5 text-slate-500">{number(vehicle.odometer_km)} km</p></td><td className="px-4 py-3"><span className="border border-slate-700 bg-slate-800 px-1.5 py-0.5 font-semibold text-slate-300">{vehicle.powertrain}</span></td><td className="px-4 py-3 text-slate-400">{time(vehicle.last_seen)}</td><td className="px-4 py-3 text-right"><button onClick={() => inspect(vehicle.vin)} className="border border-slate-700 px-2.5 py-1 font-semibold text-slate-300 hover:border-cyan-300 hover:text-cyan-200">Inspect</button></td></tr>) : <tr><td colSpan="5" className="px-4 py-12 text-center text-slate-500">{connection === 'offline' ? 'The API could not be reached.' : 'Loading fleet catalog...'}</td></tr>}</tbody></table></div></div><div className="rounded-md border border-slate-800 bg-slate-900/60"><div className="flex items-start justify-between border-b border-slate-800 px-4 py-3"><div><h3 className="text-sm font-semibold">Alert queue</h3><p className="mt-0.5 text-xs text-slate-500">Open anomaly detections.</p></div><AlertTriangle className="h-4 w-4 text-amber-300" /></div><div className="max-h-[490px] overflow-auto">{alerts.length ? alerts.map((alert) => <article key={alert.id} className="border-b border-slate-800 p-4 last:border-b-0"><div className="flex items-start justify-between gap-2"><Severity value={alert.severity} /><time className="shrink-0 text-[10px] text-slate-500">{new Date(alert.triggered_at).toLocaleTimeString()}</time></div><p className="mt-2 text-xs font-semibold text-slate-200">{alert.type}</p><p className="mt-1 text-xs leading-5 text-slate-400">{alert.description}</p><button onClick={() => inspect(alert.vin)} className="mt-2 font-mono text-[11px] text-cyan-300 hover:text-cyan-100">{vin(alert.vin)}</button></article>) : <p className="px-4 py-12 text-center text-xs text-slate-500">No open alerts.</p>}</div></div></section>}

      {activeTab === 'inspector' && <section className="space-y-5"><div className="rounded-md border border-slate-800 bg-slate-900/60 p-4"><div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.1em] text-cyan-300">Vehicle diagnostics</p><h3 className="mt-1 font-mono text-lg text-white">{selectedVin || 'Select a vehicle'}</h3><p className="mt-1 text-xs text-slate-500">{vehicleDetail?.make_model || 'No diagnostic record loaded yet.'}</p></div><div className="flex w-full gap-2 md:w-auto"><input aria-label="Vehicle VIN" value={selectedVin} onChange={(event) => setSelectedVin(event.target.value)} placeholder="Enter a VIN" className="min-w-0 flex-1 border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-white outline-none focus:border-cyan-300 md:w-64" /><button onClick={() => inspect()} className="inline-flex shrink-0 items-center gap-2 bg-cyan-300 px-3 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-200"><Search className="h-3.5 w-3.5" />Inspect</button></div></div></div>{vehicleDetail ? <div className="grid gap-5 lg:grid-cols-3"><section className="rounded-md border border-slate-800 bg-slate-900/60 p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">Breakdown risk</p><p className="mt-6 text-5xl font-semibold tabular-nums text-cyan-300">{Math.round((risk?.breakdown_risk_score ?? 0) * 100)}%</p><p className="mt-2 text-sm text-slate-300">{risk?.risk_tier || 'No risk tier returned'}</p><p className="mt-6 border-t border-slate-800 pt-3 text-xs text-slate-500">Estimated remaining useful life: <span className="font-semibold text-slate-200">{risk?.estimated_rul_days ?? '--'} days</span></p></section><section className="rounded-md border border-slate-800 bg-slate-900/60 p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">Current service signal</p><div className="mt-5 space-y-4"><div><p className="text-xs text-slate-500">Vehicle status</p><p className="mt-1 font-semibold text-slate-200">{vehicleDetail.current_status || '--'}</p></div><div><p className="text-xs text-slate-500">Last telemetry</p><p className="mt-1 text-sm text-slate-200">{time(vehicleDetail.last_telemetry_at)}</p></div><div><p className="text-xs text-slate-500">Odometer</p><p className="mt-1 font-semibold text-slate-200">{number(vehicleDetail.odometer_km)} km</p></div></div></section><section className="rounded-md border border-slate-800 bg-slate-900/60 p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">Recent alerts</p><div className="mt-4 space-y-3">{vehicleDetail.recent_alerts?.length ? vehicleDetail.recent_alerts.map((alert) => <div key={alert.id} className="border-l-2 border-amber-300 bg-slate-950/60 px-3 py-2"><p className="text-xs font-semibold text-slate-200">{alert.type}</p><p className="mt-1 text-xs text-slate-500">{alert.description}</p></div>) : <p className="py-5 text-xs text-slate-500">No alerts returned for this vehicle.</p>}</div></section></div> : <div className="rounded-md border border-dashed border-slate-700 bg-slate-900/30 px-5 py-16 text-center"><Truck className="mx-auto h-6 w-6 text-slate-600" /><p className="mt-3 text-sm text-slate-400">Select a fleet record or enter a VIN to load diagnostics.</p></div>}</section>}

      {activeTab === 'alerts' && <section className="overflow-hidden rounded-md border border-slate-800 bg-slate-900/60"><div className="border-b border-slate-800 px-4 py-3"><h3 className="text-sm font-semibold">Maintenance work orders</h3><p className="mt-0.5 text-xs text-slate-500">Work is created when a critical telemetry alert reaches the routing flow.</p></div><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-xs"><thead className="bg-slate-950/50 text-[10px] uppercase tracking-[0.08em] text-slate-500"><tr><th className="px-4 py-3">Order</th><th className="px-4 py-3">Vehicle</th><th className="px-4 py-3">Prescription</th><th className="px-4 py-3">Priority</th><th className="px-4 py-3">Cost</th><th className="px-4 py-3">Status</th></tr></thead><tbody className="divide-y divide-slate-800">{workOrders.length ? workOrders.map((order) => <tr key={order.id}><td className="px-4 py-3 font-mono text-slate-400">{order.id.slice(0, 8)}</td><td className="px-4 py-3"><button onClick={() => inspect(order.vin)} className="font-mono text-cyan-300 hover:text-cyan-100">{vin(order.vin)}</button></td><td className="px-4 py-3"><p className="font-semibold text-slate-200">{order.title}</p><p className="mt-1 max-w-md text-slate-500">{order.action}</p></td><td className="px-4 py-3"><Severity value={order.priority} /></td><td className="px-4 py-3 font-semibold text-slate-200">{money(order.estimated_cost_usd)}</td><td className="px-4 py-3 text-slate-400">{order.status}</td></tr>) : <tr><td colSpan="6" className="px-4 py-14 text-center text-slate-500">No work orders have been generated.</td></tr>}</tbody></table></div></section>}

      {activeTab === 'copilot' && <section className="flex h-[620px] flex-col overflow-hidden rounded-md border border-slate-800 bg-slate-900/60"><div className="flex items-center justify-between border-b border-slate-800 px-4 py-3"><div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-cyan-300" /><div><h3 className="text-sm font-semibold">AegisFleet copilot</h3><p className="mt-0.5 text-xs text-slate-500">Queries use the selected VIN when available.</p></div></div><ShieldCheck className="h-4 w-4 text-emerald-300" /></div><div className="flex-1 space-y-3 overflow-y-auto p-4">{copilotChat.map((message, index) => <article key={index} className={`max-w-3xl border p-3 text-xs leading-5 ${message.sender === 'user' ? 'ml-auto border-cyan-300/30 bg-cyan-300/10 text-cyan-50' : 'border-slate-800 bg-slate-950/50 text-slate-300'}`}><p className="mb-1 text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">{message.sender === 'user' ? 'Operator' : 'Copilot'}</p><p>{message.text}</p>{message.toolData && <pre className="mt-3 overflow-auto border-t border-slate-800 pt-3 text-[10px] text-cyan-200">{JSON.stringify(message.toolData, null, 2)}</pre>}</article>)}</div><form onSubmit={sendCopilot} className="flex gap-2 border-t border-slate-800 p-3"><input value={copilotInput} onChange={(event) => setCopilotInput(event.target.value)} placeholder="Ask about fleet health, risk, or cost impact" className="min-w-0 flex-1 border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-cyan-300" /><button className="grid h-8 w-8 place-items-center bg-cyan-300 text-slate-950 hover:bg-cyan-200" title="Send copilot query"><Send className="h-4 w-4" /></button></form></section>}

      {activeTab === 'benchmarks' && <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]"><div className="rounded-md border border-slate-800 bg-slate-900/60 p-5"><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.1em] text-cyan-300">Live database measurement</p><h3 className="mt-1 text-lg font-semibold">Query evidence</h3><p className="mt-2 text-xs leading-5 text-slate-500">Values are returned by the current query-benchmark endpoint, not hard-coded benchmark claims.</p></div><Database className="h-5 w-5 shrink-0 text-cyan-300" /></div><div className="mt-6 grid gap-3 sm:grid-cols-2"><Metric label="Critical alert join" value={benchmarks ? `${benchmarks.measured_latencies.open_critical_alerts_join_ms} ms` : '--'} detail={`${benchmarks?.rows_returned?.critical_alerts_join_rows ?? '--'} rows returned`} Icon={Activity} /><Metric label="Severity aggregation" value={benchmarks ? `${benchmarks.measured_latencies.severity_aggregation_ms} ms` : '--'} detail={`${benchmarks?.rows_returned?.severity_aggregation_rows ?? '--'} severity groups`} Icon={Database} tone="text-emerald-300" /></div><button onClick={refresh} className="mt-5 inline-flex items-center gap-2 border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-300 hover:border-cyan-300 hover:text-cyan-200"><RefreshCw className="h-3.5 w-3.5" />Measure again</button></div><div className="rounded-md border border-slate-800 bg-slate-900/60 p-5"><p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Indexes configured in the application</p><div className="mt-4 space-y-3">{benchmarks?.optimizations_applied?.length ? benchmarks.optimizations_applied.map((item) => <div key={item} className="flex gap-3 border-b border-slate-800 pb-3 last:border-0"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /><p className="text-xs leading-5 text-slate-300">{item}</p></div>) : <p className="text-xs text-slate-500">Waiting for benchmark data.</p>}</div><div className="mt-5 border border-slate-800 bg-slate-950/60 p-3"><p className="text-[10px] uppercase tracking-[0.08em] text-slate-500">Reported plan</p><p className="mt-2 font-mono text-xs leading-5 text-cyan-200">{benchmarks?.measured_latencies?.explain_analyze_plan || '--'}</p></div></div></section>}
    </main>
  </div>;
}
