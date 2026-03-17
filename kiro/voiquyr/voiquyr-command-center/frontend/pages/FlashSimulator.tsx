import React, { useState, useEffect, useRef } from 'react';
import { Mic, StopCircle, Zap, Radio, XCircle, BrainCircuit, Activity } from 'lucide-react';
import { SimulationStep } from '../types';

export const FlashSimulator: React.FC = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [flashMode, setFlashMode] = useState(true);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [steps, setSteps] = useState<SimulationStep[]>([]);
  const [confidence, setConfidence] = useState(0);
  const [speculating, setSpeculating] = useState(false);
  
  const startSimulation = () => {
    setIsRecording(true);
    setTranscript('');
    setInterimTranscript('');
    setAiResponse('');
    setSteps([]);
    setConfidence(0);
    setSpeculating(false);
    
    // Scenario: User changes mind (Barge-in / Context Shift)
    const part1 = "I want to order a large pepperoni pizza";
    const part2 = ", actually make that mushrooms.";
    const fullTranscript = part1 + part2;
    const finalResponse = "No problem. One large mushroom pizza coming right up.";
    
    let currentText = "";
    let currentConfidence = 0.0;
    let specTriggered = false;
    let specCancelled = false;
    
    // 1. User Speaking (Streaming)
    const speakInterval = setInterval(() => {
        if (currentText.length < fullTranscript.length) {
            // Add characters
            const chunk = fullTranscript.slice(currentText.length, currentText.length + 2);
            currentText += chunk;
            
            // Simulate Deepgram Nova-2 Confidence rising as sentence forms
            if (currentText.length < 10) currentConfidence = 0.4;
            else if (currentText.length < part1.length - 5) currentConfidence = 0.75;
            else if (currentText.length >= part1.length) currentConfidence = 0.92;
            
            // Random jitter
            currentConfidence = Math.min(0.99, Math.max(0.1, currentConfidence + (Math.random() * 0.05 - 0.025)));
            setConfidence(currentConfidence);
            setInterimTranscript(currentText);
            
            // --- SPECULATIVE INFERENCE TRIGGER LOGIC (Req 2.2) ---
            if (flashMode && !specTriggered && !specCancelled) {
                // Heuristic: High Confidence + Sentence Length > 20 chars (Grammatically likely complete)
                if (currentConfidence > 0.85 && currentText.length >= part1.length) {
                    specTriggered = true;
                    setSpeculating(true);
                    addStep({
                        id: 'spec-infer-1',
                        label: 'Speculative LLM (Intent: Pepperoni)',
                        duration: 0,
                        status: 'processing',
                        type: 'llm'
                    });
                }
            }

            // --- CANCELLATION TOKEN LOGIC ---
            // If we triggered speculation, but the user KEPT talking (length increased significantly)
            if (flashMode && specTriggered && !specCancelled) {
                if (currentText.length > part1.length + 5) {
                    specCancelled = true;
                    setSpeculating(false);
                    // Update the existing step to cancelled
                    setSteps(prev => prev.map(s => 
                        s.id === 'spec-infer-1' 
                        ? { ...s, status: 'cancelled', label: 'Speculative LLM (Cancelled: Context Shift)' } 
                        : s
                    ));
                }
            }
            
        } else {
            clearInterval(speakInterval);
            setIsRecording(false);
            setTranscript(fullTranscript);
            setInterimTranscript(''); 
            setConfidence(0.99);
            processResponse(finalResponse);
        }
    }, 60);
  };

  const addStep = (step: SimulationStep) => {
    setSteps(prev => [...prev, step]);
  };

  const processResponse = async (responseText: string) => {
    // Final VAD / STT
    addStep({ id: 'stt-final', label: 'Final Transcript (Nova-2)', duration: flashMode ? 10 : 120, status: 'completed', type: 'stt' });

    // LLM Generation (Correct Intent)
    await new Promise(r => setTimeout(r, 200));
    addStep({ id: 'llm-final', label: 'LLM Generation (Intent: Mushrooms)', duration: flashMode ? 150 : 450, status: 'processing', type: 'llm' });
    
    await new Promise(r => setTimeout(r, flashMode ? 150 : 450));
    setSteps(prev => prev.map(s => s.id === 'llm-final' ? {...s, status: 'completed'} : s));

    // TTS Streaming
    let currentResp = "";
    const ttsInterval = setInterval(() => {
        if (currentResp.length < responseText.length) {
            currentResp = responseText.slice(0, currentResp.length + 3);
            setAiResponse(currentResp);
            
            if (currentResp.length > 5 && !steps.find(s => s.id === 'tts')) {
                 addStep({ id: 'tts', label: 'ElevenLabs Audio Stream', duration: flashMode ? 80 : 250, status: 'processing', type: 'tts' });
            }
        } else {
            clearInterval(ttsInterval);
            setSteps(prev => prev.map(s => ({...s, status: 'completed'})));
        }
    }, 30);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-full">
      
      {/* Left Control Panel */}
      <div className="col-span-1 space-y-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <div className="flex justify-between items-center mb-4">
             <h3 className="text-lg font-semibold text-white">Orchestrator Sim</h3>
             {speculating && (
                 <div className="flex items-center space-x-2 animate-pulse">
                     <BrainCircuit className="text-indigo-400" size={18} />
                     <span className="text-xs font-bold text-indigo-400 uppercase">Thinking...</span>
                 </div>
             )}
          </div>
          
          {/* Flash Mode Toggle */}
          <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg mb-6 border border-slate-700/50">
            <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${flashMode ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-700 text-slate-400'}`}>
                    <Zap size={20} />
                </div>
                <div>
                    <p className="text-sm font-medium text-white">Flash Mode™</p>
                    <p className="text-xs text-slate-400">Speculative Execution</p>
                </div>
            </div>
            <button 
                onClick={() => setFlashMode(!flashMode)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${flashMode ? 'bg-indigo-500' : 'bg-slate-600'}`}
            >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${flashMode ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>

          {/* STT Confidence Meter */}
          <div className="mb-6">
            <div className="flex justify-between text-xs text-slate-400 mb-2">
                <span>STT Confidence</span>
                <span className="font-mono">{Math.round(confidence * 100)}%</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden relative">
                {/* Threshold Marker */}
                <div className="absolute top-0 bottom-0 w-0.5 bg-white/30 z-10" style={{ left: '85%' }} title="Speculation Threshold (0.85)"></div>
                <div 
                    className={`h-full transition-all duration-100 ease-out ${confidence > 0.85 ? 'bg-emerald-500' : 'bg-indigo-500'}`}
                    style={{ width: `${confidence * 100}%` }}
                ></div>
            </div>
            <div className="flex justify-between text-[10px] text-slate-600 mt-1 font-mono">
                <span>0.0</span>
                <span className="text-slate-400">Trigger: 0.85</span>
                <span>1.0</span>
            </div>
          </div>

          <div className="space-y-4">
            <div className="text-sm text-slate-400 bg-slate-950 p-4 rounded-lg border border-slate-800 font-mono space-y-2">
                <div className="flex justify-between">
                    <span>Scenario:</span>
                    <span className="text-amber-400">Barge-in / Correction</span>
                </div>
                <div className="flex justify-between">
                    <span>Logic:</span>
                    <span className="text-slate-300">Cancellation Token</span>
                </div>
            </div>

            <button
              onClick={startSimulation}
              disabled={isRecording}
              className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center space-x-3 transition-all ${
                isRecording 
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700' 
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20'
              }`}
            >
                {isRecording ? (
                    <><StopCircle /> <span>Streaming...</span></>
                ) : (
                    <><Mic /> <span>Test Speculation</span></>
                )}
            </button>
          </div>
        </div>
      </div>

      {/* Right Visualization Area */}
      <div className="lg:col-span-2 flex flex-col gap-6">
        
        {/* Conversation UI */}
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 flex-1 flex flex-col relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-50"></div>
            
            <div className="flex-1 space-y-6">
                {/* User Message */}
                <div className={`flex items-start space-x-4 transition-opacity duration-500 ${interimTranscript || transcript ? 'opacity-100' : 'opacity-0'}`}>
                    <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center border border-slate-700">
                        <span className="text-xs text-slate-400">USER</span>
                    </div>
                    <div className="flex-1 bg-slate-900 rounded-2xl rounded-tl-none p-4 border border-slate-800 relative">
                        {interimTranscript && !transcript && (
                            <span className="text-slate-400">{interimTranscript}</span>
                        )}
                        {transcript && (
                            <span className="text-slate-200">{transcript}</span>
                        )}
                         {interimTranscript && (
                             <div className="absolute -bottom-6 left-0 flex items-center space-x-1">
                                 <Radio size={12} className="text-emerald-400 animate-pulse" />
                                 <span className="text-[10px] text-emerald-400 font-mono uppercase">Interim Stream</span>
                             </div>
                         )}
                    </div>
                </div>

                {/* AI Message */}
                <div className={`flex items-start space-x-4 flex-row-reverse space-x-reverse transition-opacity duration-500 ${aiResponse ? 'opacity-100' : 'opacity-0'}`}>
                     <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center border border-indigo-500/50">
                        <span className="text-xs text-indigo-400">AI</span>
                    </div>
                    <div className="flex-1 bg-indigo-900/20 rounded-2xl rounded-tr-none p-4 border border-indigo-500/20">
                        <p className="text-indigo-100 text-lg leading-relaxed">{aiResponse}</p>
                    </div>
                </div>
            </div>

            {/* Pipeline Visualizer */}
            <div className="mt-8 pt-6 border-t border-slate-800">
                <h4 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4 flex items-center justify-between">
                    <span>Execution Trace</span>
                    {isRecording && <Activity size={14} className="animate-spin text-slate-400" />}
                </h4>
                <div className="space-y-2">
                    {steps.map((step, idx) => (
                        <div key={idx} className="flex items-center animate-in fade-in slide-in-from-left-4 duration-300">
                            <div className="w-20 text-[10px] text-right text-slate-500 font-mono mr-4">
                                {step.status === 'processing' ? 'BUSY' : step.status === 'cancelled' ? 'KILLED' : `${step.duration}ms`}
                            </div>
                            <div className={`flex-1 p-2 rounded border text-xs font-mono flex justify-between items-center transition-colors duration-300 ${
                                step.status === 'cancelled' ? 'bg-rose-900/20 border-rose-900/50 text-rose-500 line-through opacity-70' :
                                step.type === 'llm' ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300' :
                                step.type === 'stt' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' :
                                step.type === 'tts' ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300' :
                                'bg-slate-800 border-slate-700 text-slate-400'
                            }`}>
                                <div className="flex items-center">
                                    {step.status === 'cancelled' && <XCircle size={12} className="mr-2" />}
                                    <span>{step.label}</span>
                                </div>
                                {step.status === 'processing' && <span className="animate-pulse">●</span>}
                            </div>
                        </div>
                    ))}
                     {isRecording && steps.length === 0 && (
                         <div className="flex items-center justify-center py-4 text-slate-600 text-xs font-mono animate-pulse">
                            Waiting for Voice Activity...
                         </div>
                     )}
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};