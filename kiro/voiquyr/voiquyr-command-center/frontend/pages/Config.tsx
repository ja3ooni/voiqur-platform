import React, { useState, useEffect } from 'react';
import { MOCK_SIP_TRUNKS } from '../constants';
import { Region } from '../types';
import { Shield, Phone, Globe, Lock, Plus, Trash2, Server, Terminal, Activity, Wifi, Save, Code, Copy, Check, Box, FileText } from 'lucide-react';

interface ConfigProps {
  activeTab?: string;
}

export const Config: React.FC<ConfigProps> = ({ activeTab = 'trunks' }) => {
  const [sovereigntyMode, setSovereigntyMode] = useState(true);
  const [homeRegion, setHomeRegion] = useState<Region>(Region.EU_FRANKFURT);
  const [piiRedaction, setPiiRedaction] = useState(true);
  
  // Backend Settings
  const [apiUrl, setApiUrl] = useState("http://localhost:8000");
  const [wsUrl, setWsUrl] = useState("wss://your-ngrok-url.ngrok.io");
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connected' | 'checking'>('disconnected');
  const [healthResponse, setHealthResponse] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const checkConnection = async () => {
    setConnectionStatus('checking');
    setHealthResponse(null);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      
      const res = await fetch(`${apiUrl}/health`, { signal: controller.signal });
      clearTimeout(timeoutId);
      
      if (res.ok) {
        const data = await res.json();
        setConnectionStatus('connected');
        setHealthResponse(JSON.stringify(data, null, 2));
      } else {
        setConnectionStatus('disconnected');
        setHealthResponse(`Error: ${res.status} ${res.statusText}`);
      }
    } catch (err) {
      setConnectionStatus('disconnected');
      setHealthResponse("Connection failed. Is the backend running on port 8000?");
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const dockerfileContent = `FROM python:3.11-slim-buster

# Requirement 2.1: Frankfurt Region Logging Compliance
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

RUN apt-get update && apt-get install -y \\
    build-essential \\
    ffmpeg \\
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]`;

  const dockerComposeContent = `version: '3.8'
services:
  orchestrator:
    build: .
    container_name: voiquyr-edge-node
    ports:
      - "8000:8000"
    environment:
      - REGION_ID=eu-frankfurt-1
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
  redis:
    image: redis:alpine`;

  if (activeTab === 'deployment') {
      return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="space-y-6">
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                      <h3 className="text-lg font-semibold text-white flex items-center mb-4">
                          <Box className="mr-2 text-cyan-400" size={20}/>
                          Container Configuration
                      </h3>
                      <p className="text-sm text-slate-400 mb-6">
                          Docker manifests generated for <strong>Europe (Frankfurt)</strong> deployment. 
                          Timezone locked to <code>Europe/Berlin</code> for audit compliance.
                      </p>
                      
                      <div className="space-y-4">
                          <div>
                              <div className="flex justify-between items-center mb-2">
                                  <label className="text-xs font-mono text-slate-500 uppercase flex items-center">
                                      <FileText size={12} className="mr-1" /> Dockerfile
                                  </label>
                                  <button onClick={() => handleCopy(dockerfileContent)} className="text-xs text-indigo-400 hover:text-white transition-colors">
                                      {copied ? 'Copied!' : 'Copy'}
                                  </button>
                              </div>
                              <div className="bg-slate-950 border border-slate-700 rounded-lg p-4 overflow-x-auto">
                                  <pre className="text-[10px] font-mono text-slate-300 leading-relaxed">
                                      {dockerfileContent}
                                  </pre>
                              </div>
                          </div>

                          <div>
                              <div className="flex justify-between items-center mb-2">
                                  <label className="text-xs font-mono text-slate-500 uppercase flex items-center">
                                      <FileText size={12} className="mr-1" /> docker-compose.yml
                                  </label>
                                  <button onClick={() => handleCopy(dockerComposeContent)} className="text-xs text-indigo-400 hover:text-white transition-colors">
                                      Copy
                                  </button>
                              </div>
                              <div className="bg-slate-950 border border-slate-700 rounded-lg p-4 overflow-x-auto">
                                  <pre className="text-[10px] font-mono text-slate-300 leading-relaxed">
                                      {dockerComposeContent}
                                  </pre>
                              </div>
                          </div>
                      </div>
                  </div>
              </div>

              <div className="space-y-6">
                   <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                      <h3 className="text-lg font-semibold text-white flex items-center mb-4">
                          <Activity className="mr-2 text-emerald-400" size={20}/>
                          Cluster Status (Simulated)
                      </h3>
                      
                      <div className="space-y-3">
                           <div className="flex items-center justify-between p-4 bg-slate-950 border border-slate-800 rounded-lg">
                                <div className="flex items-center space-x-3">
                                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                    <div>
                                        <p className="text-sm font-medium text-slate-200">voiquyr-edge-node-1</p>
                                        <p className="text-xs text-slate-500">Uptime: 4d 12h • CPU: 12%</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <span className="text-xs font-mono text-emerald-400">HEALTHY</span>
                                </div>
                           </div>
                           
                           <div className="flex items-center justify-between p-4 bg-slate-950 border border-slate-800 rounded-lg">
                                <div className="flex items-center space-x-3">
                                    <div className="w-2 h-2 rounded-full bg-emerald-500" />
                                    <div>
                                        <p className="text-sm font-medium text-slate-200">voiquyr-redis-buffer</p>
                                        <p className="text-xs text-slate-500">Uptime: 4d 12h • Mem: 128MB</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <span className="text-xs font-mono text-emerald-400">HEALTHY</span>
                                </div>
                           </div>
                      </div>

                      <div className="mt-6 pt-6 border-t border-slate-800">
                          <h4 className="text-xs font-mono text-slate-500 uppercase mb-3">Deployment Actions</h4>
                          <div className="grid grid-cols-2 gap-4">
                               <button className="flex items-center justify-center py-2 px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 transition-colors">
                                   Restart Pods
                               </button>
                               <button className="flex items-center justify-center py-2 px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 transition-colors">
                                   View Logs
                               </button>
                          </div>
                      </div>
                   </div>
              </div>
          </div>
      );
  }

  // Render Settings / Architecture View
  if (activeTab === 'settings') {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
            {/* Connection Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h3 className="text-lg font-semibold text-white flex items-center">
                            <Server className="mr-2 text-indigo-400" size={20}/>
                            Backend Bridge
                        </h3>
                        <p className="text-sm text-slate-400 mt-1">Connect the Dashboard to your local Python/FastAPI Core</p>
                    </div>
                    <div className={`flex items-center space-x-2 px-3 py-1 rounded-full border ${
                        connectionStatus === 'connected' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 
                        connectionStatus === 'checking' ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' :
                        'bg-slate-800 border-slate-700 text-slate-400'
                    }`}>
                        <Wifi size={14} />
                        <span className="text-xs font-mono font-bold uppercase">{connectionStatus}</span>
                    </div>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-xs font-mono text-slate-500 mb-1 uppercase">REST API Endpoint</label>
                        <div className="flex space-x-2">
                            <input 
                                type="text" 
                                value={apiUrl} 
                                onChange={(e) => setApiUrl(e.target.value)}
                                className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:ring-indigo-500 focus:border-indigo-500"
                            />
                            <button 
                                onClick={checkConnection}
                                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-lg border border-slate-700 transition-colors"
                            >
                                Test Ping
                            </button>
                        </div>
                    </div>

                    {healthResponse && (
                        <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 font-mono text-xs">
                            <div className="flex items-center text-slate-500 mb-2">
                                <Terminal size={12} className="mr-2" />
                                <span>Response Output</span>
                            </div>
                            <pre className={connectionStatus === 'connected' ? 'text-emerald-400' : 'text-rose-400'}>
                                {healthResponse}
                            </pre>
                        </div>
                    )}
                </div>
            </div>

             {/* Twilio TwiML Generator */}
             <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h3 className="text-lg font-semibold text-white flex items-center">
                            <Code className="mr-2 text-rose-400" size={20}/>
                            Twilio Integration (TwiML)
                        </h3>
                        <p className="text-sm text-slate-400 mt-1">Configure your Twilio Phone Number to stream audio to Voiquyr.</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-xs font-mono text-slate-500 mb-1 uppercase">Public WebSocket URL (Ngrok/Domain)</label>
                        <input 
                            type="text" 
                            value={wsUrl} 
                            onChange={(e) => setWsUrl(e.target.value)}
                            placeholder="wss://your-app.ngrok.io"
                            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:ring-indigo-500 focus:border-indigo-500"
                        />
                        <p className="text-[10px] text-slate-500 mt-1">
                            Must be a public HTTPS/WSS URL. Use <code>ngrok http 8000</code> for local dev.
                        </p>
                    </div>

                    <div className="relative group">
                        <label className="block text-xs font-mono text-slate-500 mb-1 uppercase">XML Configuration</label>
                        <div className="bg-slate-950 border border-slate-700 rounded-lg p-4 font-mono text-xs text-slate-300 overflow-x-auto">
                            <div className="text-blue-400">&lt;?xml version="1.0" encoding="UTF-8"?&gt;</div>
                            <div className="text-yellow-400">&lt;Response&gt;</div>
                            <div className="pl-4 text-yellow-400">&lt;Connect&gt;</div>
                            <div className="pl-8 text-emerald-400">&lt;Stream url="{wsUrl}/ws/twilio" /&gt;</div>
                            <div className="pl-4 text-yellow-400">&lt;/Connect&gt;</div>
                            <div className="text-yellow-400">&lt;/Response&gt;</div>
                        </div>
                        <button 
                            onClick={() => handleCopy(`<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n  <Connect>\n    <Stream url="${wsUrl}/ws/twilio" />\n  </Connect>\n</Response>`)}
                            className="absolute top-8 right-2 p-2 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-slate-400 hover:text-white transition-colors"
                            title="Copy TwiML"
                        >
                            {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div className="space-y-6">
             {/* Architecture Diagram / Info */}
             <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden">
                <h3 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Topology</h3>
                <div className="relative z-10 border border-slate-700 rounded-lg p-6 bg-slate-950/50">
                    <div className="flex flex-col space-y-6">
                        <div className="flex items-center justify-between text-sm text-slate-400 font-mono">
                            <div className="flex flex-col items-center">
                                <div className="p-2 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 mb-1">
                                    <Phone size={16} />
                                </div>
                                <span className="text-[10px]">PSTN/Twilio</span>
                            </div>
                            <div className="flex-1 h-px bg-slate-700 mx-2 relative">
                                <span className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-slate-900 px-1 text-[8px] text-slate-500">
                                    RTP
                                </span>
                            </div>
                            <div className="flex flex-col items-center">
                                <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mb-1">
                                    <Server size={16} />
                                </div>
                                <span className="text-[10px]">FastAPI</span>
                            </div>
                        </div>
                         
                         <div className="w-full bg-slate-800/50 rounded p-2 text-[10px] text-slate-500 font-mono">
                            <div className="flex justify-between mb-1">
                                <span>Deepgram Nova-2</span>
                                <span className="text-emerald-400">Ready</span>
                            </div>
                             <div className="flex justify-between mb-1">
                                <span>Groq / Llama3</span>
                                <span className="text-indigo-400">Ready</span>
                            </div>
                             <div className="flex justify-between">
                                <span>ElevenLabs Turbo</span>
                                <span className="text-cyan-400">Ready</span>
                            </div>
                         </div>
                    </div>
                </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Active Modules</h3>
                <div className="space-y-3">
                     <div className="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 rounded-lg">
                        <div className="flex items-center">
                            <Activity size={16} className="text-indigo-400 mr-3" />
                            <span className="text-sm text-slate-200">Flash Inference</span>
                        </div>
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded">ENABLED</span>
                     </div>
                     <div className="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 rounded-lg">
                        <div className="flex items-center">
                            <Lock size={16} className="text-amber-400 mr-3" />
                            <span className="text-sm text-slate-200">Sovereignty Guard</span>
                        </div>
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded">ACTIVE</span>
                     </div>
                </div>
            </div>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
      
      {/* Telephony / BYOC Section */}
      <div className="space-y-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h3 className="text-lg font-semibold text-white flex items-center">
                        <Phone className="mr-2 text-indigo-400" size={20}/>
                        BYOC (Bring Your Own Carrier)
                    </h3>
                    <p className="text-sm text-slate-400 mt-1">Manage SIP Trunks and PSTN Gateways</p>
                </div>
                <button className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center transition-colors">
                    <Plus size={16} className="mr-2" />
                    Add Trunk
                </button>
            </div>

            <div className="overflow-hidden rounded-lg border border-slate-800">
                <table className="min-w-full bg-slate-900/50 text-left text-sm text-slate-400">
                    <thead className="bg-slate-950 text-slate-200 font-medium">
                        <tr>
                            <th className="px-4 py-3">Name</th>
                            <th className="px-4 py-3">URI</th>
                            <th className="px-4 py-3">Region</th>
                            <th className="px-4 py-3">Status</th>
                            <th className="px-4 py-3"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {MOCK_SIP_TRUNKS.map((trunk) => (
                            <tr key={trunk.id} className="hover:bg-slate-800/50 transition-colors">
                                <td className="px-4 py-3 text-white font-medium">{trunk.name}</td>
                                <td className="px-4 py-3 font-mono text-xs">{trunk.uri}</td>
                                <td className="px-4 py-3">{trunk.region}</td>
                                <td className="px-4 py-3">
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                        {trunk.status}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-right">
                                    <button className="text-slate-500 hover:text-rose-400 transition-colors">
                                        <Trash2 size={16} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="mt-4 p-4 bg-amber-500/5 border border-amber-500/10 rounded-lg flex items-start space-x-3">
                <div className="text-amber-400 mt-0.5"><Lock size={16} /></div>
                <div className="text-sm text-amber-200/80">
                    <p className="font-medium text-amber-400">TLS Encryption Required</p>
                    <p>All SIP trunks connecting to Mumbai/Bahrain regions must use Secure RTP (SRTP) per local regulations.</p>
                </div>
            </div>
        </div>
      </div>

      {/* Data Sovereignty Section */}
      <div className="space-y-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="mb-6">
                <h3 className="text-lg font-semibold text-white flex items-center">
                    <Shield className="mr-2 text-emerald-400" size={20}/>
                    Compliance & Sovereignty
                </h3>
                <p className="text-sm text-slate-400 mt-1">Control data residency and privacy filters</p>
            </div>

            <div className="space-y-6">
                {/* Home Region Selector */}
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
                    <label className="block text-sm font-medium text-slate-300 mb-2">Home Region (Data Residency)</label>
                    <div className="flex items-center space-x-4">
                        <Globe className="text-slate-500" size={20} />
                        <select 
                            value={homeRegion}
                            onChange={(e) => setHomeRegion(e.target.value as Region)}
                            className="bg-slate-900 border border-slate-700 text-white text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-full p-2.5"
                        >
                            {Object.values(Region).map((r) => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                    </div>
                    <p className="text-xs text-slate-500 mt-2 pl-9">
                        All PII logs and call recordings will be physically stored in <strong>{homeRegion}</strong>.
                        Replication to US servers is <strong>DISABLED</strong>.
                    </p>
                </div>

                {/* Toggles */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 border border-slate-800 rounded-lg hover:bg-slate-800/30 transition-colors">
                        <div>
                            <h4 className="text-sm font-medium text-white">Region Locking</h4>
                            <p className="text-xs text-slate-500">Prevent failover to regions outside Sovereignty Zone</p>
                        </div>
                        <button 
                            onClick={() => setSovereigntyMode(!sovereigntyMode)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${sovereigntyMode ? 'bg-emerald-500' : 'bg-slate-600'}`}
                        >
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${sovereigntyMode ? 'translate-x-6' : 'translate-x-1'}`} />
                        </button>
                    </div>

                    <div className="flex items-center justify-between p-4 border border-slate-800 rounded-lg hover:bg-slate-800/30 transition-colors">
                        <div>
                            <h4 className="text-sm font-medium text-white">PII Redaction (Live)</h4>
                            <p className="text-xs text-slate-500">Scrub names, credit cards, and IDs from logs</p>
                        </div>
                        <button 
                            onClick={() => setPiiRedaction(!piiRedaction)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${piiRedaction ? 'bg-indigo-500' : 'bg-slate-600'}`}
                        >
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${piiRedaction ? 'translate-x-6' : 'translate-x-1'}`} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};