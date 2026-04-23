import { WebSocketMessage, AudioStreamConfig, TranscriptionResult } from '../types/audio';

export class AudioStreamService {
  private ws: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private microphone: MediaStreamAudioSourceNode | null = null;
  private animationFrame: number | null = null;
  
  private onTranscriptionCallback?: (result: TranscriptionResult) => void;
  private onVisualizationCallback?: (data: { frequencyData: Uint8Array; waveformData: Float32Array; volume: number }) => void;
  private onConnectionCallback?: (connected: boolean) => void;
  private onErrorCallback?: (error: string) => void;
  private onLatencyCallback?: (latency: number) => void;
  private onStatusCallback?: (status: string) => void;
  
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private lastHeartbeat = 0;

  constructor(
    private wsUrl: string = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws/audio',
    private config: AudioStreamConfig = {
      sampleRate: 16000,
      channels: 1,
      bitDepth: 16,
      bufferSize: 4096,
    }
  ) {}

  // WebSocket connection management
  async connect(): Promise<void> {
    try {
      this.ws = new WebSocket(this.wsUrl);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.onConnectionCallback?.(true);
        this.onStatusCallback?.('Connected to audio service');
        
        // Send initial configuration
        this.sendMessage({
          type: 'config',
          data: this.config,
          timestamp: Date.now(),
        });

        // Start heartbeat
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          this.onErrorCallback?.('Failed to parse server message');
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason);
        this.onConnectionCallback?.(false);
        this.stopHeartbeat();
        
        // Attempt reconnection if not intentionally closed
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.attemptReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.onErrorCallback?.('WebSocket connection error');
        this.onStatusCallback?.('Connection error occurred');
      };

    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.onErrorCallback?.('Failed to connect to audio service');
      throw error;
    }
  }

  disconnect(): void {
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close(1000, 'User disconnected'); // Normal closure
      this.ws = null;
    }
    this.stopRecording();
    this.onConnectionCallback?.(false);
    this.onStatusCallback?.('Disconnected');
  }

  private attemptReconnect(): void {
    this.reconnectAttempts++;
    this.onStatusCallback?.(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      this.connect().catch(() => {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.onErrorCallback?.('Failed to reconnect after maximum attempts');
          this.onStatusCallback?.('Connection failed');
        }
      });
    }, this.reconnectDelay * this.reconnectAttempts);
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.lastHeartbeat = Date.now();
        this.sendMessage({
          type: 'heartbeat',
          data: { timestamp: this.lastHeartbeat },
          timestamp: this.lastHeartbeat,
        });
      }
    }, 30000); // Send heartbeat every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  // Audio recording management
  async startRecording(): Promise<void> {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // Set up audio context for visualization
      this.audioContext = new AudioContext({ sampleRate: this.config.sampleRate });
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 2048;
      this.analyser.smoothingTimeConstant = 0.8;

      this.microphone = this.audioContext.createMediaStreamSource(stream);
      this.microphone.connect(this.analyser);

      // Set up MediaRecorder for audio streaming
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: this.config.sampleRate * this.config.bitDepth,
      });

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && this.ws?.readyState === WebSocket.OPEN) {
          // Convert blob to array buffer and send
          event.data.arrayBuffer().then((buffer) => {
            this.sendAudioData(buffer);
          });
        }
      };

      // Start recording with smaller chunks for real-time processing
      this.mediaRecorder.start(50); // Send data every 50ms for better real-time performance
      this.startVisualization();
      this.onStatusCallback?.('Recording started');

    } catch (error) {
      console.error('Failed to start recording:', error);
      this.onErrorCallback?.('Failed to access microphone');
      throw error;
    }
  }

  stopRecording(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    if (this.microphone) {
      this.microphone.disconnect();
      this.microphone = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }

    this.analyser = null;
    this.mediaRecorder = null;
    this.onStatusCallback?.('Recording stopped');
  }

  // Audio visualization
  private startVisualization(): void {
    if (!this.analyser) return;

    const frequencyData = new Uint8Array(this.analyser.frequencyBinCount);
    const waveformData = new Float32Array(this.analyser.fftSize);

    const updateVisualization = () => {
      if (!this.analyser) return;

      this.analyser.getByteFrequencyData(frequencyData);
      this.analyser.getFloatTimeDomainData(waveformData);

      // Calculate volume (RMS)
      let sum = 0;
      for (let i = 0; i < waveformData.length; i++) {
        sum += waveformData[i] * waveformData[i];
      }
      const volume = Math.sqrt(sum / waveformData.length);

      this.onVisualizationCallback?.({
        frequencyData: new Uint8Array(frequencyData),
        waveformData: new Float32Array(waveformData),
        volume,
      });

      this.animationFrame = requestAnimationFrame(updateVisualization);
    };

    updateVisualization();
  }

  // Message handling
  private handleMessage(message: WebSocketMessage): void {
    const latency = Date.now() - message.timestamp;
    this.onLatencyCallback?.(latency);

    switch (message.type) {
      case 'transcription':
        const transcriptionResult: TranscriptionResult = {
          ...message.data,
          timestamp: message.timestamp,
        };
        this.onTranscriptionCallback?.(transcriptionResult);
        break;

      case 'error':
        console.error('Server error:', message.data);
        this.onErrorCallback?.(message.data.message || 'Server error');
        break;

      case 'status':
        console.log('Server status:', message.data);
        this.onStatusCallback?.(message.data.message || 'Status update received');
        break;

      case 'heartbeat':
        // Server heartbeat response - connection is healthy
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }

  private sendMessage(message: WebSocketMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private sendAudioData(audioBuffer: ArrayBuffer): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = {
        type: 'audio',
        data: Array.from(new Uint8Array(audioBuffer)),
        timestamp: Date.now(),
      };
      this.sendMessage(message);
    }
  }

  // Configuration
  updateConfig(newConfig: Partial<AudioStreamConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.sendMessage({
        type: 'config',
        data: this.config,
        timestamp: Date.now(),
      });
    }
  }

  // Event callbacks
  onTranscription(callback: (result: TranscriptionResult) => void): void {
    this.onTranscriptionCallback = callback;
  }

  onVisualization(callback: (data: { frequencyData: Uint8Array; waveformData: Float32Array; volume: number }) => void): void {
    this.onVisualizationCallback = callback;
  }

  onConnection(callback: (connected: boolean) => void): void {
    this.onConnectionCallback = callback;
  }

  onError(callback: (error: string) => void): void {
    this.onErrorCallback = callback;
  }

  onLatency(callback: (latency: number) => void): void {
    this.onLatencyCallback = callback;
  }

  onStatus(callback: (status: string) => void): void {
    this.onStatusCallback = callback;
  }

  // Getters
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get isRecording(): boolean {
    return this.mediaRecorder?.state === 'recording';
  }
}