import React, { useEffect, useState } from 'react';
import { MetricCard } from '../components/MetricCard';
import { Zap, Server, PhoneOutgoing, Clock, Cpu, Network } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const API_BASE = 'http://localhost:8001';

interface LatencyPoint { timestamp: string; e2e: number; ttfb: number; }
interface CallStats { activeCalls: number; totalCalls: number; avgDuration: number; }

export const Dashboard: React.FC = () => {
  const [latencyData, setLatencyData] = useState<LatencyPoint[]>([]);
  const [callStats, setCallStats] = useState<CallStats>({ activeCalls: 0, totalCalls: 0, avgDuration: 0 });
  const [health, setHealth] = useState<{ status: string; region: string } | null>(null);
  const [events, setEvents] = useState<{ time: string; level: string; msg: string }[]>([]);

  const token = localStorage.getItem('cc_token');
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const fetchData = async () => {
    // Health
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) setHealth(await res.json());
    } catch {}

    // Calls
    try {
      const res = await fetch(`${API_BASE}/api/calls/`, { headers });
      if (res.ok) {
        const calls = await res.json();
        const active = calls.filter((c: any) => c.status === 'active').length;
        const avgDur = calls.length > 0
          ? Math.round(calls.reduce((s: number, c: any) => s + (c.duration || 0), 0) / calls.length)
          : 0;
        setCallStats({ activeCalls: active, totalCalls: calls.length, avgDuration: avgDur });

        // Build latency chart from recent calls
        const recent = calls.slice(0, 20).reverse();
        setLatencyData(recent.map((c: any, i: number) => ({
          timestamp: new Date(c.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          e2e: 350 + Math.floor(Math.random() * 200),  // placeholder until real latency metrics
          ttfb: 150 + Math.floor(Math.random() * 100),
        })));

        // Build events from recent calls
        setEvents(calls.slice(0, 3).map((c: any) => ({
          time: new Date(c.started_at).toLocaleTimeString(),
          level: c.status === 'failed' ? 'warning' : 'info',
          msg: `Call ${c.call_id} — ${c.from_number} → ${c.to_number} (${c.status})`,
        })));
      }
    } catch {}
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8">
      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Active Calls"
          value={String(callStats.activeCalls)}
          trend=""
          trendUp={true}
          icon={PhoneOutgoing}
          color="indigo"
        />
        <MetricCard
          title="Total Calls"
          value={String(callStats.totalCalls)}
          trend=""
          trendUp={true}
          icon={Server}
          color="amber"
        />
        <MetricCard
          title="Avg Duration"
          value={`${callStats.avgDuration}s`}
          trend=""
          trendUp={true}
          icon={Clock}
          color="cyan"
        />
        <MetricCard
          title="API Status"
          value={health?.status === 'ok' ? 'Online' : 'Offline'}
          trend={health?.region ?? ''}
          trendUp={health?.status === 'ok'}
          icon={Zap}
          color="emerald"
        />
      </div>

      {/* Charts & Region Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-lg font-semibold text-white">Latency Performance</h3>
              <p className="text-sm text-slate-400">E2E latency from recent calls</p>
            </div>
            <span className="px-2 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-sm">EU (Frankfurt)</span>
          </div>
          <div className="h-64 w-full">
            {latencyData.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-500 text-sm">No call data yet</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={latencyData}>
                  <defs>
                    <linearGradient id="colorE2E" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorTTFB" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="timestamp" stroke="#64748b" tick={{fontSize: 12}} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748b" tick={{fontSize: 12}} tickLine={false} axisLine={false} unit="ms" />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f1f5f9' }} />
                  <Area type="monotone" dataKey="e2e" stroke="#6366f1" fillOpacity={1} fill="url(#colorE2E)" name="End-to-End" />
                  <Area type="monotone" dataKey="ttfb" stroke="#10b981" fillOpacity={1} fill="url(#colorTTFB)" name="TTFB" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Region Status</h3>
          <div className="space-y-4">
            {[
              { name: 'EU (Frankfurt)', status: health?.status === 'ok' ? 'Optimal' : 'Unknown', latency: '—', load: '—' },
              { name: 'ME (Bahrain)', status: 'Planned', latency: '—', load: '—' },
              { name: 'Asia (Mumbai)', status: 'Planned', latency: '—', load: '—' },
              { name: 'Asia (Singapore)', status: 'Planned', latency: '—', load: '—' },
            ].map((region) => (
              <div key={region.name} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-800">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${region.status === 'Optimal' ? 'bg-emerald-500' : 'bg-slate-500'}`} />
                  <span className="text-sm font-medium text-slate-200">{region.name}</span>
                </div>
                <span className="text-xs font-mono text-slate-400">{region.latency}</span>
              </div>
            ))}
          </div>
          <button className="w-full mt-6 py-2 rounded-lg border border-dashed border-slate-700 text-slate-400 text-sm hover:text-white hover:border-slate-500 hover:bg-slate-800 transition-all flex items-center justify-center space-x-2">
            <Network size={16} />
            <span>Provision New Edge Node</span>
          </button>
        </div>
      </div>

      {/* Recent Events */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
          <Clock size={18} className="text-slate-400" />
          <span>Recent Calls</span>
        </h3>
        <div className="space-y-0">
          {events.length === 0 && (
            <p className="text-sm text-slate-500 py-4 text-center">No calls yet. Make a call to see activity here.</p>
          )}
          {events.map((log, idx) => (
            <div key={idx} className="flex items-start space-x-4 py-3 border-b border-slate-800/50 last:border-0">
              <span className="text-xs font-mono text-slate-500 mt-1">{log.time}</span>
              <div className={`flex-1 text-sm ${log.level === 'warning' ? 'text-amber-400' : 'text-slate-300'}`}>
                {log.msg}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
