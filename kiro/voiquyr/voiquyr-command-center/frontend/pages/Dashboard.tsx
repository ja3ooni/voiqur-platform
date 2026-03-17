import React from 'react';
import { MetricCard } from '../components/MetricCard';
import { Zap, Server, PhoneOutgoing, Clock, Cpu, Network } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { MOCK_LATENCY_DATA } from '../constants';

export const Dashboard: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          title="Avg. E2E Latency" 
          value="438ms" 
          trend="-12ms" 
          trendUp={true} 
          icon={Zap} 
          color="emerald"
        />
        <MetricCard 
          title="Active Calls" 
          value="1,284" 
          trend="+8%" 
          trendUp={true} 
          icon={PhoneOutgoing} 
          color="indigo"
        />
        <MetricCard 
          title="GPU Utilization" 
          value="64%" 
          trend="+2%" 
          trendUp={false} 
          icon={Cpu} 
          color="cyan"
        />
        <MetricCard 
          title="Cost / Min (Avg)" 
          value="$0.042" 
          trend="-0.001" 
          trendUp={true} 
          icon={Server} 
          color="amber"
        />
      </div>

      {/* Charts & Region Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Latency Chart */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-lg font-semibold text-white">Latency Performance</h3>
              <p className="text-sm text-slate-400">Real-time E2E latency across active regions</p>
            </div>
            <div className="flex items-center space-x-2 text-sm">
              <span className="px-2 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">EU (Frankfurt)</span>
            </div>
          </div>
          
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_LATENCY_DATA}>
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
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f1f5f9' }}
                  itemStyle={{ color: '#cbd5e1' }}
                />
                <Area type="monotone" dataKey="e2e" stroke="#6366f1" fillOpacity={1} fill="url(#colorE2E)" name="End-to-End" />
                <Area type="monotone" dataKey="ttfb" stroke="#10b981" fillOpacity={1} fill="url(#colorTTFB)" name="TTFB" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Region Status */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Region Status</h3>
          <div className="space-y-4">
            {[
              { name: 'EU (Frankfurt)', status: 'Optimal', latency: '24ms', load: '45%' },
              { name: 'ME (Bahrain)', status: 'Optimal', latency: '31ms', load: '32%' },
              { name: 'Asia (Mumbai)', status: 'High Load', latency: '48ms', load: '88%' },
              { name: 'Asia (Singapore)', status: 'Maintenance', latency: '--', load: '0%' },
            ].map((region) => (
              <div key={region.name} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-800 hover:border-slate-700 transition-all">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${region.status === 'Optimal' ? 'bg-emerald-500' : region.status === 'High Load' ? 'bg-amber-500' : 'bg-slate-500'}`} />
                  <span className="text-sm font-medium text-slate-200">{region.name}</span>
                </div>
                <div className="text-right">
                  <p className="text-xs font-mono text-slate-400">{region.latency}</p>
                  {region.load !== '0%' && <p className="text-[10px] text-slate-500">Load: {region.load}</p>}
                </div>
              </div>
            ))}
          </div>
          
          <button className="w-full mt-6 py-2 rounded-lg border border-dashed border-slate-700 text-slate-400 text-sm hover:text-white hover:border-slate-500 hover:bg-slate-800 transition-all flex items-center justify-center space-x-2">
            <Network size={16} />
            <span>Provision New Edge Node</span>
          </button>
        </div>
      </div>

      {/* Recent Alerts */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <Clock size={18} className="text-slate-400" />
            <span>System Events</span>
        </h3>
        <div className="space-y-0">
            {[
                { time: '10:42:15', level: 'info', msg: 'Auto-scaled Inference Nodes in Mumbai (ap-south-1)' },
                { time: '10:38:22', level: 'warning', msg: 'SIP Trunk "Tata Pri" experienced 2% packet loss' },
                { time: '10:15:00', level: 'info', msg: 'Daily Compliance Report generated for Region: EU' },
            ].map((log, idx) => (
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